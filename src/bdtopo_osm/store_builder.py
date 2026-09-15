"""Construction du graphe directement dans la base SQLite cible.

À l'échelle d'un département, le graphe ne tient pas en mémoire : la Vienne
seule dépasse dix millions de nœuds, et chaque nœud coûte plusieurs centaines
d'octets en objets Python. Ce constructeur écrit au fil de l'eau dans les
tables finales, et déplace la déduplication des sommets dans une table
`node_coords (lon, lat) → id`.

Ce qui rend l'exactitude possible : un REAL SQLite est un double IEEE 754, le
même type que la coordonnée shapely. La recherche par égalité stricte y a donc
exactement le sens qu'elle avait dans le dictionnaire Python — pas de
tolérance, pas d'arrondi, pas de surprise.

`node_coords` est conservée après la conversion. Elle permet d'ajouter une
couche plus tard (les haies, par exemple) en partageant les nœuds avec ce qui
est déjà en base. Elle n'est pas maintenue par l'édition : un nœud déplacé dans
iD garde son ancienne entrée. C'est un index de conversion, pas une vérité.
"""
from __future__ import annotations

import sqlite3

from . import store
from .topology import OsmBuilder

FLUSH_EVERY = 20_000


class SqliteBuilder(OsmBuilder):
    def __init__(self, con: sqlite3.Connection) -> None:
        super().__init__()
        self.con = con
        store.initialize(con)
        con.execute(
            "CREATE TABLE IF NOT EXISTS node_coords ("
            "  lon REAL NOT NULL, lat REAL NOT NULL, id INTEGER NOT NULL,"
            "  PRIMARY KEY (lon, lat)"
            ") WITHOUT ROWID"
        )
        # L'index de coordonnées est un outil de conversion, pas de service :
        # `finalize` le supprime pour ne pas alourdir la base livrée. Pour
        # reprendre au-dessus d'une base finalisée, on le reconstruit depuis
        # les sommets des ways — ce sont eux que les couches suivantes doivent
        # pouvoir rejoindre (extrémités de tronçons, pylônes sur une ligne).
        if con.execute("SELECT NOT EXISTS (SELECT 1 FROM node_coords)").fetchone()[0]:
            con.execute(
                "INSERT OR IGNORE INTO node_coords (lon, lat, id) "
                "SELECT n.lon, n.lat, n.id FROM nodes n "
                "WHERE EXISTS (SELECT 1 FROM way_nodes w WHERE w.node_id = n.id)"
            )
        con.commit()

        # Reprise possible sur une base déjà partiellement remplie : on repart
        # au-dessus des identifiants existants.
        self._next = {
            kind: con.execute(f"SELECT coalesce(max(id), 0) + 1 FROM {table}").fetchone()[0]
            for kind, table in (("node", "nodes"), ("way", "ways"), ("relation", "relations"))
        }
        self.stamp = store.now()

        self._nodes: list[tuple] = []
        self._node_tags: list[tuple] = []
        self._ways: list[tuple] = []
        self._way_nodes: list[tuple] = []
        self._way_tags: list[tuple] = []
        self._relations: list[tuple] = []
        self._members: list[tuple] = []
        self._relation_tags: list[tuple] = []
        self._idmap: list[tuple] = []
        self._provenance: list[tuple] = []
        self._pending = 0
        self._final_counts: dict[str, int] | None = None

        # Une transaction par couche (cf. `commit_layer`) : rapide, et une
        # interruption ne laisse pas de couche à moitié écrite.
        self.con.execute("BEGIN")

    # ------------------------------------------------------------ primitives

    def _allocate(self, kind: str) -> int:
        value = self._next[kind]
        self._next[kind] = value + 1
        return value

    def _lookup_node(self, lon: float, lat: float) -> int | None:
        row = self.con.execute(
            "SELECT id FROM node_coords WHERE lon = ? AND lat = ?", (lon, lat)
        ).fetchone()
        return None if row is None else row[0]

    def _create_node(self, lon: float, lat: float, indexed: bool) -> int:
        node_id = self._allocate("node")
        if indexed:
            # Écrit immédiatement : la prochaine recherche doit le voir. Les
            # autres tables, elles, peuvent attendre le prochain flush.
            self.con.execute(
                "INSERT INTO node_coords (lon, lat, id) VALUES (?, ?, ?)", (lon, lat, node_id)
            )
        self._nodes.append((node_id, lat, lon, self.stamp))
        self._bump()
        return node_id

    def _tag_node(self, node_id: int, tags: dict[str, str]) -> None:
        for k, v in tags.items():
            self._node_tags.append((node_id, k, v))
        cleabs = tags.get(store.CLEABS_TAG)
        if cleabs:
            self._idmap.append((cleabs, "node", node_id))

    def _put_way(self, way_id: int, nodes: list[int], tags: dict[str, str]) -> None:
        self._ways.append((way_id, self.stamp))
        self._way_nodes.extend((way_id, seq, n) for seq, n in enumerate(nodes))
        self._way_tags.extend((way_id, k, v) for k, v in tags.items())
        cleabs = tags.get(store.CLEABS_TAG)
        if cleabs:
            self._idmap.append((cleabs, "way", way_id))
        self._bump()

    def _put_relation(self, relation_id, members, tags) -> None:
        self._relations.append((relation_id, self.stamp))
        self._members.extend(
            (relation_id, seq, mtype, mid, role) for seq, (mtype, mid, role) in enumerate(members)
        )
        self._relation_tags.extend((relation_id, k, v) for k, v in tags.items())
        cleabs = tags.get(store.CLEABS_TAG)
        if cleabs:
            self._idmap.append((cleabs, "relation", relation_id))
        self._bump()

    def record_provenance(self, kind, element_id, layer, attributes) -> None:
        self._provenance.append((kind, element_id, layer, store.pack_provenance(attributes)))

    def counts(self) -> dict[str, int]:
        # Après `finalize`, la connexion est rendue au pipeline qui la ferme :
        # le rapport doit lire les compteurs figés, pas rouvrir la base.
        if self._final_counts is not None:
            return self._final_counts
        self.flush()
        return {
            table: self.con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("nodes", "ways", "relations")
        }

    # ------------------------------------------------------------ écriture

    def _bump(self) -> None:
        self._pending += 1
        if self._pending >= FLUSH_EVERY:
            self.flush()

    def flush(self) -> None:
        con = self.con
        if self._nodes:
            con.executemany(
                "INSERT INTO nodes (id, lat, lon, timestamp) VALUES (?, ?, ?, ?)", self._nodes
            )
            con.executemany(
                "INSERT INTO node_index (id, min_lon, max_lon, min_lat, max_lat) "
                "VALUES (?, ?, ?, ?, ?)",
                [(i, lon, lon, lat, lat) for i, lat, lon, _ in self._nodes],
            )
            self._nodes.clear()
        if self._node_tags:
            con.executemany(
                "INSERT OR REPLACE INTO node_tags (node_id, k, v) VALUES (?, ?, ?)",
                self._node_tags,
            )
            self._node_tags.clear()
        if self._ways:
            con.executemany("INSERT INTO ways (id, timestamp) VALUES (?, ?)", self._ways)
            con.executemany(
                "INSERT INTO way_nodes (way_id, seq, node_id) VALUES (?, ?, ?)", self._way_nodes
            )
            con.executemany(
                "INSERT INTO way_tags (way_id, k, v) VALUES (?, ?, ?)", self._way_tags
            )
            self._ways.clear()
            self._way_nodes.clear()
            self._way_tags.clear()
        if self._relations:
            con.executemany(
                "INSERT INTO relations (id, timestamp) VALUES (?, ?)", self._relations
            )
            con.executemany(
                "INSERT INTO relation_members (relation_id, seq, member_type, member_id, role) "
                "VALUES (?, ?, ?, ?, ?)",
                self._members,
            )
            con.executemany(
                "INSERT INTO relation_tags (relation_id, k, v) VALUES (?, ?, ?)",
                self._relation_tags,
            )
            self._relations.clear()
            self._members.clear()
            self._relation_tags.clear()
        if self._idmap:
            con.executemany(
                "INSERT OR REPLACE INTO idmap (cleabs, element_type, element_id) VALUES (?, ?, ?)",
                self._idmap,
            )
            self._idmap.clear()
        if self._provenance:
            con.executemany(
                "INSERT OR REPLACE INTO provenance (element_type, element_id, layer, data) "
                "VALUES (?, ?, ?, ?)",
                self._provenance,
            )
            self._provenance.clear()
        self._pending = 0

    def commit_layer(self) -> None:
        """Valide la couche en cours et ouvre la transaction de la suivante."""
        self.flush()
        self.con.commit()
        self.con.execute("BEGIN")

    def finalize(self, source_label: str = "") -> dict[str, int]:
        """Clôt la conversion : compteurs, métadonnées, statistiques SQLite."""
        self.flush()
        self.con.commit()
        con = self.con
        con.executemany(
            "INSERT OR REPLACE INTO sequences (name, value) VALUES (?, ?)",
            [
                ("node", self._next["node"] - 1),
                ("way", self._next["way"] - 1),
                ("relation", self._next["relation"] - 1),
                ("changeset", 0),
            ],
        )
        con.executemany(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            [
                ("loaded_at", self.stamp),
                ("source", source_label),
                ("max_node_id", str(self._next["node"] - 1)),
                ("max_way_id", str(self._next["way"] - 1)),
                ("max_relation_id", str(self._next["relation"] - 1)),
                store._bounds_meta_row(con),
            ],
        )
        con.commit()
        con.execute("DROP TABLE IF EXISTS node_coords")
        store.build_spatial_indexes(con)
        con.commit()
        con.execute("ANALYZE")
        con.commit()
        con.execute("VACUUM")  # rend au fichier la place de l'index supprimé
        self._final_counts = {
            table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("nodes", "ways", "relations")
        }
        return store.counts(con)
