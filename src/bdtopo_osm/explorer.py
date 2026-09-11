"""Documentation BD TOPO Explorer (bdtopoexplorer.ign.fr), extraite pour l'éditeur.

BD TOPO Explorer documente chaque couche, chaque attribut et **chaque valeur**
possible, avec des ancres stables (`#attribute_486`, `#attribute_value_465`).
C'est exactement ce qu'iD attend d'une référence : un titre, une définition, un
lien. On extrait tout cela une fois (`bdtopo-osm docs-explorer`) dans
`web/bdtopo-docs.json`, servi tel quel ; la page d'iD y puise quand l'usager
demande la référence d'un tag `bdtopo:*`.

L'extraction est un traitement hors ligne : ni bs4 ni requêtes IGN au moment
de servir.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

BASE_URL = "https://bdtopoexplorer.ign.fr"

# Préfixe des `cleabs` → couche. C'est ce qui permet, depuis un objet OSM qui
# ne porte que ses tags, de retrouver la page BD TOPO Explorer de sa couche.
CLEABS_PREFIXES = {
    "TRONROUT": "troncon_de_route",
    "BATIMENT": "batiment",
    "TRON_EAU": "troncon_hydrographique",
    "SURF_EAU": "surface_hydrographique",
    "TRONFERR": "troncon_de_voie_ferree",
    "ZONEVEGE": "zone_de_vegetation",
    "PAIHABIT": "zone_d_habitation",
    "PAIE_NAT": "lieu_dit_non_habite",
    "SURFACTI": "zone_d_activite_ou_d_interet",
    "EQ_RESEA": "equipement_de_transport",
    "TERRSPOR": "terrain_de_sport",
    "CIMETIER": "cimetiere",
    "CONSSURF": "construction_surfacique",
    "CONSLINE": "construction_lineaire",
    "CONSPONC": "construction_ponctuelle",
    "LIGNELEC": "ligne_electrique",
    "PYLONE__": "pylone",
    "POSTRANS": "poste_de_transformation",
    "SURFPARC": "parc_ou_reserve",
    "RESERVOI": "reservoir",
    "AERODROM": "aerodrome",
    "PISTAERO": "piste_d_aerodrome",
    "PAIHYDRO": "detail_hydrographique",
}


def _clean(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _article_text(article) -> str:
    """Contenu d'un article sans son intitulé, sans modifier le DOM."""
    text = _clean(article.get_text(" "))
    return text.split(":", 1)[1].strip() if ":" in text else text


def _definition(node, own_only: bool = True) -> str:
    """Texte qui suit « Définition : » dans les articles d'un bloc.

    `own_only` : ignorer les articles appartenant à un sous-bloc (une valeur
    imbriquée dans un attribut, un attribut imbriqué dans la page), pour que la
    définition d'un niveau ne soit jamais volée par celle du niveau inférieur.
    """
    for article in node.select("div.specif-Contenu div.contenu_article"):
        title = article.select_one("span.titre_article")
        if not title or "Définition" not in title.get_text():
            continue
        if own_only:
            owner = article.find_parent("div", class_="div_valeur") or article.find_parent(
                "div", class_="div_attribut"
            )
            if owner is not None and owner is not node:
                continue
        return _article_text(article)
    return ""


def parse_layer_page(html: str, layer: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    page_url = f"{BASE_URL}/{layer}"

    # Le libellé de la couche n'est pas dans un élément dédié ; le lien PDF
    # le porte en clair : `nom_pdf=Tronçon de route.pdf`.
    pdf = soup.select_one("a[href*='id_classe='][href*='nom_pdf=']")
    m = re.search(r"nom_pdf=(.*?)\.pdf", pdf["href"]) if pdf else None
    layer_label = _clean(m.group(1)) if m else layer
    definition = _definition(soup, own_only=True)

    attributes: dict[str, dict] = {}
    for block in soup.select("div.div_attribut[id^=attribute_]"):
        anchor = block["id"]
        head = block.select_one("span.titre_attribut_pdf")
        if head:
            for extra in head.select("span.copier_lien_attribut"):
                extra.extract()
        label = _clean(head.get_text()) if head else anchor
        cell = block.select_one("table.table_nom_attr tr:nth-of-type(2) td")
        field = _clean(cell.get_text()) if cell else ""
        if not field:
            continue

        values: dict[str, dict] = {}
        for vblock in block.select("div.div_valeur[id^=attribute_value_]"):
            vtitle = vblock.select_one("span.titre_valeur")
            if vtitle:
                for extra in vtitle.select("span.copier_lien_valeur"):
                    extra.extract()
            raw = _clean(vtitle.get_text()) if vtitle else ""
            m = re.search(r"«\s*(.*?)\s*»", raw)
            value = m.group(1) if m else raw.split("=", 1)[-1].strip()
            values[value] = {
                "definition": _definition(vblock),
                "url": f"{page_url}#{vblock['id']}",
            }

        attributes[field] = {
            "label": label,
            "definition": _definition(block),
            "url": f"{page_url}#{anchor}",
            "values": values,
        }

    return {
        "label": layer_label,
        "definition": definition,
        "url": page_url,
        "attributes": attributes,
    }


def fetch_all(layers: list[str], out: Path, delay: float = 0.5) -> dict:
    import requests

    # Le libellé de la couche est plus fiable dans la liste des classes déjà
    # lue par bdtopo-extract (« Zone d'habitation ») que dans le nom du PDF
    # (« Zone d_habitation »). Sa *description*, en revanche, n'est pas reprise :
    # bdtopo-extract la lit au premier « Définition » de la page, qui pour les
    # couches sans définition de classe (troncon_de_route…) est celle du premier
    # attribut. Un champ vide vaut mieux qu'une définition fausse.
    try:
        from bdtopo_extract import docs as extract_docs

        fallback = extract_docs.get_docs()
    except Exception:  # pragma: no cover - dépendance facultative
        fallback = {}

    docs: dict[str, dict] = {}
    for layer in layers:
        html = requests.get(f"{BASE_URL}/{layer}", timeout=60).text
        page = parse_layer_page(html, layer)
        extra = fallback.get(layer, {})
        if extra.get("display_name"):
            page["label"] = extra["display_name"]
        page["theme"] = extra.get("theme", "")
        docs[layer] = page
        time.sleep(delay)  # site institutionnel : on reste courtois

    payload = {
        "source": BASE_URL,
        "extrait_le": time.strftime("%Y-%m-%d"),
        "prefixes": CLEABS_PREFIXES,
        "couches": docs,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload
