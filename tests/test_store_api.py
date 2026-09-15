from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Polygon

from bdtopo_osm import store
from bdtopo_osm.api import MAX_AREA, _chunked, create_app
from bdtopo_osm.topology import MemoryBuilder


# L'emprise de test tient sous la limite de 0,25 degré carré que l'API annonce
# dans ses capabilities — sans quoi c'est le garde-fou qui répond, pas la requête.
BBOX = (0.0, 0.0, 0.4, 0.4)


@pytest.fixture
def db(tmp_path):
    """Petit jeu de données : une route qui sort de l'emprise, un bâtiment troué."""
    builder = MemoryBuilder()
    # Route traversant l'emprise de test et la débordant largement.
    builder.add_linestring(
        LineString([(0.05, 0.05), (0.35, 0.35), (5.0, 5.0)]),
        {"highway": "residential", "name": "Rue de Test", "ref:FR:IGN:cleabs": "TR1"},
    )
    # Bâtiment entièrement hors emprise.
    builder.add_polygon(
        Polygon([(20, 20), (21, 20), (21, 21), (20, 21), (20, 20)]),
        {"building": "house", "ref:FR:IGN:cleabs": "BA1"},
    )
    # Bâtiment troué dans l'emprise.
    builder.add_polygon(
        Polygon(
            [(0.1, 0.1), (0.4, 0.1), (0.4, 0.4), (0.1, 0.4), (0.1, 0.1)],
            [[(0.2, 0.2), (0.3, 0.2), (0.3, 0.3), (0.2, 0.3), (0.2, 0.2)]],
        ),
        {"building": "yes", "ref:FR:IGN:cleabs": "BA2"},
    )

    path = tmp_path / "test.db"
    con = store.connect(path)
    store.load(con, builder, source_label="test")
    con.close()
    return path


@pytest.fixture
def client(db):
    return TestClient(create_app(db))


# ------------------------------------------------------------------- store


def test_chargement_et_comptes(db):
    con = store.connect(db, read_only=True)
    counts = store.counts(con)
    # route + bâtiment simple + les 2 anneaux (extérieur, intérieur) du troué
    assert counts["ways"] == 4
    assert counts["relations"] == 1
    assert counts["idmap"] == 3  # TR1, BA1, BA2
    con.close()


def test_idmap_pointe_vers_le_bon_element(db):
    con = store.connect(db, read_only=True)
    row = con.execute("SELECT * FROM idmap WHERE cleabs = 'BA2'").fetchone()
    assert row["element_type"] == "relation"
    row = con.execute("SELECT * FROM idmap WHERE cleabs = 'TR1'").fetchone()
    assert row["element_type"] == "way"
    con.close()


def test_way_debordant_revient_entier(db):
    """Un way dont un seul nœud est dans l'emprise doit revenir complet.

    Sans cette règle l'éditeur reçoit des géométries tronquées et croit que
    l'objet s'arrête au bord de l'écran.
    """
    con = store.connect(db, read_only=True)
    result = store.query_map(con, BBOX)

    ways = {w["id"]: w for w in result.ways}
    route = next(w for w in ways.values() if w["tags"].get("highway"))
    assert len(route["nodes"]) == 3  # y compris le sommet à (5, 5)

    returned = {n["id"] for n in result.nodes}
    assert set(route["nodes"]) <= returned  # tous ses nœuds sont fournis
    con.close()


def test_elements_hors_emprise_absents(db):
    con = store.connect(db, read_only=True)
    result = store.query_map(con, BBOX)
    cleabs = {w["tags"].get("ref:FR:IGN:cleabs") for w in result.ways}
    assert "BA1" not in cleabs  # bâtiment à (20, 20)
    con.close()


def test_relation_ramenee_avec_ses_membres(db):
    con = store.connect(db, read_only=True)
    result = store.query_map(con, BBOX)
    assert len(result.relations) == 1
    relation = result.relations[0]
    assert relation["tags"]["type"] == "multipolygon"
    roles = sorted(m["role"] for m in relation["members"])
    assert roles == ["inner", "outer"]

    returned_ways = {w["id"] for w in result.ways}
    assert {m["ref"] for m in relation["members"]} <= returned_ways
    con.close()


def test_requetes_successives_ne_se_contaminent_pas(db):
    """Les tables temporaires de sélection doivent être purgées entre appels."""
    con = store.connect(db, read_only=True)
    large = store.query_map(con, BBOX)
    empty = store.query_map(con, (50.0, 50.0, 50.1, 50.1))
    assert large.ways and not empty.ways and not empty.nodes
    con.close()


# --------------------------------------------------------------------- API


