"""Base de données OSM sur SQLite.

Le schéma reprend celui du serveur OSM officiel — tables séparées pour les
éléments, leurs tags et leurs membres — à une différence près : l'index spatial
est un **R*Tree** plutôt que la colonne *quadtile* du Rails port. Le quadtile
existe parce que PostgreSQL n'offrait pas d'index spatial adapté sans PostGIS ;
SQLite embarque R*Tree en standard (vérifié : module présent), qui fait le même
travail sans arithmétique d'entrelacement de bits à réimplémenter.

Les coordonnées sont stockées en degrés flottants. Le serveur OSM utilise des
entiers en virgule fixe (1e7) pour garantir la reproductibilité des
comparaisons ; à l'échelle d'un département mono-utilisateur, la simplicité
prime, et la précision d'un float64 dépasse largement les 7 décimales émises.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # shapely n'est pas une dépendance du service
    from .topology import OsmBuilder

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS nodes (
    id            INTEGER PRIMARY KEY,
    lat           REAL    NOT NULL,
    lon           REAL    NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    visible       INTEGER NOT NULL DEFAULT 1,
    changeset_id  INTEGER NOT NULL DEFAULT 1,
    timestamp     TEXT    NOT NULL
);

-- Index spatial : une entrée par nœud, dégénérée (min = max) puisqu'un nœud
-- est un point. R*Tree gère ce cas nativement.
CREATE VIRTUAL TABLE IF NOT EXISTS node_index USING rtree(
    id, min_lon, max_lon, min_lat, max_lat
);

CREATE TABLE IF NOT EXISTS node_tags (
    node_id INTEGER NOT NULL,
    k       TEXT    NOT NULL,
    v       TEXT    NOT NULL,
    PRIMARY KEY (node_id, k)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS ways (
    id            INTEGER PRIMARY KEY,
    version       INTEGER NOT NULL DEFAULT 1,
    visible       INTEGER NOT NULL DEFAULT 1,
    changeset_id  INTEGER NOT NULL DEFAULT 1,
    timestamp     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS way_nodes (
    way_id  INTEGER NOT NULL,
    seq     INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    PRIMARY KEY (way_id, seq)
) WITHOUT ROWID;

-- Indispensable à /api/0.6/map : retrouver les ways passant par un nœud donné.
CREATE INDEX IF NOT EXISTS way_nodes_node ON way_nodes (node_id);

CREATE TABLE IF NOT EXISTS way_tags (
    way_id INTEGER NOT NULL,
    k      TEXT    NOT NULL,
    v      TEXT    NOT NULL,
    PRIMARY KEY (way_id, k)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS relations (
    id            INTEGER PRIMARY KEY,
    version       INTEGER NOT NULL DEFAULT 1,
    visible       INTEGER NOT NULL DEFAULT 1,
    changeset_id  INTEGER NOT NULL DEFAULT 1,
    timestamp     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS relation_members (
    relation_id INTEGER NOT NULL,
    seq         INTEGER NOT NULL,
    member_type TEXT    NOT NULL,
    member_id   INTEGER NOT NULL,
    role        TEXT    NOT NULL DEFAULT '',
    PRIMARY KEY (relation_id, seq)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS relation_members_member
    ON relation_members (member_type, member_id);

CREATE TABLE IF NOT EXISTS relation_tags (
    relation_id INTEGER NOT NULL,
    k           TEXT    NOT NULL,
    v           TEXT    NOT NULL,
    PRIMARY KEY (relation_id, k)
) WITHOUT ROWID;

-- Correspondance identifiant BD Topo → élément OSM. C'est elle qui rend la
-- conversion réversible et permettra, au millésime suivant, de produire un
-- différentiel plutôt qu'un rechargement complet.
CREATE TABLE IF NOT EXISTS idmap (
    cleabs       TEXT    NOT NULL PRIMARY KEY,
    element_type TEXT    NOT NULL,
    element_id   INTEGER NOT NULL
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idmap_element ON idmap (element_type, element_id);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS changesets (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    created_at  TEXT    NOT NULL,
    closed_at   TEXT,
    open        INTEGER NOT NULL DEFAULT 1,
    num_changes INTEGER NOT NULL DEFAULT 0,
    min_lat REAL, min_lon REAL, max_lat REAL, max_lon REAL
);

CREATE TABLE IF NOT EXISTS changeset_tags (
    changeset_id INTEGER NOT NULL,
    k            TEXT    NOT NULL,
    v            TEXT    NOT NULL,
    PRIMARY KEY (changeset_id, k)
) WITHOUT ROWID;

-- Compteurs d'identifiants. On ne réutilise jamais l'identifiant d'un élément
-- supprimé : un client qui garderait une référence obsolète pointerait sinon
-- vers un objet sans rapport.
CREATE TABLE IF NOT EXISTS sequences (
    name  TEXT    PRIMARY KEY,
    value INTEGER NOT NULL
);
"""

