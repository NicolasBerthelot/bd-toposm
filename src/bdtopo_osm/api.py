"""Serveur API OSM 0.6, sous-ensemble lecture.

iD n'utilise qu'une poignée d'endpoints ; les implémenter directement évite
d'installer le Rails port officiel (Ruby + PostgreSQL + Docker) pour une
démonstration départementale.

**iD parle JSON, pas XML.** Lecture faite de son code (`iD.js`) :

- il interroge `/api/capabilities.json`, jamais la variante XML ;
- il charge les données par `/api/0.6/map.json?bbox=`, en tuiles de zoom 16 ;
- il déréférence `payload.policy.imagery.blacklist.map(...)` sans garde, donc
  ce tableau doit exister même vide, sous peine d'exception au démarrage ;
- il lit `payload.api.status.api` : la valeur `readonly` lui fait masquer les
  outils d'édition proprement, plutôt que d'échouer à l'enregistrement.

Les variantes XML sont conservées : elles ne servent pas à iD, mais elles sont
le format attendu par JOSM et par les outils en ligne de commande.
"""
from __future__ import annotations

import gzip
import json
import sqlite3
import time
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

import html
import time as _time

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from . import auth, edit, store
from .osmxml import GENERATOR, sanitize

# Limite d'emprise de l'API OSM, en degrés carrés. iD la lit dans les
# capabilities et refuse de demander plus large.
MAX_AREA = 0.25
MAX_WAY_NODES = 2000
MAX_CHANGESET_ELEMENTS = 10000

# Taille du tampon de sortie. Starlette itère un générateur synchrone via son
# pool de threads : *chaque* `yield` paie un aller-retour thread/async. Rendre
# le XML balise par balise coûtait 58 280 yields et 25,6 s par requête, contre
# 0,19 s pour le même rendu en mémoire — un facteur 137. Le tampon ramène cela
# à quelques dizaines de yields, sans renoncer au streaming (indispensable à
# l'échelle du département, où la réponse se compte en centaines de Mo).
CHUNK_SIZE = 256 * 1024

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def _chunked(pieces: Iterator[str], size: int = CHUNK_SIZE) -> Iterator[str]:
    buffer: list[str] = []
    length = 0
    for piece in pieces:
        buffer.append(piece)
        length += len(piece)
        if length >= size:
            yield "".join(buffer)
            buffer = []
            length = 0
    if buffer:
        yield "".join(buffer)


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox.split(","))
    except ValueError:
        raise HTTPException(400, "bbox attendu : min_lon,min_lat,max_lon,max_lat")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(400, "emprise vide ou inversée")
    area = (max_lon - min_lon) * (max_lat - min_lat)
    if area > MAX_AREA:
        raise HTTPException(400, f"emprise de {area:.4f} degrés carrés, maximum {MAX_AREA}")
    return (min_lon, min_lat, max_lon, max_lat)


# ------------------------------------------------------------- capabilities


def capabilities_payload(readonly: bool) -> dict:
    return {
        "version": "0.6",
        "generator": GENERATOR,
        "api": {
            "version": {"minimum": "0.6", "maximum": "0.6"},
            "area": {"maximum": MAX_AREA},
            "note_area": {"maximum": 25},
            "tracepoints": {"per_page": 5000},
            "waynodes": {"maximum": MAX_WAY_NODES},
            "relationmembers": {"maximum": 32000},
            "changesets": {
                "maximum_elements": MAX_CHANGESET_ELEMENTS,
                "default_query_limit": 100,
                "maximum_query_limit": 500,
            },
            "timeout": {"seconds": 300},
            "status": {
                "database": "online",
                "api": "readonly" if readonly else "online",
                "gpx": "offline",
            },
        },
        # iD fait `policy.imagery.blacklist.map(...)` sans vérifier l'existence :
        # le tableau doit être présent, quitte à être vide.
        "policy": {"imagery": {"blacklist": []}},
    }


def capabilities_xml(readonly: bool) -> str:
    status = "readonly" if readonly else "online"
    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        f'<osm version="0.6" generator={quoteattr(GENERATOR)}>\n'
        "  <api>\n"
        '    <version minimum="0.6" maximum="0.6"/>\n'
        f'    <area maximum="{MAX_AREA}"/>\n'
        '    <note_area maximum="25"/>\n'
        '    <tracepoints per_page="5000"/>\n'
        f'    <waynodes maximum="{MAX_WAY_NODES}"/>\n'
        '    <relationmembers maximum="32000"/>\n'
        f'    <changesets maximum_elements="{MAX_CHANGESET_ELEMENTS}" '
        'default_query_limit="100" maximum_query_limit="500"/>\n'
        '    <timeout seconds="300"/>\n'
        f'    <status database="online" api="{status}" gpx="offline"/>\n'
        "  </api>\n"
        "  <policy>\n"
        "    <imagery/>\n"
        "  </policy>\n"
        "</osm>\n"
    )


# --------------------------------------------------------------------- map


def _tags_xml(tags: dict[str, str], indent: str) -> Iterator[str]:
    for key, value in tags.items():
        k, v = sanitize(key), sanitize(value)
        if k and v:
            yield f"{indent}<tag k={quoteattr(k)} v={quoteattr(v)}/>\n"


def _map_xml(result: store.MapResult, bbox: tuple[float, float, float, float]) -> Iterator[str]:
    min_lon, min_lat, max_lon, max_lat = bbox
    yield "<?xml version='1.0' encoding='UTF-8'?>\n"
    yield f'<osm version="0.6" generator={quoteattr(GENERATOR)} copyright="IGN BD TOPO">\n'
    yield (
        f'  <bounds minlat="{min_lat:.7f}" minlon="{min_lon:.7f}" '
        f'maxlat="{max_lat:.7f}" maxlon="{max_lon:.7f}"/>\n'
    )

    for node in result.nodes:
        head = (
            f'  <node id="{node["id"]}" visible="true" version="{node["version"]}" '
            f'changeset="1" timestamp="{node["timestamp"]}" '
            f'lat="{node["lat"]:.7f}" lon="{node["lon"]:.7f}"'
        )
        if not node["tags"]:
            yield head + "/>\n"
        else:
            yield head + ">\n"
            yield from _tags_xml(node["tags"], "    ")
            yield "  </node>\n"

    for way in result.ways:
        yield (
            f'  <way id="{way["id"]}" visible="true" version="{way["version"]}" '
            f'changeset="1" timestamp="{way["timestamp"]}">\n'
        )
        for ref in way["nodes"]:
            yield f'    <nd ref="{ref}"/>\n'
        yield from _tags_xml(way["tags"], "    ")
        yield "  </way>\n"

    for relation in result.relations:
        yield (
            f'  <relation id="{relation["id"]}" visible="true" '
            f'version="{relation["version"]}" changeset="1" '
            f'timestamp="{relation["timestamp"]}">\n'
        )
        for member in relation["members"]:
            yield (
                f'    <member type="{member["type"]}" ref="{member["ref"]}" '
                f"role={quoteattr(member['role'])}/>\n"
            )
        yield from _tags_xml(relation["tags"], "    ")
        yield "  </relation>\n"

    yield "</osm>\n"


def _dump(element: dict) -> str:
    return json.dumps(element, ensure_ascii=False, separators=(",", ":"))


def _map_json(result: store.MapResult) -> Iterator[str]:
    """Format OSM JSON attendu par iD : `{version, generator, elements: [...]}`.

    Les champs suivent ses parseurs : un way porte `nodes` (identifiants
    numériques), une relation porte `members` ([{type, ref, role}]). `visible`
    est omis — iD le considère vrai par défaut.
    """
    yield f'{{"version":"0.6","generator":{json.dumps(GENERATOR)},"elements":['
    first = True

    def separator() -> str:
        nonlocal first
        if first:
            first = False
            return ""
        return ","

    for node in result.nodes:
        element = {
            "type": "node",
            "id": node["id"],
            "lat": node["lat"],
            "lon": node["lon"],
            "version": node["version"],
            "timestamp": node["timestamp"],
        }
        if node["tags"]:
            element["tags"] = node["tags"]
        yield separator() + _dump(element)

    for way in result.ways:
        element = {
            "type": "way",
            "id": way["id"],
            "version": way["version"],
            "timestamp": way["timestamp"],
            "nodes": way["nodes"],
        }
        if way["tags"]:
            element["tags"] = way["tags"]
        yield separator() + _dump(element)

    for relation in result.relations:
        element = {
            "type": "relation",
            "id": relation["id"],
            "version": relation["version"],
            "timestamp": relation["timestamp"],
            "members": relation["members"],
        }
        if relation["tags"]:
            element["tags"] = relation["tags"]
        yield separator() + _dump(element)

    yield "]}"


# ------------------------------------------------------------- application


