from __future__ import annotations

from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from bdtopo_osm.topology import MAX_WAY_NODES, MemoryBuilder


def test_noeuds_partages_entre_geometries():
    """Le cœur de la conversion : deux tronçons qui se touchent partagent le nœud.

    Sans ça le réseau est visuellement juste mais topologiquement mort.
    """
    b = MemoryBuilder()
    b.add_linestring(LineString([(0, 0), (1, 1)]), {"highway": "residential"})
    b.add_linestring(LineString([(1, 1), (2, 2)]), {"highway": "residential"})

    assert len(b.nodes) == 3  # et non 4
    way_a, way_b = list(b.ways.values())
    assert way_a.nodes[-1] == way_b.nodes[0]


def test_dimension_z_ignoree():
    b = MemoryBuilder()
    b.add_linestring(LineString([(0, 0, 100), (1, 1, 120)]), {})
    assert len(b.nodes) == 2
    assert all(not hasattr(n, "z") for n in b.nodes.values())


def test_coordonnees_proches_non_fusionnees():
    """La coïncidence est exacte dans la BD Topo ; pas de snapping implicite."""
    b = MemoryBuilder()
    b.node_id(0.0, 0.0)
    b.node_id(0.00000001, 0.0)
    assert len(b.nodes) == 2


def test_polygone_simple_devient_way_ferme():
    b = MemoryBuilder()
    carre = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    kind, _ = b.add_polygon(carre, {"building": "house"})

    assert kind == "way"
    assert not b.relations
    way = next(iter(b.ways.values()))
    assert way.nodes[0] == way.nodes[-1]
    assert len(b.nodes) == 4  # le nœud de fermeture est mutualisé


def test_polygone_troue_devient_multipolygon():
    b = MemoryBuilder()
    exterieur = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    trou = [(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)]
    kind, rid = b.add_polygon(Polygon(exterieur, [trou]), {"building": "yes"})

    assert kind == "relation"
    relation = b.relations[rid]
    assert relation.tags["type"] == "multipolygon"
    assert relation.tags["building"] == "yes"
    roles = sorted(role for _, _, role in relation.members)
    assert roles == ["inner", "outer"]
    # les tags appartiennent à la relation, pas aux ways membres
    assert all(not b.ways[ref].tags for _, ref, _ in relation.members)


def test_multipolygone_multipartie():
    b = MemoryBuilder()
    a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    c = Polygon([(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)])
    kind, rid = b.add_polygon(MultiPolygon([a, c]), {"building": "yes"})

    assert kind == "relation"
    assert len(b.relations[rid].members) == 2


def test_way_trop_long_decoupe_en_chaine():
    """L'API OSM refuse au-delà de 2 000 nœuds ; le découpage ne doit pas trouer."""
    b = MemoryBuilder()
    n = MAX_WAY_NODES + 500
    b.add_linestring(LineString([(i * 0.001, 0) for i in range(n)]), {"waterway": "river"})

    ways = list(b.ways.values())
    assert len(ways) == 2
    assert all(len(w.nodes) <= MAX_WAY_NODES for w in ways)
    assert ways[0].nodes[-1] == ways[1].nodes[0]  # jonction partagée
    total = sum(len(w.nodes) for w in ways) - (len(ways) - 1)
    assert total == n  # aucun sommet perdu


def test_point_porte_ses_tags():
    b = MemoryBuilder()
    b.add_point(Point(1, 2), {"amenity": "parking"})
    node = next(iter(b.nodes.values()))
    assert node.tags == {"amenity": "parking"}


def test_geometries_vides_comptees():
    b = MemoryBuilder()
    b.add_linestring(LineString(), {})
    assert b.stats["empty_geometries"] == 1


def test_identifiants_independants_par_type():
    b = MemoryBuilder()
    b.add_polygon(Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]), {"building": "yes"})
    assert min(b.nodes) == 1
    assert min(b.ways) == 1


# ------------------------------------------------- équivalence des deux moteurs


def _peupler(b):
    """Jeu couvrant nœuds partagés, anneau, trou, découpage, point autonome et partagé."""
    b.add_linestring(LineString([(0, 0), (1, 1), (2, 2)]), {"highway": "residential", "ref:FR:IGN:cleabs": "R1"})
    b.add_linestring(LineString([(2, 2), (3, 3)]), {"highway": "residential", "ref:FR:IGN:cleabs": "R2"})
    b.add_polygon(Polygon([(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)]), {"building": "house", "ref:FR:IGN:cleabs": "B1"})
    b.add_polygon(
        Polygon([(10, 10), (14, 10), (14, 14), (10, 14), (10, 10)],
                [[(11, 11), (12, 11), (12, 12), (11, 12), (11, 11)]]),
        {"building": "yes", "ref:FR:IGN:cleabs": "B2"},
    )
    b.add_linestring(LineString([(i * 0.001, 20) for i in range(MAX_WAY_NODES + 10)]), {"waterway": "river"})
    b.add_point(Point(2, 2), {"power": "tower"}, shared=True)       # sur un sommet existant
    b.add_point(Point(2, 2), {"amenity": "bench"}, shared=False)    # superposé mais autonome
    b.add_point(Point(30, 30), {"place": "locality"})


def test_sqlite_builder_produit_le_meme_graphe(tmp_path):
    from bdtopo_osm import store
    from bdtopo_osm.store_builder import SqliteBuilder

    memoire = MemoryBuilder()
    _peupler(memoire)

    con = store.connect(tmp_path / "eq.db")
    disque = SqliteBuilder(con)
    _peupler(disque)
    counts = disque.finalize("test")

    assert counts["nodes"] == len(memoire.nodes)
    assert counts["ways"] == len(memoire.ways)
    assert counts["relations"] == len(memoire.relations)
    assert disque.stats == memoire.stats

    # le pylône partagé est bien un sommet de la route ; le banc autonome, non
    tower = con.execute("SELECT node_id FROM node_tags WHERE k='power'").fetchone()[0]
    bench = con.execute("SELECT node_id FROM node_tags WHERE k='amenity'").fetchone()[0]
    assert con.execute("SELECT count(*) FROM way_nodes WHERE node_id=?", (tower,)).fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM way_nodes WHERE node_id=?", (bench,)).fetchone()[0] == 0
    assert disque.stats["points_superposes"] == 1

    # la relation multipolygone et l'idmap sont là
    assert con.execute("SELECT v FROM relation_tags WHERE k='type'").fetchone()[0] == "multipolygon"
    assert con.execute("SELECT element_type FROM idmap WHERE cleabs='B2'").fetchone()[0] == "relation"
    assert con.execute("SELECT count(*) FROM node_index").fetchone()[0] == counts["nodes"]
    con.close()


def test_sqlite_builder_reprend_au_dessus_des_identifiants_existants(tmp_path):
    from bdtopo_osm import store
    from bdtopo_osm.store_builder import SqliteBuilder

    con = store.connect(tmp_path / "suite.db")
    premier = SqliteBuilder(con)
    premier.add_linestring(LineString([(0, 0), (1, 1)]), {"highway": "path"})
    premier.finalize()
    max_way = con.execute("SELECT max(id) FROM ways").fetchone()[0]

    second = SqliteBuilder(con)
    # partage le nœud (1,1) déjà en base grâce à node_coords conservée
    second.add_linestring(LineString([(1, 1), (2, 2)]), {"highway": "path"})
    second.finalize()
    assert con.execute("SELECT max(id) FROM ways").fetchone()[0] == max_way + 1
    assert con.execute("SELECT count(*) FROM nodes").fetchone()[0] == 3
    con.close()