ELEMENT_TABLES = {
    "node": ("nodes", "node_tags", "node_id"),
    "way": ("ways", "way_tags", "way_id"),
    "relation": ("relations", "relation_tags", "relation_id"),
}

CLEABS_TAG = "ref:FR:IGN:cleabs"


def connect(path: str | Path, read_only: bool = False) -> sqlite3.Connection:
    path = Path(path)
    if read_only:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA synchronous = NORMAL")
    return con


def initialize(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def ensure_schema(con: sqlite3.Connection) -> None:
    """Met à niveau une base existante et amorce les compteurs manquants.

    Une base produite avant l'ajout de l'écriture n'a ni `changesets` ni
    `sequences` ; `CREATE TABLE IF NOT EXISTS` les crée, et les compteurs
    repartent du plus grand identifiant déjà présent — jamais de zéro, sous
    peine de réattribuer des identifiants existants.
    """
    initialize(con)
    for kind, table in (("node", "nodes"), ("way", "ways"), ("relation", "relations")):
        if con.execute("SELECT 1 FROM sequences WHERE name = ?", (kind,)).fetchone():
            continue
        largest = con.execute(f"SELECT coalesce(max(id), 0) FROM {table}").fetchone()[0]
        con.execute("INSERT INTO sequences (name, value) VALUES (?, ?)", (kind, largest))
    if not con.execute("SELECT 1 FROM sequences WHERE name = 'changeset'").fetchone():
        largest = con.execute("SELECT coalesce(max(id), 0) FROM changesets").fetchone()[0]
        con.execute("INSERT INTO sequences (name, value) VALUES ('changeset', ?)", (largest,))
    con.commit()


# --------------------------------------------------------------- chargement


def load(con: sqlite3.Connection, builder: OsmBuilder, *, source_label: str = "") -> dict[str, int]:
    """Verse un graphe construit en mémoire dans la base.

    Insertion en une transaction unique : sur plusieurs millions de lignes, un
    commit par élément multiplierait la durée par deux ordres de grandeur.
    """
    initialize(con)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    con.execute("BEGIN")
    con.executemany(
        "INSERT OR REPLACE INTO nodes (id, lat, lon, timestamp) VALUES (?, ?, ?, ?)",
        ((n.id, n.lat, n.lon, stamp) for n in builder.nodes.values()),
    )
    con.executemany(
        "INSERT OR REPLACE INTO node_index (id, min_lon, max_lon, min_lat, max_lat) "
        "VALUES (?, ?, ?, ?, ?)",
        ((n.id, n.lon, n.lon, n.lat, n.lat) for n in builder.nodes.values()),
    )
    con.executemany(
        "INSERT OR REPLACE INTO node_tags (node_id, k, v) VALUES (?, ?, ?)",
        ((n.id, k, v) for n in builder.nodes.values() for k, v in n.tags.items()),
    )

    con.executemany(
        "INSERT OR REPLACE INTO ways (id, timestamp) VALUES (?, ?)",
        ((w.id, stamp) for w in builder.ways.values()),
    )
    con.executemany(
        "INSERT OR REPLACE INTO way_nodes (way_id, seq, node_id) VALUES (?, ?, ?)",
        (
            (w.id, seq, node_id)
            for w in builder.ways.values()
            for seq, node_id in enumerate(w.nodes)
        ),
    )
    con.executemany(
        "INSERT OR REPLACE INTO way_tags (way_id, k, v) VALUES (?, ?, ?)",
        ((w.id, k, v) for w in builder.ways.values() for k, v in w.tags.items()),
    )

    con.executemany(
        "INSERT OR REPLACE INTO relations (id, timestamp) VALUES (?, ?)",
        ((r.id, stamp) for r in builder.relations.values()),
    )
    con.executemany(
        "INSERT OR REPLACE INTO relation_members "
        "(relation_id, seq, member_type, member_id, role) VALUES (?, ?, ?, ?, ?)",
        (
            (r.id, seq, mtype, mid, role)
            for r in builder.relations.values()
            for seq, (mtype, mid, role) in enumerate(r.members)
        ),
    )
    con.executemany(
        "INSERT OR REPLACE INTO relation_tags (relation_id, k, v) VALUES (?, ?, ?)",
        ((r.id, k, v) for r in builder.relations.values() for k, v in r.tags.items()),
    )

    con.executemany(
        "INSERT OR REPLACE INTO idmap (cleabs, element_type, element_id) VALUES (?, ?, ?)",
        _idmap_rows(builder),
    )

    con.executemany(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        [
            ("loaded_at", stamp),
            ("source", source_label),
            ("max_node_id", str(max(builder.nodes, default=0))),
            ("max_way_id", str(max(builder.ways, default=0))),
            ("max_relation_id", str(max(builder.relations, default=0))),
            _bounds_meta_row(con),
        ],
    )
    # Les compteurs démarrent au-dessus du plus grand identifiant chargé : les
    # éléments créés par l'éditeur ne doivent jamais entrer en collision avec
    # ceux issus de la conversion.
    con.executemany(
        "INSERT OR REPLACE INTO sequences (name, value) VALUES (?, ?)",
        [
            ("node", max(builder.nodes, default=0)),
            ("way", max(builder.ways, default=0)),
            ("relation", max(builder.relations, default=0)),
            ("changeset", 0),
        ],
    )
    con.commit()
    con.execute("ANALYZE")
    con.commit()

    return counts(con)


def _idmap_rows(builder: OsmBuilder) -> Iterator[tuple[str, str, int]]:
    for way in builder.ways.values():
        cleabs = way.tags.get(CLEABS_TAG)
        if cleabs:
            yield (cleabs, "way", way.id)
    for relation in builder.relations.values():
        cleabs = relation.tags.get(CLEABS_TAG)
        if cleabs:
            yield (cleabs, "relation", relation.id)
    for node in builder.nodes.values():
        cleabs = node.tags.get(CLEABS_TAG)
        if cleabs:
            yield (cleabs, "node", node.id)


def counts(con: sqlite3.Connection) -> dict[str, int]:
    return {
        table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("nodes", "ways", "relations", "node_tags", "way_tags", "idmap")
    }


def compute_bounds(con: sqlite3.Connection) -> tuple[float, float, float, float] | None:
    row = con.execute(
        "SELECT min(lon), min(lat), max(lon), max(lat) FROM nodes"
    ).fetchone()
    return tuple(row) if row and row[0] is not None else None


def bounds(con: sqlite3.Connection) -> tuple[float, float, float, float] | None:
    """Emprise de la base, figée dans `meta` à la conversion.

    Le calcul direct balaye toute la table des nœuds : négligeable pour une
    commune, plusieurs secondes à chaque appel de `/status` pour un département.
    """
    row = con.execute("SELECT value FROM meta WHERE key = 'bounds'").fetchone()
    if row and row[0]:
        return tuple(float(v) for v in row[0].split(","))
    return compute_bounds(con)


def _bounds_meta_row(con: sqlite3.Connection) -> tuple[str, str]:
    box = compute_bounds(con)
    return ("bounds", ",".join(repr(v) for v in box) if box else "")


# ------------------------------------------------------------------ écriture


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_id(con: sqlite3.Connection, kind: str) -> int:
    """Alloue un identifiant. Jamais de réemploi, même après suppression."""
    con.execute(
        "INSERT INTO sequences (name, value) VALUES (?, 1) "
        "ON CONFLICT(name) DO UPDATE SET value = value + 1",
        (kind,),
    )
    return con.execute("SELECT value FROM sequences WHERE name = ?", (kind,)).fetchone()[0]


def element_state(con: sqlite3.Connection, kind: str, element_id: int) -> tuple[int, bool] | None:
    """(version, visible) de l'élément, ou None s'il n'a jamais existé."""
    table = ELEMENT_TABLES[kind][0]
    row = con.execute(
        f"SELECT version, visible FROM {table} WHERE id = ?", (element_id,)
    ).fetchone()
    return None if row is None else (row["version"], bool(row["visible"]))


def set_tags(con: sqlite3.Connection, kind: str, element_id: int, tags: dict[str, str]) -> None:
    _, tag_table, column = ELEMENT_TABLES[kind]
    con.execute(f"DELETE FROM {tag_table} WHERE {column} = ?", (element_id,))
    if tags:
        con.executemany(
            f"INSERT INTO {tag_table} ({column}, k, v) VALUES (?, ?, ?)",
            [(element_id, k, v) for k, v in tags.items()],
        )


def write_node(
    con: sqlite3.Connection,
    node_id: int,
    lon: float,
    lat: float,
    version: int,
    changeset_id: int,
    tags: dict[str, str],
) -> None:
    con.execute(
        "INSERT OR REPLACE INTO nodes (id, lat, lon, version, visible, changeset_id, timestamp) "
        "VALUES (?, ?, ?, ?, 1, ?, ?)",
        (node_id, lat, lon, version, changeset_id, now()),
    )
    # L'index R*Tree ne contient que les nœuds visibles : c'est lui qui pilote
    # la sélection de /api/0.6/map.
    con.execute(
        "INSERT OR REPLACE INTO node_index (id, min_lon, max_lon, min_lat, max_lat) "
        "VALUES (?, ?, ?, ?, ?)",
        (node_id, lon, lon, lat, lat),
    )
    set_tags(con, "node", node_id, tags)


def write_way(
    con: sqlite3.Connection,
    way_id: int,
    nodes: list[int],
    version: int,
    changeset_id: int,
    tags: dict[str, str],
) -> None:
    con.execute(
        "INSERT OR REPLACE INTO ways (id, version, visible, changeset_id, timestamp) "
        "VALUES (?, ?, 1, ?, ?)",
        (way_id, version, changeset_id, now()),
    )
    con.execute("DELETE FROM way_nodes WHERE way_id = ?", (way_id,))
    con.executemany(
        "INSERT INTO way_nodes (way_id, seq, node_id) VALUES (?, ?, ?)",
        [(way_id, seq, node_id) for seq, node_id in enumerate(nodes)],
    )
    set_tags(con, "way", way_id, tags)


def write_relation(
    con: sqlite3.Connection,
    relation_id: int,
    members: list[tuple[str, int, str]],
    version: int,
    changeset_id: int,
    tags: dict[str, str],
) -> None:
    con.execute(
        "INSERT OR REPLACE INTO relations (id, version, visible, changeset_id, timestamp) "
        "VALUES (?, ?, 1, ?, ?)",
        (relation_id, version, changeset_id, now()),
    )
    con.execute("DELETE FROM relation_members WHERE relation_id = ?", (relation_id,))
    con.executemany(
        "INSERT INTO relation_members (relation_id, seq, member_type, member_id, role) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (relation_id, seq, mtype, mid, role)
            for seq, (mtype, mid, role) in enumerate(members)
        ],
    )
    set_tags(con, "relation", relation_id, tags)


def delete_element(
    con: sqlite3.Connection, kind: str, element_id: int, version: int, changeset_id: int
) -> None:
    """Marque l'élément invisible et retire ce qui le rendrait encore visible.

    On conserve la ligne — l'API doit pouvoir répondre « supprimé » plutôt que
    « inconnu » — mais on purge index, tags et enfants pour qu'aucune requête
    de lecture ne le ramène.
    """
    table, tag_table, column = ELEMENT_TABLES[kind]
    con.execute(
        f"UPDATE {table} SET visible = 0, version = ?, changeset_id = ?, timestamp = ? "
        "WHERE id = ?",
        (version, changeset_id, now(), element_id),
    )
    con.execute(f"DELETE FROM {tag_table} WHERE {column} = ?", (element_id,))
    if kind == "node":
        con.execute("DELETE FROM node_index WHERE id = ?", (element_id,))
    elif kind == "way":
        con.execute("DELETE FROM way_nodes WHERE way_id = ?", (element_id,))
    else:
        con.execute("DELETE FROM relation_members WHERE relation_id = ?", (element_id,))
    con.execute(
        "DELETE FROM idmap WHERE element_type = ? AND element_id = ?", (kind, element_id)
    )


def referenced_by(con: sqlite3.Connection, kind: str, element_id: int) -> list[str]:
    """Éléments encore visibles qui référencent celui-ci.

    Supprimer un nœud encore porté par un chemin trouerait la géométrie : l'API
    OSM répond 412 dans ce cas, et `if-unused` demande de passer outre en
    laissant l'élément en place.
    """
    users: list[str] = []
    if kind == "node":
        for row in con.execute(
            "SELECT DISTINCT wn.way_id FROM way_nodes wn JOIN ways w ON w.id = wn.way_id "
            "WHERE wn.node_id = ? AND w.visible = 1 LIMIT 5",
            (element_id,),
        ):
            users.append(f"Way {row[0]}")
    for row in con.execute(
        "SELECT DISTINCT rm.relation_id FROM relation_members rm "
        "JOIN relations r ON r.id = rm.relation_id "
        "WHERE rm.member_type = ? AND rm.member_id = ? AND r.visible = 1 LIMIT 5",
        (kind, element_id),
    ):
        users.append(f"Relation {row[0]}")
    return users


