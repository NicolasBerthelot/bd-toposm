"""Passage du modèle en couches de la BD Topo au modèle nodes / ways / relations.

L'opération clé est la déduplication des sommets : deux tronçons qui se
rejoignent doivent partager le *même* nœud OSM, sinon le réseau est visuellement
correct mais topologiquement mort (impossible de router, et déplacer un carrefour
dans iD ne déplace qu'une des branches).

Mesure préalable sur Poitiers (11 991 tronçons, 23 982 extrémités) : les
extrémités coïncidentes le sont **exactement en float64** — arrondir à 1e-7 ne
fusionne pas un seul nœud de plus. La BD Topo est déjà un graphe topologique, la
déduplication est donc un simple regroupement par coordonnée, sans tolérance ni
snapping. C'est ce qui rend cette étape sûre plutôt qu'heuristique.

Le stockage est séparé de la logique : `OsmBuilder` porte les règles (anneaux,
multipolygones, découpage à 2 000 nœuds) et délègue la persistance à cinq
primitives. `MemoryBuilder` les implémente en dictionnaires — suffisant pour
une commune, et ce que les tests exercent. `store_builder.SqliteBuilder` les
implémente sur la base cible — indispensable pour un département, où le graphe
dépasse la mémoire disponible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from shapely import get_coordinates
from shapely.geometry.base import BaseGeometry

# Limite de l'API OSM 0.6 : un way ne peut porter plus de 2 000 nœuds. Les
# grandes surfaces (plans d'eau, massifs forestiers) la dépassent et doivent
# être découpées en plusieurs ways chaînés.
MAX_WAY_NODES = 2000


@dataclass
class Way:
    id: int
    nodes: list[int]
    tags: dict[str, str]


@dataclass
class Relation:
    id: int
    members: list[tuple[str, int, str]]  # (type, ref, role)
    tags: dict[str, str]


@dataclass
class Node:
    id: int
    lon: float
    lat: float
    tags: dict[str, str] = field(default_factory=dict)


class OsmBuilder:
    """Règles de construction du graphe, indépendantes du stockage.

    Les sous-classes fournissent les primitives `_lookup_node`, `_create_node`,
    `_tag_node`, `_put_way`, `_put_relation` et `_allocate`.
    """

    def __init__(self) -> None:
        self.stats = {
            "ways_split": 0,
            "multipolygons": 0,
            "closed_ways": 0,
            "shared_nodes": 0,
            "empty_geometries": 0,
            "points_superposes": 0,
        }

    # ---------------------------------------------------- primitives à fournir

    def _allocate(self, kind: str) -> int:
        raise NotImplementedError

    def _lookup_node(self, lon: float, lat: float) -> int | None:
        raise NotImplementedError

    def _create_node(self, lon: float, lat: float, indexed: bool) -> int:
        raise NotImplementedError

    def _tag_node(self, node_id: int, tags: dict[str, str]) -> None:
        raise NotImplementedError

    def _put_way(self, way_id: int, nodes: list[int], tags: dict[str, str]) -> None:
        raise NotImplementedError

    def _put_relation(
        self, relation_id: int, members: list[tuple[str, int, str]], tags: dict[str, str]
    ) -> None:
        raise NotImplementedError

    def counts(self) -> dict[str, int]:
        raise NotImplementedError

    # ---------------------------------------------------------------- nœuds

    def node_id(self, lon: float, lat: float) -> int:
        """Identifiant du nœud à cette coordonnée, créé au besoin.

        La clé est la coordonnée brute en float64 : c'est la propriété vérifiée
        sur la donnée, pas une approximation. Arrondir ici introduirait des
        fusions non voulues entre objets réellement distincts.
        """
        existing = self._lookup_node(lon, lat)
        if existing is not None:
            self.stats["shared_nodes"] += 1
            return existing
        return self._create_node(lon, lat, indexed=True)

    # ----------------------------------------------------------- géométries

    def add_point(
        self, geom: BaseGeometry, tags: dict[str, str], shared: bool = False
    ) -> list[int]:
        """Crée un nœud porteur de tags.

        `shared=True` réutilise le nœud déjà présent à cette coordonnée : c'est
        ce qu'on veut quand l'objet ponctuel *est* un sommet d'une géométrie
        voisine — un pylône sur sa ligne électrique, par exemple.

        `shared=False` (défaut) alloue un nœud dédié, non indexé par
        coordonnée. Un équipement public qui tomberait par hasard sur un coin de
        bâtiment ne doit pas s'y greffer : il deviendrait un sommet du contour,
        et le déplacer déformerait le bâtiment.
        """
        coords = get_coordinates(geom)  # 2D : la dimension Z est écartée
        if len(coords) == 0:
            self.stats["empty_geometries"] += 1
            return []
        lon, lat = float(coords[0][0]), float(coords[0][1])

        if shared:
            node_id = self.node_id(lon, lat)
        else:
            if self._lookup_node(lon, lat) is not None:
                self.stats["points_superposes"] += 1
            node_id = self._create_node(lon, lat, indexed=False)

        self._tag_node(node_id, tags)
        return [node_id]

    def add_linestring(self, geom: BaseGeometry, tags: dict[str, str]) -> list[int]:
        """Crée un ou plusieurs ways. Retourne les identifiants créés."""
        if geom is None or geom.is_empty:
            self.stats["empty_geometries"] += 1
            return []
        created: list[int] = []
        for part in _line_parts(geom):
            node_ids = self._nodes_for(part)
            if len(node_ids) < 2:
                self.stats["empty_geometries"] += 1
                continue
            created.extend(self._emit_way_chain(node_ids, tags))
        return created

    def add_polygon(self, geom: BaseGeometry, tags: dict[str, str]) -> tuple[str, int] | None:
        """Crée un way fermé, ou une relation multipolygon si nécessaire.

        Une relation s'impose dès qu'il y a un trou, plusieurs parties, ou un
        contour trop long pour tenir dans un seul way.
        """
        parts = _polygon_parts(geom)
        if not parts:
            self.stats["empty_geometries"] += 1
            return None

        simple = len(parts) == 1 and not parts[0][1]
        if simple:
            ring_nodes = self._nodes_for(parts[0][0])
            if 4 <= len(ring_nodes) <= MAX_WAY_NODES:
                way_id = self._allocate("way")
                self._put_way(way_id, ring_nodes, dict(tags))
                self.stats["closed_ways"] += 1
                return ("way", way_id)

        members: list[tuple[str, int, str]] = []
        for outer, inners in parts:
            for way_id in self._emit_ring(outer):
                members.append(("way", way_id, "outer"))
            for inner in inners:
                for way_id in self._emit_ring(inner):
                    members.append(("way", way_id, "inner"))

        if not members:
            self.stats["empty_geometries"] += 1
            return None

        relation_id = self._allocate("relation")
        self._put_relation(relation_id, members, {"type": "multipolygon", **tags})
        self.stats["multipolygons"] += 1
        return ("relation", relation_id)

    # -------------------------------------------------------------- internes

    def _nodes_for(self, coords) -> list[int]:
        return [self.node_id(float(x), float(y)) for x, y in coords]

    def _emit_ring(self, coords) -> list[int]:
        """Ways portant un anneau, sans tags (ils sont portés par la relation)."""
        node_ids = self._nodes_for(coords)
        if len(node_ids) < 4:
            return []
        return self._emit_way_chain(node_ids, {})

    def _emit_way_chain(self, node_ids: list[int], tags: dict[str, str]) -> list[int]:
        """Émet un way, ou une chaîne de ways si la limite de 2 000 est dépassée.

        Les segments successifs partagent leur nœud de jonction : le découpage
        est une contrainte de format, il ne doit pas trouer la géométrie.
        """
        if len(node_ids) <= MAX_WAY_NODES:
            way_id = self._allocate("way")
            self._put_way(way_id, node_ids, dict(tags))
            return [way_id]

        created: list[int] = []
        start = 0
        while start < len(node_ids) - 1:
            end = min(start + MAX_WAY_NODES, len(node_ids))
            way_id = self._allocate("way")
            self._put_way(way_id, node_ids[start:end], dict(tags))
            created.append(way_id)
            self.stats["ways_split"] += 1
            start = end - 1  # le dernier nœud du segment est le premier du suivant
        return created

    # ---------------------------------------------------------------- sortie

    def summary(self) -> dict[str, int]:
        return {**self.counts(), **self.stats}


class MemoryBuilder(OsmBuilder):
    """Graphe en mémoire : suffisant à l'échelle d'une commune."""

    def __init__(self) -> None:
        super().__init__()
        self._node_by_coord: dict[tuple[float, float], int] = {}
        self.nodes: dict[int, Node] = {}
        self.ways: dict[int, Way] = {}
        self.relations: dict[int, Relation] = {}
        self._next = {"node": 1, "way": 1, "relation": 1}

    def _allocate(self, kind: str) -> int:
        value = self._next[kind]
        self._next[kind] = value + 1
        return value

    def _lookup_node(self, lon: float, lat: float) -> int | None:
        return self._node_by_coord.get((lon, lat))

    def _create_node(self, lon: float, lat: float, indexed: bool) -> int:
        node_id = self._allocate("node")
        self.nodes[node_id] = Node(node_id, lon, lat)
        if indexed:
            self._node_by_coord[(lon, lat)] = node_id
        return node_id

    def _tag_node(self, node_id: int, tags: dict[str, str]) -> None:
        self.nodes[node_id].tags.update(tags)

    def _put_way(self, way_id: int, nodes: list[int], tags: dict[str, str]) -> None:
        self.ways[way_id] = Way(way_id, nodes, tags)

    def _put_relation(self, relation_id, members, tags) -> None:
        self.relations[relation_id] = Relation(relation_id, members, tags)

    def counts(self) -> dict[str, int]:
        return {
            "nodes": len(self.nodes),
            "ways": len(self.ways),
            "relations": len(self.relations),
        }


def _line_parts(geom: BaseGeometry) -> Iterator:
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == "LineString":
        yield get_coordinates(geom)
    elif geom.geom_type == "MultiLineString":
        for part in geom.geoms:
            if not part.is_empty:
                yield get_coordinates(part)


def _polygon_parts(geom: BaseGeometry) -> list[tuple]:
    """[(anneau extérieur, [anneaux intérieurs]), ...] en coordonnées 2D."""
    if geom is None or geom.is_empty:
        return []
    polygons = []
    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = [p for p in geom.geoms if not p.is_empty]
    return [
        (get_coordinates(p.exterior), [get_coordinates(r) for r in p.interiors])
        for p in polygons
    ]
