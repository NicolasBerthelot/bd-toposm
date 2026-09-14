from __future__ import annotations

import base64
import gzip
import hashlib
from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Polygon

from bdtopo_osm import store
from bdtopo_osm.api import create_app
from bdtopo_osm.topology import MemoryBuilder

BBOX = "0.0,0.0,0.4,0.4"

VERIFIER = "verificateur-pkce-suffisamment-long-pour-etre-credible-0123456789"
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
)


@pytest.fixture
def db(tmp_path):
    builder = MemoryBuilder()
    builder.add_linestring(
        LineString([(0.05, 0.05), (0.15, 0.15), (0.25, 0.25)]),
        {"highway": "residential", "name": "Rue de Test", "ref:FR:IGN:cleabs": "TR1"},
    )
    builder.add_polygon(
        Polygon([(0.30, 0.30), (0.34, 0.30), (0.34, 0.34), (0.30, 0.34), (0.30, 0.30)]),
        {"building": "house", "ref:FR:IGN:cleabs": "BA1"},
    )
    path = tmp_path / "edit.db"
    con = store.connect(path)
    store.load(con, builder, source_label="test")
    con.close()
    return path


@pytest.fixture
def client(db):
    return TestClient(create_app(db, readonly=False))


@pytest.fixture
def token(client):
    """Parcourt le vrai circuit OAuth2 PKCE plutôt que d'injecter un jeton."""
    r = client.get(
        "/oauth2/authorize",
        params={
            "redirect_uri": "http://testserver/land.html",
            "state": "xyz",
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    query = dict(p.split("=", 1) for p in r.headers["location"].split("?")[1].split("&"))
    assert query["state"] == "xyz"

    r = client.post(
        "/oauth2/token",
        params={"code": query["code"], "code_verifier": VERIFIER},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def open_changeset(client, token, comment="essai"):
    r = client.put(
        "/api/0.6/changeset/create",
        headers=auth_headers(token),
        content=f'<osm><changeset><tag k="comment" v="{comment}"/></changeset></osm>',
    )
    assert r.status_code == 200
    return int(r.text)


def upload(client, token, changeset_id, body, compress=False):
    headers = {**auth_headers(token), "Content-Type": "text/xml"}
    payload = body.encode("utf-8")
    if compress:
        payload = gzip.compress(payload)
        headers["Content-Encoding"] = "gzip"
    return client.post(
        f"/api/0.6/changeset/{changeset_id}/upload", headers=headers, content=payload
    )


def elements(client, kind=None):
    payload = client.get("/api/0.6/map.json", params={"bbox": BBOX}).json()["elements"]
    return [e for e in payload if kind is None or e["type"] == kind]


# ------------------------------------------------------------------- OAuth2


def test_pkce_verifie_reellement(client):
    r = client.get(
        "/oauth2/authorize",
        params={
            "redirect_uri": "http://testserver/land.html",
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    code = dict(p.split("=", 1) for p in r.headers["location"].split("?")[1].split("&"))["code"]
    r = client.post("/oauth2/token", params={"code": code, "code_verifier": "mauvais"})
    assert r.status_code == 400


def test_code_a_usage_unique(client, token):
    """Un code déjà échangé ne doit plus valoir."""
    r = client.get(
        "/oauth2/authorize",
        params={"redirect_uri": "http://testserver/land.html", "code_challenge": CHALLENGE,
                "code_challenge_method": "S256"},
        follow_redirects=False,
    )
    code = dict(p.split("=", 1) for p in r.headers["location"].split("?")[1].split("&"))["code"]
    assert client.post("/oauth2/token", params={"code": code, "code_verifier": VERIFIER}).status_code == 200
    assert client.post("/oauth2/token", params={"code": code, "code_verifier": VERIFIER}).status_code == 400


def test_redirection_ouverte_refusee(client):
    """Sans ce garde-fou, l'endpoint serait une redirection ouverte."""
    r = client.get(
        "/oauth2/authorize",
        params={"redirect_uri": "https://exemple.invalide/vol", "code_challenge": CHALLENGE},
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_ecriture_refusee_sans_jeton(client):
    assert client.put("/api/0.6/changeset/create", content="<osm/>").status_code == 401


def test_ecriture_refusee_en_lecture_seule(db, token):
    lecture_seule = TestClient(create_app(db, readonly=True))
    r = lecture_seule.put(
        "/api/0.6/changeset/create", headers=auth_headers(token), content="<osm/>"
    )
    assert r.status_code in (401, 403)


def test_user_details_expose_la_cle_user(client, token):
    payload = client.get("/api/0.6/user/details.json", headers=auth_headers(token)).json()
    # `parseUserJSON` d'iD refuse une charge sans `user`.
    assert payload["user"]["id"] == 1
    assert payload["user"]["display_name"]


# ------------------------------------------------------------------ création


def test_creation_noeud_et_identifiant_de_remplacement(client, token):
    cs = open_changeset(client, token)
    r = upload(
        client,
        token,
        cs,
        f"""<osmChange version="0.6" generator="iD">
          <create>
            <node id="-1" lon="0.2" lat="0.2" version="0" changeset="{cs}">
              <tag k="amenity" v="bench"/>
            </node>
          </create>
        </osmChange>""",
    )
    assert r.status_code == 200, r.text

    diff = ET.fromstring(r.text)
    entry = diff.find("node")
    assert entry.get("old_id") == "-1"
    nouvel_id = int(entry.get("new_id"))
    assert nouvel_id > 0
    assert entry.get("new_version") == "1"

    banc = [e for e in elements(client, "node") if e.get("tags", {}).get("amenity") == "bench"]
    assert len(banc) == 1 and banc[0]["id"] == nouvel_id


def test_identifiants_negatifs_resolus_dans_les_references(client, token):
    """Un way créé référence ses nœuds par identifiants négatifs."""
    cs = open_changeset(client, token)
    r = upload(
        client,
        token,
        cs,
        f"""<osmChange version="0.6" generator="iD">
          <create>
            <node id="-1" lon="0.10" lat="0.20" version="0" changeset="{cs}"/>
            <node id="-2" lon="0.12" lat="0.20" version="0" changeset="{cs}"/>
            <way id="-3" version="0" changeset="{cs}">
              <nd ref="-1"/><nd ref="-2"/>
              <tag k="highway" v="footway"/>
            </way>
          </create>
        </osmChange>""",
    )
    assert r.status_code == 200, r.text

    diff = ET.fromstring(r.text)
    ids = {e.get("old_id"): int(e.get("new_id")) for e in diff}
    chemin = next(w for w in elements(client, "way") if w.get("tags", {}).get("highway") == "footway")
    assert chemin["id"] == ids["-3"]
    assert chemin["nodes"] == [ids["-1"], ids["-2"]]


def test_reference_negative_non_declaree_refusee(client, token):
    cs = open_changeset(client, token)
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><create>
              <way id="-3" version="0" changeset="{cs}"><nd ref="-9"/><nd ref="-8"/></way>
            </create></osmChange>""",
    )
    assert r.status_code == 412


def test_upload_gzip(client, token):
    """iD compresse l'osmChange quand le navigateur le permet."""
    cs = open_changeset(client, token)
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><create>
              <node id="-1" lon="0.21" lat="0.21" version="0" changeset="{cs}">
                <tag k="amenity" v="waste_basket"/>
              </node>
            </create></osmChange>""",
        compress=True,
    )
    assert r.status_code == 200, r.text
    assert any(
        e.get("tags", {}).get("amenity") == "waste_basket" for e in elements(client, "node")
    )


# ---------------------------------------------------------------- modification


def test_modification_incremente_la_version(client, token):
    batiment = next(w for w in elements(client, "way") if w.get("tags", {}).get("building"))
    cs = open_changeset(client, token)
    nds = "".join(f'<nd ref="{n}"/>' for n in batiment["nodes"])
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><modify>
              <way id="{batiment['id']}" version="{batiment['version']}" changeset="{cs}">
                {nds}<tag k="building" v="house"/><tag k="name" v="Maison Dupont"/>
              </way>
            </modify></osmChange>""",
    )
    assert r.status_code == 200, r.text

    apres = next(w for w in elements(client, "way") if w["id"] == batiment["id"])
    assert apres["tags"]["name"] == "Maison Dupont"
    assert apres["version"] == batiment["version"] + 1


def test_version_perimee_donne_409(client, token):
    """Le cœur de la détection de conflit : quelqu'un est passé avant."""
    batiment = next(w for w in elements(client, "way") if w.get("tags", {}).get("building"))
    cs = open_changeset(client, token)
    nds = "".join(f'<nd ref="{n}"/>' for n in batiment["nodes"])
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><modify>
              <way id="{batiment['id']}" version="99" changeset="{cs}">{nds}
                <tag k="building" v="yes"/>
              </way>
            </modify></osmChange>""",
    )
    assert r.status_code == 409
    assert "Version mismatch" in r.text


# ----------------------------------------------------------------- suppression


def test_suppression_noeud_encore_utilise_donne_412(client, token):
    route = next(w for w in elements(client, "way") if w.get("tags", {}).get("highway"))
    noeud_id = route["nodes"][0]
    noeud = next(n for n in elements(client, "node") if n["id"] == noeud_id)
    cs = open_changeset(client, token)
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><delete>
              <node id="{noeud_id}" version="{noeud['version']}" changeset="{cs}"
                    lon="{noeud['lon']}" lat="{noeud['lat']}"/>
            </delete></osmChange>""",
    )
    assert r.status_code == 412
    assert str(route["id"]) in r.text


def test_if_unused_epargne_sans_echouer(client, token):
    """`if-unused` demande de ne pas supprimer plutôt que d'échouer."""
    route = next(w for w in elements(client, "way") if w.get("tags", {}).get("highway"))
    noeud_id = route["nodes"][0]
    noeud = next(n for n in elements(client, "node") if n["id"] == noeud_id)
    cs = open_changeset(client, token)
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><delete if-unused="true">
              <node id="{noeud_id}" version="{noeud['version']}" changeset="{cs}"
                    lon="{noeud['lon']}" lat="{noeud['lat']}"/>
            </delete></osmChange>""",
    )
    assert r.status_code == 200, r.text
    entry = ET.fromstring(r.text).find("node")
    assert entry.get("new_id") == str(noeud_id)  # survivant, donc renvoyé inchangé
    assert any(n["id"] == noeud_id for n in elements(client, "node"))


def test_suppression_noeud_libre(client, token):
    cs = open_changeset(client, token)
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><create>
              <node id="-1" lon="0.22" lat="0.22" version="0" changeset="{cs}">
                <tag k="amenity" v="bench"/></node>
            </create></osmChange>""",
    )
    nouvel_id = int(ET.fromstring(r.text).find("node").get("new_id"))

    cs2 = open_changeset(client, token)
    r = upload(
        client, token, cs2,
        f"""<osmChange version="0.6"><delete>
              <node id="{nouvel_id}" version="1" changeset="{cs2}" lon="0.22" lat="0.22"/>
            </delete></osmChange>""",
    )
    assert r.status_code == 200, r.text
    entry = ET.fromstring(r.text).find("node")
    assert entry.get("new_id") is None  # supprimé : pas de nouvelle version
    assert not any(n["id"] == nouvel_id for n in elements(client, "node"))


def test_identifiant_supprime_non_reattribue(client, token):
    """Réemployer l'identifiant d'un objet supprimé ferait pointer les
    références obsolètes d'un client vers un objet sans rapport."""
    cs = open_changeset(client, token)
    r = upload(client, token, cs,
        f"""<osmChange version="0.6"><create>
              <node id="-1" lon="0.23" lat="0.23" version="0" changeset="{cs}"/>
            </create></osmChange>""")
    premier = int(ET.fromstring(r.text).find("node").get("new_id"))

    upload(client, token, cs,
        f"""<osmChange version="0.6"><delete>
              <node id="{premier}" version="1" changeset="{cs}" lon="0.23" lat="0.23"/>
            </delete></osmChange>""")

    r = upload(client, token, cs,
        f"""<osmChange version="0.6"><create>
              <node id="-2" lon="0.24" lat="0.24" version="0" changeset="{cs}"/>
            </create></osmChange>""")
    second = int(ET.fromstring(r.text).find("node").get("new_id"))
    assert second > premier


# ------------------------------------------------------------------ atomicité


def test_diff_partiellement_invalide_n_applique_rien(client, token):
    """Un échec au dernier élément doit annuler les précédents.

    Sans cela, un way pourrait rester en base en pointant vers un nœud qui
    n'a jamais été créé.
    """
    avant = len(elements(client, "node"))
    cs = open_changeset(client, token)
    r = upload(
        client, token, cs,
        f"""<osmChange version="0.6"><create>
              <node id="-1" lon="0.26" lat="0.26" version="0" changeset="{cs}">
                <tag k="amenity" v="fountain"/></node>
              <node id="-2" lon="0.27" lat="0.27" version="0" changeset="{cs}"/>
              <way id="-3" version="0" changeset="{cs}"><nd ref="-1"/><nd ref="-77"/></way>
            </create></osmChange>""",
    )
    assert r.status_code == 412
    assert len(elements(client, "node")) == avant
    assert not any(
        e.get("tags", {}).get("amenity") == "fountain" for e in elements(client, "node")
    )


# ------------------------------------------------------------------ changesets


def test_changeset_clos_refuse_l_upload(client, token):
    cs = open_changeset(client, token)
    assert client.put(
        f"/api/0.6/changeset/{cs}/close", headers=auth_headers(token)
    ).status_code == 200
    r = upload(client, token, cs, '<osmChange version="0.6"><create/></osmChange>')
    assert r.status_code == 409


def test_changesets_json_pour_id(client, token):
    open_changeset(client, token, comment="premier essai")
    payload = client.get(
        "/api/0.6/changesets.json", params={"user": 1}, headers=auth_headers(token)
    ).json()
    # iD filtre sur `tags.comment` : sans cette clé le changeset est ignoré.
    assert any(c["tags"].get("comment") == "premier essai" for c in payload["changesets"])


def test_changeset_compte_les_modifications(client, token):
    cs = open_changeset(client, token)
    upload(client, token, cs,
        f"""<osmChange version="0.6"><create>
              <node id="-1" lon="0.28" lat="0.28" version="0" changeset="{cs}"/>
              <node id="-2" lon="0.29" lat="0.29" version="0" changeset="{cs}"/>
            </create></osmChange>""")
    payload = client.get(
        "/api/0.6/changesets.json", params={"user": 1}, headers=auth_headers(token)
    ).json()
    courant = next(c for c in payload["changesets"] if c["id"] == cs)
    assert courant["changes_count"] == 2


# ------------------------------------------------------ mot de passe de démo


@pytest.fixture
def client_demo(db):
    return TestClient(create_app(db, readonly=False, demo_password="sesame", ephemeral=True))


AUTHZ = {"redirect_uri": "http://testserver/land.html", "state": "s1",
         "code_challenge": CHALLENGE, "code_challenge_method": "S256"}


def test_avec_mot_de_passe_authorize_affiche_un_formulaire(client_demo):
    r = client_demo.get("/oauth2/authorize", params=AUTHZ, follow_redirects=False)
    assert r.status_code == 200
    assert 'name="password"' in r.text
    assert 'name="code_challenge"' in r.text            # le contexte OAuth est conservé
    assert "réinitialisées" in r.text                   # mention du disque éphémère


def test_mauvais_mot_de_passe_refuse_sans_code(client_demo):
    r = client_demo.post("/oauth2/authorize", data={**AUTHZ, "password": "faux"}, follow_redirects=False)
    assert r.status_code == 401
    assert "incorrect" in r.text
    assert "code=" not in r.headers.get("location", "")


def test_bon_mot_de_passe_delivre_un_code_puis_un_jeton(client_demo):
    r = client_demo.post("/oauth2/authorize", data={**AUTHZ, "password": "sesame"}, follow_redirects=False)
    assert r.status_code == 302
    query = dict(p.split("=", 1) for p in r.headers["location"].split("?")[1].split("&"))
    assert query["state"] == "s1"
    r = client_demo.post("/oauth2/token", params={"code": query["code"], "code_verifier": VERIFIER})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert client_demo.put(
        "/api/0.6/changeset/create", headers=auth_headers(token), content="<osm/>"
    ).status_code == 200


def test_sans_mot_de_passe_le_formulaire_n_existe_pas(client):
    r = client.post("/oauth2/authorize", data={**AUTHZ, "password": "x"}, follow_redirects=False)
    assert r.status_code == 404


# ------------------------------------------------------------ explication


def test_explain_rejoue_les_regles_sur_la_provenance(tmp_path):
    """Chaque tag d'un objet converti doit pouvoir dire d'où il vient."""
    from bdtopo_osm.pipeline import _emit, _plain_attributes
    from bdtopo_osm.mapping import RuleSet
    from bdtopo_osm.pipeline import RULES_DIR

    rules = RuleSet.load(RULES_DIR / "troncon_de_route.yaml")
    feature = {"cleabs": "TRONROUT42", "nature": "Route empierrée", "importance": "5",
               "sens_de_circulation": "Double sens", "nombre_de_voies": 1.0, "urbain": False,
               "etat_de_l_objet": "En service", "fictif": False, "position_par_rapport_au_sol": "0"}
    tags = rules.apply(feature)
    builder = MemoryBuilder()
    created = _emit(builder, LineString([(0.1, 0.1), (0.2, 0.2)]), tags)
    used = sorted(rules.referenced_fields() & set(feature))
    for kind, eid in created:
        builder.record_provenance(kind, eid, "troncon_de_route", _plain_attributes(feature, used))

    path = tmp_path / "prov.db"
    con = store.connect(path); store.load(con, builder); con.close()

    client = TestClient(create_app(path, readonly=True))
    r = client.get(f"/api/bdfrance/explain/way/{created[0][1]}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["layer"] == "troncon_de_route"
    hw = body["tags"]["highway"]
    assert hw["value"] == "unclassified"
    assert hw["fields"] == {"nature": "Route empierrée"}
    assert "Route empierrée" in hw["condition"]
    assert "unclassified" in hw["motif"]          # le motif rédigé est restitué
    assert body["tags"]["surface"]["value"] == "unpaved"
    assert body["tags"]["lanes"]["fields"] == {"nombre_de_voies": 1.0}

    assert client.get("/api/bdfrance/explain/way/999999").status_code == 404