# --------------------------------------------------------------- changesets


def open_changeset(con: sqlite3.Connection, user_id: int, tags: dict[str, str]) -> int:
    changeset_id = next_id(con, "changeset")
    con.execute(
        "INSERT INTO changesets (id, user_id, created_at, open) VALUES (?, ?, ?, 1)",
        (changeset_id, user_id, now()),
    )
    con.executemany(
        "INSERT OR REPLACE INTO changeset_tags (changeset_id, k, v) VALUES (?, ?, ?)",
        [(changeset_id, k, v) for k, v in tags.items()],
    )
    con.commit()
    return changeset_id


def changeset(con: sqlite3.Connection, changeset_id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM changesets WHERE id = ?", (changeset_id,)).fetchone()


def changeset_tags(con: sqlite3.Connection, changeset_id: int) -> dict[str, str]:
    return {
        row["k"]: row["v"]
        for row in con.execute(
            "SELECT k, v FROM changeset_tags WHERE changeset_id = ?", (changeset_id,)
        )
    }


def close_changeset(con: sqlite3.Connection, changeset_id: int) -> None:
    con.execute(
        "UPDATE changesets SET open = 0, closed_at = ? WHERE id = ?", (now(), changeset_id)
    )
    con.commit()


def record_changeset_activity(
    con: sqlite3.Connection, changeset_id: int, count: int, bbox: tuple | None
) -> None:
    con.execute(
        "UPDATE changesets SET num_changes = num_changes + ? WHERE id = ?",
        (count, changeset_id),
    )
    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        con.execute(
            "UPDATE changesets SET "
            "  min_lon = min(coalesce(min_lon, ?), ?), min_lat = min(coalesce(min_lat, ?), ?), "
            "  max_lon = max(coalesce(max_lon, ?), ?), max_lat = max(coalesce(max_lat, ?), ?) "
            "WHERE id = ?",
            (min_lon, min_lon, min_lat, min_lat, max_lon, max_lon, max_lat, max_lat, changeset_id),
        )


def changesets_for_user(con: sqlite3.Connection, user_id: int, limit: int = 100) -> list[dict]:
    rows = con.execute(
        "SELECT * FROM changesets WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "closed_at": row["closed_at"],
            "open": bool(row["open"]),
            "user": "bdtopo",
            "uid": row["user_id"],
            "changes_count": row["num_changes"],
            "tags": changeset_tags(con, row["id"]),
        }
        for row in rows
    ]


