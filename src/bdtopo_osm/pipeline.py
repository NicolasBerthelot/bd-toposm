"""Orchestration : couches BD Topo → règles → graphe OSM → fichier .osm."""
from __future__ import annotations

import gc
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import computers  # noqa: F401  (enregistre les fonctions `compute:`)
from . import osmxml, source, store
from .mapping import RuleSet
from .topology import MemoryBuilder, OsmBuilder

# Taille des lots de `to_dict("records")`. Convertir toute une couche d'un coup
# double son empreinte mémoire (GeoDataFrame + dictionnaires) ; par lots, seul
# un lot de dictionnaires coexiste avec la couche.
CHUNK = 20_000

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


@dataclass
class LayerReport:
    layer: str
    features: int = 0
    converted: int = 0
    dropped: int = 0
    untagged: int = 0
    read_seconds: float = 0.0
    drop_reasons: Counter = field(default_factory=Counter)
    main_key_values: Counter = field(default_factory=Counter)
    coverage: dict = field(default_factory=dict)


SOCLE_MANIFEST = RULES_DIR / "socle.yaml"


def socle_layers(path: Path = SOCLE_MANIFEST) -> list[str]:
    """Couches du socle OSM-utile, dans l'ordre de conversion.

    L'ordre compte : les couches linéaires et surfaciques d'abord, les couches
    ponctuelles ensuite, pour que les objets ponctuels qui doivent se greffer
    sur un sommet existant le trouvent déjà en place.
    """
    import yaml

    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [entry["layer"] for entry in doc["couches"]]


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def convert(
    layer_names: list[str],
    territoire_spec: str,
    output: Path | None,
    rules_dir: Path = RULES_DIR,
    db: Path | None = None,
    engine: str = "memory",
) -> tuple[OsmBuilder, list[LayerReport], dict | None]:
    """Convertit les couches demandées.

    `engine="memory"` construit le graphe en dictionnaires puis, si `db` est
    donné, le verse en base d'un bloc. `engine="sqlite"` écrit directement dans
    `db` au fil de l'eau : c'est le seul moyen de tenir un département, où le
    graphe dépasse la mémoire — mais il ne produit pas de fichier `.osm`.
    """
    terr = source.resolve_territoire(territoire_spec)
    reports: list[LayerReport] = []

    con = None
    if engine == "sqlite":
        if db is None:
            raise ValueError("engine='sqlite' exige une base cible (--db)")
        from .store_builder import SqliteBuilder

        con = store.connect(db)
        builder: OsmBuilder = SqliteBuilder(con)
    else:
        builder = MemoryBuilder()

    total_started = time.time()
    for index, layer_name in enumerate(layer_names, 1):
        ruleset = RuleSet.load(Path(rules_dir) / f"{layer_name}.yaml")
        _log(f"[{index}/{len(layer_names)}] {layer_name} : lecture…")
        gdf = source.load_layer(layer_name, terr)

        report = LayerReport(layer=layer_name, features=len(gdf))
        report.read_seconds = gdf.attrs.get("read_seconds", 0.0)
        report.coverage = ruleset.coverage(gdf.columns)
        _log(f"    {len(gdf)} entités lues en {report.read_seconds}s, conversion…")

        if len(gdf):
            main_key = ruleset.report_key
            shared_points = ruleset.point_mode == "shared"
            # Champs consultés par les règles : c'est la provenance conservée
            # par objet, pour pouvoir expliquer chaque tag après coup.
            used_fields = sorted(ruleset.referenced_fields() & set(gdf.columns))
            attributes = gdf.drop(columns=gdf.geometry.name)
            geometries = gdf.geometry.to_numpy()
            started = time.time()

            for chunk_start in range(0, len(gdf), CHUNK):
                records = attributes.iloc[chunk_start : chunk_start + CHUNK].to_dict("records")
                for offset, feature in enumerate(records):
                    reason = ruleset.dropped_reason(feature)
                    if reason is not None:
                        report.dropped += 1
                        report.drop_reasons[reason] += 1
                        continue
                    tags = ruleset.apply(feature) or {}
                    if not tags:
                        report.untagged += 1
                        continue
                    created = _emit(builder, geometries[chunk_start + offset], tags, shared_points)
                    if created:
                        source_attrs = _plain_attributes(feature, used_fields)
                        for kind, element_id in created:
                            builder.record_provenance(kind, element_id, layer_name, source_attrs)
                    report.converted += 1
                    if main_key:
                        report.main_key_values[tags.get(main_key, "(aucun)")] += 1
                if len(gdf) > CHUNK:
                    done = min(chunk_start + CHUNK, len(gdf))
                    _log(f"    {done}/{len(gdf)}  ({time.time() - started:.0f}s)")

            del attributes, geometries

        del gdf
        gc.collect()

        if con is not None:
            builder.commit_layer()  # type: ignore[attr-defined]
        reports.append(report)
        _log(f"    → {report.converted} converties, {report.dropped} écartées")

    _log(f"conversion terminée en {time.time() - total_started:.0f}s")

    written = None
    if output is not None:
        if engine == "sqlite":
            _log("(pas de .osm avec engine=sqlite : la base est la sortie)")
        else:
            started = time.time()
            written = osmxml.write(builder, output)
            written["write_seconds"] = round(time.time() - started, 1)

    if con is not None:
        _log("finalisation de la base (compteurs, ANALYZE)…")
        builder.finalize(source_label=territoire_spec)  # type: ignore[attr-defined]
        con.close()
    elif db is not None:
        con = store.connect(db)
        try:
            store.load(con, builder, source_label=territoire_spec)
        finally:
            con.close()

    return builder, reports, written


