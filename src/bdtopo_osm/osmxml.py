"""Écriture d'un fichier .osm (XML API 0.6).

Écriture en flux : le fichier d'un département pèsera plusieurs gigaoctets, il
n'est pas question de construire l'arbre en mémoire.

Les identifiants émis sont **positifs**, avec `version="1"`. Un fichier à
identifiants négatifs signifierait « objets à créer » pour JOSM ; ici on décrit
un état de base existant, destiné à être chargé tel quel dans l'API.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TextIO
from xml.sax.saxutils import quoteattr

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # shapely n'est pas une dépendance du service
    from .topology import OsmBuilder

# OSM impose 255 caractères par clé et par valeur.
MAX_TAG_LENGTH = 255

# XML 1.0 interdit la plupart des caractères de contrôle, que la BD Topo peut
# véhiculer dans des toponymes issus de saisies anciennes.
_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

GENERATOR = "bdtopo-osm"


def sanitize(value: str) -> str:
    return _INVALID_XML.sub("", str(value)).strip()


class OsmWriter:
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream
        self.truncated = 0

    def __enter__(self) -> "OsmWriter":
        self.stream.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        self.stream.write(f'<osm version="0.6" generator={quoteattr(GENERATOR)}>\n')
        return self

    def __exit__(self, *exc) -> None:
        self.stream.write("</osm>\n")

    # ------------------------------------------------------------------ tags

    def _write_tags(self, tags: dict[str, str], indent: str) -> None:
        for key, value in tags.items():
            key_s, value_s = sanitize(key), sanitize(value)
            if not key_s or not value_s:
                continue
            if len(key_s) > MAX_TAG_LENGTH or len(value_s) > MAX_TAG_LENGTH:
                key_s, value_s = key_s[:MAX_TAG_LENGTH], value_s[:MAX_TAG_LENGTH]
                self.truncated += 1
            self.stream.write(f"{indent}<tag k={quoteattr(key_s)} v={quoteattr(value_s)}/>\n")

    # -------------------------------------------------------------- éléments

    def write_node(self, node) -> None:
        head = (
            f'  <node id="{node.id}" visible="true" version="1" '
            f'lat="{node.lat:.7f}" lon="{node.lon:.7f}"'
        )
        if not node.tags:
            self.stream.write(head + "/>\n")
            return
        self.stream.write(head + ">\n")
        self._write_tags(node.tags, "    ")
        self.stream.write("  </node>\n")

    def write_way(self, way) -> None:
        self.stream.write(f'  <way id="{way.id}" visible="true" version="1">\n')
        for ref in way.nodes:
            self.stream.write(f'    <nd ref="{ref}"/>\n')
        self._write_tags(way.tags, "    ")
        self.stream.write("  </way>\n")

    def write_relation(self, relation) -> None:
        self.stream.write(f'  <relation id="{relation.id}" visible="true" version="1">\n')
        for member_type, ref, role in relation.members:
            self.stream.write(
                f'    <member type="{member_type}" ref="{ref}" role={quoteattr(role)}/>\n'
            )
        self._write_tags(relation.tags, "    ")
        self.stream.write("  </relation>\n")


def write(builder: OsmBuilder, path: str | Path) -> dict[str, int]:
    """Sérialise le graphe. Les nœuds précèdent les ways, qui précèdent les
    relations : l'ordre est exigé par les consommateurs qui lisent en flux."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        with OsmWriter(fh) as writer:
            for node in builder.nodes.values():
                writer.write_node(node)
            for way in builder.ways.values():
                writer.write_way(way)
            for relation in builder.relations.values():
                writer.write_relation(relation)
    return {"tags_truncated": writer.truncated, "bytes": path.stat().st_size}