# ------------------------------------------------------------------ lecture


class MapResult:
    """Éléments à renvoyer pour une requête `/api/0.6/map`."""

    def __init__(self, nodes, ways, relations):
        self.nodes = nodes
        self.ways = ways
        self.relations = relations


def query_map(
    con: sqlite3.Connection, bbox: tuple[float, float, float, float]
) -> MapResult:
    """Sélection OSM classique pour une emprise.

    La règle n'est pas « tout ce qui est dans la boîte » : un way dont un seul
    nœud tombe dans l'emprise doit être renvoyé **entier**, avec tous ses nœuds,
    y compris ceux au-dehors. Sans cela l'éditeur reçoit des géométries
    tronquées et croit que l'objet s'arrête au bord de l'écran.
    """
    min_lon, min_lat, max_lon, max_lat = bbox

    con.executescript(
        "CREATE TEMP TABLE IF NOT EXISTS sel_nodes (id INTEGER PRIMARY KEY);"
        "CREATE TEMP TABLE IF NOT EXISTS sel_ways (id INTEGER PRIMARY KEY);"
        "CREATE TEMP TABLE IF NOT EXISTS sel_relations (id INTEGER PRIMARY KEY);"
        "DELETE FROM sel_nodes; DELETE FROM sel_ways; DELETE FROM sel_relations;"
    )

    # 1. nœuds de l'emprise
    con.execute(
        "INSERT OR IGNORE INTO sel_nodes (id) SELECT id FROM node_index "
        "WHERE min_lon >= ? AND max_lon <= ? AND min_lat >= ? AND max_lat <= ?",
        (min_lon, max_lon, min_lat, max_lat),
    )
    # 2. ways touchant l'un de ces nœuds
    con.execute(
        "INSERT OR IGNORE INTO sel_ways (id) SELECT DISTINCT way_id FROM way_nodes "
        "WHERE node_id IN (SELECT id FROM sel_nodes)"
    )
    # 3. complétion : tous les nœuds de ces ways, même hors emprise
    con.execute(
        "INSERT OR IGNORE INTO sel_nodes (id) SELECT DISTINCT node_id FROM way_nodes "
        "WHERE way_id IN (SELECT id FROM sel_ways)"
    )
    # 4. relations référençant un élément retenu (sans récursion, comme l'API OSM)
    con.execute(
        "INSERT OR IGNORE INTO sel_relations (id) SELECT DISTINCT relation_id "
        "FROM relation_members WHERE "
        "(member_type = 'node' AND member_id IN (SELECT id FROM sel_nodes)) OR "
        "(member_type = 'way'  AND member_id IN (SELECT id FROM sel_ways))"
    )

    return MapResult(
        nodes=_fetch_nodes(con),
        ways=_fetch_ways(con),
        relations=_fetch_relations(con),
    )