def create_app(
    db_path: str | Path,
    *,
    readonly: bool = True,
    id_dir: Path | None = None,
    demo_password: str | None = None,
    ephemeral: bool = False,
) -> FastAPI:
    """`demo_password` : si fourni, `/oauth2/authorize` exige ce mot de passe
    avant de délivrer un code. C'est la seule barrière d'une instance publique.
    `ephemeral` : signale dans la page de connexion que les modifications ne
    survivent pas au redémarrage (disque éphémère d'un hébergeur gratuit)."""
    app = FastAPI(title="bdtopo-osm API 0.6", docs_url=None, redoc_url=None)
    app.state.db_path = Path(db_path)
    app.state.readonly = readonly
    app.state.auth = auth.AuthStore()
    app.state.demo_password = demo_password
    app.state.ephemeral = ephemeral

    if not readonly:
        # Une base convertie avant l'ajout de l'écriture n'a ni `changesets`
        # ni `sequences` : on la met à niveau avant d'accepter la moindre
        # requête, plutôt que d'échouer au premier enregistrement.
        migration = store.connect(app.state.db_path)
        try:
            store.ensure_schema(migration)
        finally:
            migration.close()

    def connection() -> sqlite3.Connection:
        # Une connexion par requête : SQLite en WAL supporte les lectures
        # concurrentes, et cela évite de partager un curseur entre threads.
        return store.connect(app.state.db_path, read_only=True)

    # ---------------------------------------------------------- capabilities

    @app.get("/api/capabilities.json")
    @app.get("/api/0.6/capabilities.json")
    def capabilities_json() -> dict:
        return capabilities_payload(app.state.readonly)

    @app.get("/api/capabilities")
    @app.get("/api/0.6/capabilities")
    def capabilities() -> StreamingResponse:
        return StreamingResponse(
            iter([capabilities_xml(app.state.readonly)]), media_type="text/xml"
        )

    @app.get("/api/versions")
    def versions() -> StreamingResponse:
        body = (
            "<?xml version='1.0' encoding='UTF-8'?>\n"
            f'<osm generator={quoteattr(GENERATOR)}>\n'
            "  <api><version>0.6</version></api>\n"
            "</osm>\n"
        )
        return StreamingResponse(iter([body]), media_type="text/xml")

    # ------------------------------------------------------------------ map

    def _query(bbox: str):
        box = parse_bbox(bbox)
        con = connection()
        return con, box, store.query_map(con, box)

    @app.get("/api/0.6/map.json")
    def map_json(bbox: str = Query(..., description="min_lon,min_lat,max_lon,max_lat")):
        con, _, result = _query(bbox)

        def stream() -> Iterator[str]:
            try:
                yield from _chunked(_map_json(result))
            finally:
                con.close()

        return StreamingResponse(stream(), media_type="application/json")

    @app.get("/api/0.6/map")
    def map_xml(bbox: str = Query(..., description="min_lon,min_lat,max_lon,max_lat")):
        con, box, result = _query(bbox)

        def stream() -> Iterator[str]:
            try:
                yield from _chunked(_map_xml(result, box))
            finally:
                con.close()

        return StreamingResponse(stream(), media_type="text/xml")

    # ---------------------------------------------------------------- OAuth2

    def require_write(authorization: str | None = Header(default=None)) -> int:
        """Porte d'entrée de toute écriture. Renvoie l'identifiant utilisateur."""
        if app.state.readonly:
            raise HTTPException(403, "instance ouverte en lecture seule")
        if not app.state.auth.validate(auth.bearer_token(authorization)):
            raise HTTPException(401, "jeton absent ou invalide")
        return auth.SYNTHETIC_USER["id"]

    def _check_redirect(request: Request, redirect_uri: str):
        # Un `redirect_uri` arbitraire ferait de cet endpoint une redirection
        # ouverte. On n'accepte que la propre origine du serveur : iD y pointe
        # `land.html`, qui est servi par nous. Derrière un proxy TLS, uvicorn
        # doit être lancé avec proxy_headers pour que `request.url` reflète
        # l'origine vue par le navigateur (cf. cli `--behind-proxy`).
        # X-Forwarded-Host prime si un proxy l'envoie ; uvicorn ne réécrit que
        # le schéma. Un client qui le forgerait ne tromperait que lui-même : la
        # redirection ne part que vers l'adresse qu'il a lui-même fournie.
        netloc = request.headers.get("x-forwarded-host") or request.url.netloc
        origin = f"{request.url.scheme}://{netloc}"
        target = urlparse(redirect_uri)
        if f"{target.scheme}://{target.netloc}" != origin:
            raise HTTPException(400, "redirect_uri hors de cette instance")
        return target

    def _grant(redirect_uri: str, target, state: str, challenge, method):
        code = app.state.auth.issue_code(redirect_uri, challenge, method)
        separator = "&" if target.query else "?"
        return RedirectResponse(
            f"{redirect_uri}{separator}{urlencode({'code': code, 'state': state})}",
            status_code=302,
        )

    def _login_page(params: dict, error: str | None = None) -> HTMLResponse:
        hidden = "".join(
            f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(v)}">'
            for k, v in params.items()
            if v is not None
        )
        note = (
            "Les modifications sont réinitialisées à chaque redémarrage de la démo."
            if app.state.ephemeral
            else ""
        )
        body = auth.LOGIN_PAGE.format(
            hidden=hidden,
            error=f'<p class="err">{html.escape(error)}</p>' if error else "",
            ephemeral=note,
        )
        return HTMLResponse(body, status_code=401 if error else 200)

    @app.get("/oauth2/authorize")
    def oauth_authorize(
        request: Request,
        redirect_uri: str = Query(...),
        state: str = Query(default=""),
        code_challenge: str | None = Query(default=None),
        code_challenge_method: str | None = Query(default=None),
    ):
        target = _check_redirect(request, redirect_uri)
        if app.state.demo_password:
            # La fenêtre qu'iD ouvre pour « se connecter » affiche ce formulaire :
            # le mot de passe s'insère dans le protocole sans le modifier.
            return _login_page(
                {
                    "redirect_uri": redirect_uri,
                    "state": state,
                    "code_challenge": code_challenge,
                    "code_challenge_method": code_challenge_method,
                }
            )
        return _grant(redirect_uri, target, state, code_challenge, code_challenge_method)

    @app.post("/oauth2/authorize")
    def oauth_authorize_submit(
        request: Request,
        password: str = Form(...),
        redirect_uri: str = Form(...),
        state: str = Form(default=""),
        code_challenge: str | None = Form(default=None),
        code_challenge_method: str | None = Form(default=None),
    ):
        target = _check_redirect(request, redirect_uri)
        if not app.state.demo_password:
            raise HTTPException(404)
        if not auth.password_matches(password, app.state.demo_password):
            _time.sleep(0.8)  # freine l'énumération sans coûter à l'usager honnête
            return _login_page(
                {
                    "redirect_uri": redirect_uri,
                    "state": state,
                    "code_challenge": code_challenge,
                    "code_challenge_method": code_challenge_method,
                },
                error="Mot de passe incorrect.",
            )
        return _grant(redirect_uri, target, state, code_challenge, code_challenge_method)

    @app.post("/oauth2/token")
    def oauth_token(
        code: str = Query(...),
        code_verifier: str | None = Query(default=None),
        grant_type: str = Query(default="authorization_code"),
    ) -> dict:
        # iD transmet ces paramètres dans la query string, avec un corps vide.
        if grant_type != "authorization_code":
            raise HTTPException(400, f"grant_type non géré : {grant_type}")
        try:
            token = app.state.auth.exchange(code, code_verifier)
        except ValueError as err:
            raise HTTPException(400, str(err))
        return {
            "access_token": token,
            "token_type": "Bearer",
            "scope": "read_prefs write_prefs write_api read_gpx write_notes",
            "created_at": int(time.time()),
        }

    # ------------------------------------------------------------ utilisateur

    @app.get("/api/0.6/user/details.json")
    def user_details(user_id: int = Depends(require_write)) -> dict:
        con = connection()
        try:
            user = dict(auth.SYNTHETIC_USER)
            user["changesets"] = {
                "count": con.execute(
                    "SELECT count(*) FROM changesets WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
            }
            # `parseUserJSON` d'iD exige la clé `user` à la racine.
            return {"version": "0.6", "generator": GENERATOR, "user": user}
        finally:
            con.close()

    @app.get("/api/0.6/changesets.json")
    def user_changesets(
        user: int = Query(default=1), _: int = Depends(require_write)
    ) -> dict:
        con = connection()
        try:
            return {
                "version": "0.6",
                "generator": GENERATOR,
                "changesets": store.changesets_for_user(con, user),
            }
        finally:
            con.close()

    # ------------------------------------------------------------ changesets

    async def read_body(request: Request) -> bytes:
        """Corps de la requête, décompressé si besoin.

        iD compresse l'osmChange quand le navigateur expose `CompressionStream`
        et pose `Content-Encoding: gzip`. Starlette ne décompresse pas les corps
        entrants : sans cette étape, le parseur XML reçoit des octets gzip et
        l'enregistrement échoue avec une erreur de syntaxe déroutante.
        """
        raw = await request.body()
        if request.headers.get("content-encoding", "").lower() == "gzip":
            try:
                return gzip.decompress(raw)
            except OSError as err:
                raise HTTPException(400, f"corps gzip illisible : {err}")
        return raw

    def open_changeset_or_fail(con: sqlite3.Connection, changeset_id: int, user_id: int):
        row = store.changeset(con, changeset_id)
        if row is None:
            raise HTTPException(404, f"changeset {changeset_id} inconnu")
        if row["user_id"] != user_id:
            raise HTTPException(409, f"le changeset {changeset_id} appartient à un autre compte")
        if not row["open"]:
            raise HTTPException(409, f"le changeset {changeset_id} est déjà clos")
        return row

    def _changeset_tags(payload: bytes) -> dict[str, str]:
        try:
            root = ET.fromstring(payload) if payload.strip() else None
        except ET.ParseError as err:
            raise HTTPException(400, f"changeset illisible : {err}")
        if root is None:
            return {}
        node = root.find("changeset") if root.tag == "osm" else root
        if node is None:
            return {}
        return {
            tag.get("k"): tag.get("v")
            for tag in node.findall("tag")
            if tag.get("k") and tag.get("v") is not None
        }

    @app.put("/api/0.6/changeset/create")
    async def changeset_create(request: Request, user_id: int = Depends(require_write)):
        tags = _changeset_tags(await read_body(request))
        con = store.connect(app.state.db_path)
        try:
            changeset_id = store.open_changeset(con, user_id, tags)
        finally:
            con.close()
        # L'API OSM renvoie l'identifiant en texte brut, pas en XML.
        return PlainTextResponse(str(changeset_id))

    @app.put("/api/0.6/changeset/{changeset_id}")
    async def changeset_update(
        changeset_id: int, request: Request, user_id: int = Depends(require_write)
    ):
        tags = _changeset_tags(await read_body(request))
        con = store.connect(app.state.db_path)
        try:
            open_changeset_or_fail(con, changeset_id, user_id)
            con.executemany(
                "INSERT OR REPLACE INTO changeset_tags (changeset_id, k, v) VALUES (?, ?, ?)",
                [(changeset_id, k, v) for k, v in tags.items()],
            )
            con.commit()
        finally:
            con.close()
        return PlainTextResponse(str(changeset_id))

    @app.post("/api/0.6/changeset/{changeset_id}/upload")
    async def changeset_upload(
        changeset_id: int, request: Request, user_id: int = Depends(require_write)
    ):
        payload = await read_body(request)
        con = store.connect(app.state.db_path)
        try:
            open_changeset_or_fail(con, changeset_id, user_id)
            try:
                entries = edit.apply_osmchange(
                    con, payload, changeset_id, MAX_CHANGESET_ELEMENTS
                )
            except edit.OsmApiError as err:
                # Les codes portent le sens : 409 conflit de version,
                # 412 intégrité référentielle, 410 objet déjà supprimé.
                return PlainTextResponse(err.message, status_code=err.status)
            return Response(edit.diff_result_xml(entries), media_type="text/xml")
        finally:
            con.close()

    @app.put("/api/0.6/changeset/{changeset_id}/close")
    def changeset_close(changeset_id: int, user_id: int = Depends(require_write)):
        con = store.connect(app.state.db_path)
        try:
            open_changeset_or_fail(con, changeset_id, user_id)
            store.close_changeset(con, changeset_id)
        finally:
            con.close()
        return PlainTextResponse("")

    # ----------------------------------------------------------- diagnostic

    @app.get("/status")
    def status() -> dict:
        con = connection()
        try:
            return {
                "readonly": app.state.readonly,
                "counts": store.counts(con),
                "bounds": store.bounds(con),
                "changesets": con.execute("SELECT count(*) FROM changesets").fetchone()[0],
                "meta": {r["key"]: r["value"] for r in con.execute("SELECT key, value FROM meta")},
            }
        finally:
            con.close()

    # ------------------------------------------------------------------- iD

    if id_dir is not None and Path(id_dir).is_dir():
        id_dir = Path(id_dir)
        # Page d'accueil maison si elle existe (elle branche iD sur cette API),
        # sinon celle livrée avec le build, qui pointerait sur openstreetmap.org.
        custom_index = WEB_DIR / "index.html"
        index_file = custom_index if custom_index.exists() else id_dir / "index.html"

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(index_file, media_type="text/html")

        # Monté à la racine : `assetPath('')` d'iD résout ses ressources en
        # relatif depuis la page, donc `/iD.min.js`, `/img/...`, `/locales/...`.
        app.mount("/", StaticFiles(directory=id_dir), name="id")

    return app