def _emit(
    builder: OsmBuilder, geom, tags: dict[str, str], shared_points: bool = False
) -> list[tuple[str, int]]:
    """Émet la géométrie et renvoie les éléments *porteurs de tags* créés."""
    kind = geom.geom_type if geom is not None else None
    if kind in ("Point", "MultiPoint"):
        return [("node", n) for n in builder.add_point(geom, tags, shared=shared_points)]
    if kind in ("LineString", "MultiLineString"):
        return [("way", w) for w in builder.add_linestring(geom, tags)]
    if kind in ("Polygon", "MultiPolygon"):
        result = builder.add_polygon(geom, tags)
        return [result] if result else []
    builder.stats["empty_geometries"] += 1
    return []


def _plain_attributes(feature: dict, fields: list[str]) -> dict:
    from .mapping import is_empty, format_value

    out = {}
    for f in fields:
        v = feature.get(f)
        if is_empty(v):
            continue
        out[f] = v if isinstance(v, (bool, int, float, str)) else format_value(v)
    return out


def format_report(reports: list[LayerReport], builder: OsmBuilder, written: dict | None) -> str:
    lines: list[str] = []
    for r in reports:
        lines.append(f"\n── {r.layer} " + "─" * (60 - len(r.layer)))
        lines.append(
            f"   {r.features} entités lues en {r.read_seconds}s → "
            f"{r.converted} converties, {r.dropped} écartées, {r.untagged} sans tag"
        )
        for reason, count in r.drop_reasons.most_common():
            lines.append(f"     écarté ({count}) : {reason[:90]}")

        cov = r.coverage
        lines.append(
            f"   champs : {len(cov['used'])} utilisés, "
            f"{len(cov['declared_unmapped'])} écartés et documentés"
        )
        if cov["uncovered"]:
            lines.append(
                "   ⚠ NON COUVERTS (à traiter ou à documenter dans `unmapped:`) : "
                + ", ".join(sorted(cov["uncovered"]))
            )
        if cov["unknown"]:
            lines.append(
                "   ⚠ déclarés mais absents de la couche : "
                + ", ".join(sorted(cov["unknown"]))
            )

        if r.main_key_values:
            lines.append("   répartition :")
            for value, count in r.main_key_values.most_common(20):
                pct = 100 * count / max(r.converted, 1)
                lines.append(f"     {value:<22} {count:>8}  {pct:5.1f}%")

    s = builder.summary()
    lines.append("\n── graphe OSM " + "─" * 48)
    lines.append(f"   nodes     {s['nodes']:>10}")
    lines.append(f"   ways      {s['ways']:>10}")
    lines.append(f"   relations {s['relations']:>10}")
    lines.append(
        f"   dont {s['closed_ways']} ways fermés, {s['multipolygons']} multipolygones, "
        f"{s['ways_split']} segments issus d'un découpage (>2000 nœuds)"
    )
    lines.append(
        f"   {s['shared_nodes']} réutilisations de nœud "
        f"(sommets mutualisés entre géométries)"
    )
    if s["empty_geometries"]:
        lines.append(f"   ⚠ {s['empty_geometries']} géométries vides ou non gérées")
    if written is not None:
        lines.append(
            f"\n   fichier : {written['bytes'] / 1e6:.1f} Mo écrits en "
            f"{written['write_seconds']}s"
        )
        if written["tags_truncated"]:
            lines.append(f"   ⚠ {written['tags_truncated']} tags tronqués à 255 caractères")
    return "\n".join(lines)