def _tags_for(con: sqlite3.Connection, table: str, column: str, selection: str) -> dict:
    grouped: dict[int, dict[str, str]] = {}
    for row in con.execute(
        f"SELECT {column}, k, v FROM {table} WHERE {column} IN (SELECT id FROM {selection})"
    ):
        grouped.setdefault(row[0], {})[row[1]] = row[2]
    return grouped


def _fetch_nodes(con: sqlite3.Connection) -> list[dict]:
    tags = _tags_for(con, "node_tags", "node_id", "sel_nodes")
    return [
        {
            "id": r["id"],
            "lat": r["lat"],
            "lon": r["lon"],
            "version": r["version"],
            "timestamp": r["timestamp"],
            "tags": tags.get(r["id"], {}),
        }
        for r in con.execute(
            "SELECT id, lat, lon, version, timestamp FROM nodes "
            "WHERE id IN (SELECT id FROM sel_nodes) AND visible = 1 ORDER BY id"
        )
    ]


def _fetch_ways(con: sqlite3.Connection) -> list[dict]:
    tags = _tags_for(con, "way_tags", "way_id", "sel_ways")
    refs: dict[int, list[int]] = {}
    for row in con.execute(
        "SELECT way_id, node_id FROM way_nodes "
        "WHERE way_id IN (SELECT id FROM sel_ways) ORDER BY way_id, seq"
    ):
        refs.setdefault(row[0], []).append(row[1])
    return [
        {
            "id": r["id"],
            "version": r["version"],
            "timestamp": r["timestamp"],
            "nodes": refs.get(r["id"], []),
            "tags": tags.get(r["id"], {}),
        }
        for r in con.execute(
            "SELECT id, version, timestamp FROM ways "
            "WHERE id IN (SELECT id FROM sel_ways) AND visible = 1 ORDER BY id"
        )
    ]


def _fetch_relations(con: sqlite3.Connection) -> list[dict]:
    tags = _tags_for(con, "relation_tags", "relation_id", "sel_relations")
    members: dict[int, list[dict]] = {}
    for row in con.execute(
        "SELECT relation_id, member_type, member_id, role FROM relation_members "
        "WHERE relation_id IN (SELECT id FROM sel_relations) ORDER BY relation_id, seq"
    ):
        members.setdefault(row[0], []).append(
            {"type": row[1], "ref": row[2], "role": row[3]}
        )
    return [
        {
            "id": r["id"],
            "version": r["version"],
            "timestamp": r["timestamp"],
            "members": members.get(r["id"], []),
            "tags": tags.get(r["id"], {}),
        }
        for r in con.execute(
            "SELECT id, version, timestamp FROM relations "
            "WHERE id IN (SELECT id FROM sel_relations) AND visible = 1 ORDER BY id"
        )
    ]
