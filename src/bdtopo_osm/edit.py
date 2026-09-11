"""Application d'un document osmChange à la base.

C'est la partie de l'API 0.6 où la sémantique compte vraiment. Quatre règles
gouvernent l'opération, toutes reprises du serveur OSM :

1. **Atomicité.** Un diff s'applique en entier ou pas du tout. Un échec au
   milieu laisserait des ways pointant vers des nœuds inexistants.
2. **Identifiants de remplacement.** Les objets créés arrivent avec des
   identifiants négatifs, y compris dans les références (`<nd ref="-3"/>`).
   Le serveur alloue les vrais identifiants et les renvoie dans le diffResult ;
   l'éditeur s'en sert pour recoller ses objets locaux.
3. **Détection de conflit par version.** Le client annonce la version sur
   laquelle il a travaillé. Si elle ne correspond plus, c'est 409 — quelqu'un
   d'autre est passé avant.
4. **Intégrité référentielle.** Supprimer un nœud encore porté par un chemin
   trouerait la géométrie : 412, sauf `if-unused` qui demande de laisser
   l'élément en place sans échouer.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

from . import store
from .osmxml import GENERATOR

ELEMENT_KINDS = ("node", "way", "relation")


class OsmApiError(Exception):
    """Erreur portant le code HTTP que l'API OSM renverrait."""

    status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Conflict(OsmApiError):
    status = 409


class Gone(OsmApiError):
    status = 410


class Precondition(OsmApiError):
    status = 412


@dataclass
class DiffEntry:
    kind: str
    old_id: int
    new_id: int | None = None
    new_version: int | None = None


def _tags(element: ET.Element) -> dict[str, str]:
    return {
        tag.get("k"): tag.get("v")
        for tag in element.findall("tag")
        if tag.get("k") and tag.get("v") is not None
    }


def _int_attr(element: ET.Element, name: str, default: int | None = None) -> int:
    raw = element.get(name)
    if raw is None:
        if default is None:
            raise OsmApiError(f"attribut {name!r} manquant sur <{element.tag}>")
        return default
    try:
        return int(raw)
    except ValueError:
        raise OsmApiError(f"attribut {name}={raw!r} invalide sur <{element.tag}>")