def test_capabilities_annonce_lecture_seule(client):
    r = client.get("/api/capabilities")
    assert r.status_code == 200
    root = ET.fromstring(r.text)
    status = root.find("./api/status")
    assert status.get("api") == "readonly"
    assert root.find("./api/version").get("maximum") == "0.6"
    assert float(root.find("./api/area").get("maximum")) == MAX_AREA
    assert root.find("./api/waynodes").get("maximum") == "2000"


def test_capabilities_disponible_aux_deux_chemins(client):
    assert client.get("/api/capabilities").status_code == 200
    assert client.get("/api/0.6/capabilities").status_code == 200


def test_map_renvoie_du_osm_valide(client):
    r = client.get("/api/0.6/map", params={"bbox": "0.0,0.0,0.4,0.4"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/xml")

    root = ET.fromstring(r.text)
    assert root.tag == "osm"
    assert root.get("version") == "0.6"

    bounds = root.find("bounds")
    assert bounds is not None and bounds.get("minlat") == "0.0000000"

    # intégrité référentielle de la réponse
    node_ids = {int(n.get("id")) for n in root.findall("node")}
    for way in root.findall("way"):
        for nd in way.findall("nd"):
            assert int(nd.get("ref")) in node_ids

    way_ids = {int(w.get("id")) for w in root.findall("way")}
    for relation in root.findall("relation"):
        for member in relation.findall("member"):
            if member.get("type") == "way":
                assert int(member.get("ref")) in way_ids


def test_map_refuse_une_emprise_trop_large(client):
    r = client.get("/api/0.6/map", params={"bbox": "0,0,10,10"})
    assert r.status_code == 400
    assert "maximum 0.25" in r.text


@pytest.mark.parametrize("bbox", ["pas-un-bbox", "1,2,3", "1,1,0,0"])
def test_map_refuse_un_bbox_invalide(client, bbox):
    assert client.get("/api/0.6/map", params={"bbox": bbox}).status_code == 400


def test_status(client):
    body = client.get("/status").json()
    assert body["readonly"] is True
    assert body["counts"]["ways"] == 4


# ------------------------------------------------- contrat JSON attendu par iD
# Ces attentes sont relevées dans le code d'iD (`web/id/iD.js`), pas déduites :
# `status()` lit capabilities.json, `loadTile()` appelle /api/0.6/map.json, et
# `jsonparsers` fixe la forme des éléments.


def test_capabilities_json_couvre_ce_que_id_deréférence(client):
    payload = client.get("/api/capabilities.json").json()

    # iD fait `payload.policy.imagery.blacklist.map(...)` sans garde : absent,
    # c'est une exception au démarrage et une page blanche.
    assert payload["policy"]["imagery"]["blacklist"] == []

    assert payload["api"]["waynodes"]["maximum"] == 2000
    assert isinstance(payload["api"]["changesets"]["maximum_elements"], int)
    assert payload["api"]["status"]["api"] == "readonly"


def test_map_json_respecte_les_parseurs_id(client):
    payload = client.get("/api/0.6/map.json", params={"bbox": "0.0,0.0,0.4,0.4"}).json()

    # `parseJSON` refuse une charge sans `elements`.
    assert "elements" in payload
    elements = payload["elements"]
    assert elements

    by_type = {}
    for element in elements:
        by_type.setdefault(element["type"], []).append(element)
    assert set(by_type) == {"node", "way", "relation"}

    node = by_type["node"][0]
    assert isinstance(node["lat"], float) and isinstance(node["lon"], float)

    way = next(w for w in by_type["way"] if w.get("tags", {}).get("highway"))
    # `getNodesJSON` itère `obj.nodes` : des identifiants, pas des objets.
    assert all(isinstance(ref, int) for ref in way["nodes"])

    relation = by_type["relation"][0]
    # `getMembersJSON` lit `type`, `ref` et `role` sur chaque membre.
    for member in relation["members"]:
        assert set(member) == {"type", "ref", "role"}
        assert member["type"] in ("node", "way", "relation")


def test_map_json_est_referentiellement_complet(client):
    payload = client.get("/api/0.6/map.json", params={"bbox": "0.0,0.0,0.4,0.4"}).json()
    elements = payload["elements"]
    node_ids = {e["id"] for e in elements if e["type"] == "node"}
    way_ids = {e["id"] for e in elements if e["type"] == "way"}

    for element in elements:
        if element["type"] == "way":
            assert set(element["nodes"]) <= node_ids
        elif element["type"] == "relation":
            for member in element["members"]:
                if member["type"] == "way":
                    assert member["ref"] in way_ids


def test_map_json_et_xml_decrivent_le_meme_contenu(client):
    payload = client.get("/api/0.6/map.json", params={"bbox": "0.0,0.0,0.4,0.4"}).json()
    root = ET.fromstring(
        client.get("/api/0.6/map", params={"bbox": "0.0,0.0,0.4,0.4"}).text
    )

    counts_json = {}
    for element in payload["elements"]:
        counts_json[element["type"]] = counts_json.get(element["type"], 0) + 1

    for kind in ("node", "way", "relation"):
        assert counts_json.get(kind, 0) == len(root.findall(kind))


def test_map_json_applique_le_garde_fou_d_emprise(client):
    assert client.get("/api/0.6/map.json", params={"bbox": "0,0,10,10"}).status_code == 400


# --------------------------------------------------------------- streaming


def test_tampon_regroupe_les_fragments():
    """Starlette paie un aller-retour thread/async par `yield`.

    Sans tampon, rendre le XML balise par balise coûtait 58 280 yields et 25,6 s
    pour 3,2 Mo, contre 0,19 s en mémoire. Ce test verrouille le regroupement.
    """
    pieces = ["x" * 100] * 10_000  # 1 Mo en 10 000 fragments
    chunks = list(_chunked(pieces, size=256 * 1024))

    assert len(chunks) <= 8
    assert "".join(chunks) == "".join(pieces)


def test_tampon_preserve_le_contenu_court():
    assert list(_chunked(iter([]))) == []
    assert list(_chunked(iter(["a", "b"]))) == ["ab"]


def test_healthz_est_leger(client):
    assert client.get("/healthz").json() == {"ok": True}


# ------------------------------------------------------- lecture unitaire


def test_lecture_unitaire_et_full(client):
    payload = client.get("/api/0.6/map.json", params={"bbox": "0.0,0.0,0.4,0.4"}).json()
    route = next(e for e in payload["elements"] if e["type"] == "way" and e.get("tags", {}).get("highway"))
    relation = next(e for e in payload["elements"] if e["type"] == "relation")

    seul = client.get(f"/api/0.6/way/{route['id']}.json").json()["elements"]
    assert [e["type"] for e in seul] == ["way"]

    full = client.get(f"/api/0.6/way/{route['id']}/full.json").json()["elements"]
    assert {e["id"] for e in full if e["type"] == "node"} == set(route["nodes"])

    rfull = client.get(f"/api/0.6/relation/{relation['id']}/full.json").json()["elements"]
    assert {e["id"] for e in rfull if e["type"] == "way"} == {m["ref"] for m in relation["members"]}
    assert any(e["type"] == "node" for e in rfull)  # nœuds des ways membres inclus

    membre = relation["members"][0]["ref"]
    rels = client.get(f"/api/0.6/way/{membre}/relations.json").json()["elements"]
    assert [e["id"] for e in rels] == [relation["id"]]

    ways = client.get(f"/api/0.6/node/{route['nodes'][0]}/ways.json").json()["elements"]
    assert route["id"] in {e["id"] for e in ways}

    multi = client.get("/api/0.6/ways.json", params={"ways": f"{route['id']},{membre}"}).json()["elements"]
    assert {e["id"] for e in multi} == {route["id"], membre}

    assert client.get("/api/0.6/way/999999.json").status_code == 404
    assert client.get("/api/0.6/node/1/full.json").status_code == 404


# ---------------------------------------------------- filtrage par couche


@pytest.fixture
def db_couches(tmp_path):
    """Route, bâtiment troué, commune (relation boundary) et un point créé
    « à la main » (sans provenance), tous dans l'emprise de test."""
    builder = MemoryBuilder()
    (kind, wid), = [("way", w) for w in builder.add_linestring(
        LineString([(0.05, 0.05), (0.35, 0.35)]),
        {"highway": "residential", "ref:FR:IGN:cleabs": "TRONROUT1"},
    )]
    builder.record_provenance(kind, wid, "troncon_de_route", {})
    kind, rid = builder.add_polygon(
        Polygon(
            [(0.1, 0.1), (0.4, 0.1), (0.4, 0.4), (0.1, 0.4), (0.1, 0.1)],
            [[(0.2, 0.2), (0.3, 0.2), (0.3, 0.3), (0.2, 0.3), (0.2, 0.2)]],
        ),
        {"building": "yes", "ref:FR:IGN:cleabs": "BATIMENT1"},
    )
    builder.record_provenance(kind, rid, "batiment", {})
    kind, cid = builder.add_polygon(
        Polygon([(0.0, 0.0), (0.4, 0.0), (0.4, 0.4), (0.0, 0.4), (0.0, 0.0)]),
        {"boundary": "administrative", "admin_level": "8", "ref:FR:IGN:cleabs": "COMMUNE_1"},
        mode="boundary",
    )
    builder.record_provenance(kind, cid, "commune", {})
    from shapely.geometry import Point
    builder.add_point(Point(0.15, 0.15), {"amenity": "bench"})  # sans provenance

    path = tmp_path / "couches.db"
    con = store.connect(path)
    store.load(con, builder, source_label="test")
    con.close()
    return path


def _resume(result):
    ways_tagged = sum(1 for w in result.ways if w["tags"])
    return {
        "relations": sorted(r["tags"].get("ref:FR:IGN:cleabs", "?") for r in result.relations),
        "ways": len(result.ways),
        "ways_tagues": ways_tagged,
        "nodes": len(result.nodes),
        "points": sorted(n["tags"].get("amenity", "?") for n in result.nodes if n["tags"]),
    }


def test_filtre_par_couche_ne_garde_que_le_module(db_couches):
    con = store.connect(db_couches, read_only=True)
    tout = _resume(store.query_map(con, BBOX))
    assert tout["relations"] == ["BATIMENT1", "COMMUNE_1"] and tout["ways"] == 4

    admin = _resume(store.query_map(con, BBOX, {"commune"}))
    # la relation commune, son way membre (sans provenance propre), ses nœuds,
    # et le banc créé à la main — jamais la route ni le bâtiment
    assert admin["relations"] == ["COMMUNE_1"]
    assert admin["ways"] == 1 and admin["ways_tagues"] == 0
    assert admin["points"] == ["bench"]
    assert admin["nodes"] == 4 + 1

    routes = _resume(store.query_map(con, BBOX, {"troncon_de_route"}))
    assert routes["relations"] == [] and routes["ways"] == 1 and routes["ways_tagues"] == 1

    bati = _resume(store.query_map(con, BBOX, {"batiment", "commune"}))
    assert bati["relations"] == ["BATIMENT1", "COMMUNE_1"] and bati["ways"] == 3
    con.close()


def test_api_filtre_par_parametre_ou_cookie(db_couches):
    client = TestClient(create_app(db_couches))
    bbox = ",".join(str(v) for v in BBOX)

    def cleabs(resp):
        return sorted(e["tags"]["ref:FR:IGN:cleabs"] for e in resp.json()["elements"]
                      if e.get("tags", {}).get("ref:FR:IGN:cleabs"))

    assert cleabs(client.get(f"/api/0.6/map.json?bbox={bbox}")) == ["BATIMENT1", "COMMUNE_1", "TRONROUT1"]
    assert cleabs(client.get(f"/api/0.6/map.json?bbox={bbox}&layers=commune")) == ["COMMUNE_1"]
    # le cookie posé par les modules (virgule encodée), supplanté par `layers=`
    client.cookies.set("bdf_layers", "commune%2Ctroncon_de_route")
    assert cleabs(client.get(f"/api/0.6/map.json?bbox={bbox}")) == ["COMMUNE_1", "TRONROUT1"]
    assert cleabs(client.get(f"/api/0.6/map.json?bbox={bbox}&layers=batiment")) == ["BATIMENT1"]


def test_chemin_sans_index_equivalent(db_couches):
    """Une base antérieure aux index de ways (ouverte en lecture seule) doit
    répondre la même chose par le chemin des nœuds."""
    con = store.connect(db_couches)
    assert store.has_spatial_index(con)
    with_index = {
        key: _resume(store.query_map(con, BBOX, layers))
        for key, layers in (("tout", None), ("admin", {"commune"}), ("routes", {"troncon_de_route"}))
    }
    con.execute("DROP TABLE way_index")
    con.execute("DROP TABLE point_index")
    con.commit()
    assert not store.has_spatial_index(con)
    for key, layers in (("tout", None), ("admin", {"commune"}), ("routes", {"troncon_de_route"})):
        assert _resume(store.query_map(con, BBOX, layers)) == with_index[key], key
    # et la mise à niveau les reconstruit
    store.ensure_schema(con)
    assert store.has_spatial_index(con)
    con.close()


def test_emprise_du_way_suit_ses_noeuds(db_couches):
    """Déplacer un nœud (osmChange) doit mettre à jour l'index du way."""
    from bdtopo_osm import edit

    con = store.connect(db_couches)
    way_id = con.execute(
        "SELECT element_id FROM idmap WHERE cleabs = 'TRONROUT1'"
    ).fetchone()[0]
    node_id = con.execute(
        "SELECT node_id FROM way_nodes WHERE way_id = ? ORDER BY seq DESC LIMIT 1", (way_id,)
    ).fetchone()[0]
    loin = (3.0, 3.0, 3.4, 3.4)
    assert not [w for w in store.query_map(con, loin).ways]

    cs = store.open_changeset(con, 1, {})
    payload = (
        '<osmChange version="0.6"><modify>'
        f'<node id="{node_id}" lon="3.2" lat="3.2" version="1" changeset="{cs}"/>'
        "</modify></osmChange>"
    ).encode()
    edit.apply_osmchange(con, payload, cs)
    assert [w["id"] for w in store.query_map(con, loin).ways] == [way_id]
    assert [w["id"] for w in store.query_map(con, loin, {"troncon_de_route"}).ways] == [way_id]
    con.close()
