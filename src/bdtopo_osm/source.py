"""Lecture des couches BD Topo, via `bdtopo-extract`.

Différence essentielle avec l'extraction géomatique : on sélectionne les entités
**entières** qui intersectent le territoire, au lieu de découper les géométries
sur sa limite. `geopandas.clip` conviendrait pour produire une carte, mais pour
une conversion OSM il tronquerait les bâtiments à cheval sur une limite
communale et fabriquerait des sommets qui ne correspondent à aucun nœud BD Topo
— en cassant au passage l'identité `cleabs` sur laquelle repose la réversibilité.
"""
from __future__ import annotations

import time

import geopandas as gpd
import pyogrio

from bdtopo_extract import catalog, territoire


def resolve_territoire(spec: str):
    """`commune:86194`, `departement:86`, `bbox:xmin,ymin,xmax,ymax`."""
    kind, _, value = spec.partition(":")
    if kind == "bbox":
        xmin, ymin, xmax, ymax = (float(v) for v in value.split(","))
        return territoire.from_bbox(xmin, ymin, xmax, ymax)
    return territoire.resolve(kind, value)


def load_layer(layer_name: str, terr) -> gpd.GeoDataFrame:
    """Entités entières intersectant le territoire, en EPSG:4326.

    Le bbox sert de préfiltre (index spatial FlatGeobuf, lecture réseau réduite) ;
    la sélection exacte se fait ensuite par prédicat d'intersection.
    """
    layers = catalog.get_catalog("bdtopo")
    if layer_name not in layers:
        raise KeyError(f"couche inconnue : {layer_name!r}")

    started = time.time()
    gdf = pyogrio.read_dataframe(layers[layer_name].vsi_path, bbox=terr.bbox)
    if len(gdf):
        gdf = gdf[gdf.intersects(terr.geometry)].copy()
    gdf.attrs["read_seconds"] = round(time.time() - started, 1)
    return gdf