class _Applier:
    def __init__(self, con: sqlite3.Connection, changeset_id: int, max_elements: int):
        self.con = con
        self.changeset_id = changeset_id
        self.max_elements = max_elements
        self.placeholders: dict[tuple[str, int], int] = {}
        self.diff: list[DiffEntry] = []
        self.touched = 0
        self.bbox: list[float] | None = None

    # -- utilitaires

    def resolve(self, kind: str, ref: int) -> int:
        """Traduit une référence, en tenant compte des identifiants négatifs."""
        if ref >= 0:
            return ref
        actual = self.placeholders.get((kind, ref))
        if actual is None:
            raise Precondition(
                f"référence {kind} {ref} inconnue : un objet créé doit apparaître "
                "avant d'être référencé"
            )
        return actual

    def require_visible(self, kind: str, element_id: int) -> int:
        state = store.element_state(self.con, kind, element_id)
        if state is None:
            raise Precondition(f"{kind} {element_id} inexistant")
        version, visible = state
        if not visible:
            raise Gone(f"{kind} {element_id} a été supprimé")
        return version

    def check_version(self, kind: str, element_id: int, claimed: int) -> int:
        current = self.require_visible(kind, element_id)
        if claimed != current:
            raise Conflict(
                f"Version mismatch: Provided {claimed}, server had: {current} "
                f"of {kind.capitalize()} {element_id}"
            )
        return current

    def note_point(self, lon: float, lat: float) -> None:
        if self.bbox is None:
            self.bbox = [lon, lat, lon, lat]
        else:
            self.bbox[0] = min(self.bbox[0], lon)
            self.bbox[1] = min(self.bbox[1], lat)
            self.bbox[2] = max(self.bbox[2], lon)
            self.bbox[3] = max(self.bbox[3], lat)

    def count(self) -> None:
        self.touched += 1
        if self.touched > self.max_elements:
            raise OsmApiError(
                f"changeset de plus de {self.max_elements} éléments"
            )

    # -- lecture d'un élément du document

    def _node_payload(self, element: ET.Element) -> tuple[float, float, dict[str, str]]:
        try:
            lon = float(element.get("lon"))
            lat = float(element.get("lat"))
        except (TypeError, ValueError):
            raise OsmApiError(f"coordonnées invalides sur node {element.get('id')}")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise OsmApiError(f"coordonnées hors domaine sur node {element.get('id')}")
        return lon, lat, _tags(element)

    def _way_nodes(self, element: ET.Element) -> list[int]:
        refs = [self.resolve("node", _int_attr(nd, "ref")) for nd in element.findall("nd")]
        if len(refs) < 2:
            raise Precondition(f"way {element.get('id')} : moins de 2 nœuds")
        for ref in refs:
            self.require_visible("node", ref)
        return refs

    def _members(self, element: ET.Element) -> list[tuple[str, int, str]]:
        members = []
        for member in element.findall("member"):
            kind = member.get("type")
            if kind not in ELEMENT_KINDS:
                raise OsmApiError(f"type de membre inconnu : {kind!r}")
            ref = self.resolve(kind, _int_attr(member, "ref"))
            self.require_visible(kind, ref)
            members.append((kind, ref, member.get("role") or ""))
        return members

    # -- les trois opérations

    def create(self, element: ET.Element) -> None:
        kind = element.tag
        old_id = _int_attr(element, "id")
        new_id = store.next_id(self.con, kind)
        self.placeholders[(kind, old_id)] = new_id

        if kind == "node":
            lon, lat, tags = self._node_payload(element)
            store.write_node(self.con, new_id, lon, lat, 1, self.changeset_id, tags)
            self.note_point(lon, lat)
        elif kind == "way":
            store.write_way(
                self.con, new_id, self._way_nodes(element), 1, self.changeset_id, _tags(element)
            )
        else:
            store.write_relation(
                self.con, new_id, self._members(element), 1, self.changeset_id, _tags(element)
            )

        self.count()
        self.diff.append(DiffEntry(kind, old_id, new_id, 1))

    def modify(self, element: ET.Element) -> None:
        kind = element.tag
        element_id = self.resolve(kind, _int_attr(element, "id"))
        claimed = _int_attr(element, "version", 0)
        self.check_version(kind, element_id, claimed)
        version = claimed + 1

        if kind == "node":
            lon, lat, tags = self._node_payload(element)
            store.write_node(self.con, element_id, lon, lat, version, self.changeset_id, tags)
            self.note_point(lon, lat)
        elif kind == "way":
            store.write_way(
                self.con,
                element_id,
                self._way_nodes(element),
                version,
                self.changeset_id,
                _tags(element),
            )
        else:
            store.write_relation(
                self.con,
                element_id,
                self._members(element),
                version,
                self.changeset_id,
                _tags(element),
            )

        self.count()
        self.diff.append(DiffEntry(kind, element_id, element_id, version))

    def delete(self, element: ET.Element, if_unused: bool) -> None:
        kind = element.tag
        element_id = self.resolve(kind, _int_attr(element, "id"))
        claimed = _int_attr(element, "version", 0)
        current = self.check_version(kind, element_id, claimed)

        users = store.referenced_by(self.con, kind, element_id)
        if users:
            if not if_unused:
                raise Precondition(
                    f"{kind.capitalize()} {element_id} est encore référencé par "
                    + ", ".join(users)
                )
            # `if-unused` : ne pas supprimer, ne pas échouer — l'élément est
            # renvoyé inchangé pour que le client sache qu'il a survécu.
            self.diff.append(DiffEntry(kind, element_id, element_id, current))
            return

        store.delete_element(self.con, kind, element_id, claimed + 1, self.changeset_id)
        self.count()
        self.diff.append(DiffEntry(kind, element_id))


def apply_osmchange(
    con: sqlite3.Connection,
    payload: bytes,
    changeset_id: int,
    max_elements: int = 10000,
) -> list[DiffEntry]:
    """Applique le document et renvoie le diffResult, ou lève une OsmApiError.

    Toute l'opération tient dans une transaction : une erreur au dernier
    élément annule les précédents.
    """
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise OsmApiError(f"osmChange illisible : {err}")

    if root.tag != "osmChange":
        raise OsmApiError(f"racine <{root.tag}> inattendue, <osmChange> attendu")

    applier = _Applier(con, changeset_id, max_elements)

    con.execute("BEGIN IMMEDIATE")
    try:
        # Les blocs sont traités dans l'ordre du document : c'est ce qui garantit
        # qu'un objet créé existe avant d'être référencé par un autre.
        for block in root:
            if block.tag not in ("create", "modify", "delete"):
                continue
            if_unused = block.get("if-unused") in ("true", "1")
            for element in block:
                if element.tag not in ELEMENT_KINDS:
                    continue
                if block.tag == "create":
                    applier.create(element)
                elif block.tag == "modify":
                    applier.modify(element)
                else:
                    applier.delete(element, if_unused)

        store.record_changeset_activity(
            con, changeset_id, applier.touched, tuple(applier.bbox) if applier.bbox else None
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    return applier.diff


def diff_result_xml(entries: list[DiffEntry]) -> str:
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f"<diffResult version=\"0.6\" generator={quoteattr(GENERATOR)}>",
    ]
    for entry in entries:
        attrs = f'old_id="{entry.old_id}"'
        if entry.new_id is not None:
            attrs += f' new_id="{entry.new_id}" new_version="{entry.new_version}"'
        lines.append(f"  <{entry.kind} {attrs}/>")
    lines.append("</diffResult>")
    return "\n".join(lines) + "\n"
