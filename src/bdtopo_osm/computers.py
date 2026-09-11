"""Fonctions `compute:` appelables depuis les règles YAML.

Réservé aux cas que le déclaratif ne couvre pas honnêtement. Chaque fonction
ajoutée ici est une dette de lisibilité : le YAML cesse d'être auto-suffisant.
On l'accepte quand la contorsion du DSL coûterait plus cher que le code.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from .mapping import computer, is_empty

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"

_ROMAN = re.compile(r"^[IVXLCDM]+$")


@lru_cache(maxsize=1)
def _abreviations() -> dict:
    doc = yaml.safe_load((RULES_DIR / "abreviations_fantoir.yaml").read_text(encoding="utf-8"))
    return {
        "types": {k.upper(): v for k, v in doc["types_de_voie"].items()},
        "partout": {k.upper(): v for k, v in doc["partout"].items()},
        "particules": {p.lower() for p in doc["particules"]},
    }


# ------------------------------------------------------- normalisation de nom


def _capitalize(token: str) -> str:
    return token[:1].upper() + token[1:] if token else token


def _cap_hyphenated(word: str, first: bool, particules: set[str]) -> str:
    """« saint-jean-de-sauves » → « Saint-Jean-de-Sauves »."""
    pieces = word.split("-")
    out = []
    for index, piece in enumerate(pieces):
        leading = first and index == 0
        if not leading and piece in particules:
            out.append(piece)
        else:
            out.append(_capitalize(piece))
    return "-".join(out)


def _cap_word(word: str, first: bool, particules: set[str]) -> str:
    if _ROMAN.match(word.upper()) and len(word) > 1:
        return word.upper()  # « Jean XXIII », pas « Jean Xxiii »
    if "'" in word:
        # La partie qui précède l'apostrophe peut elle-même être composée :
        # « saint-julien-l'ars » → « Saint-Julien-l'Ars ».
        head, _, tail = word.partition("'")
        head_out = _cap_hyphenated(head, first, particules)
        return f"{head_out}'{_cap_hyphenated(tail, False, particules)}"
    return _cap_hyphenated(word, first, particules)


def title_case_fr(text: str) -> str:
    """Casse typographique française : particules en minuscules sauf en tête."""
    particules = _abreviations()["particules"]
    words = text.lower().split()
    return " ".join(_cap_word(w, i == 0, particules) for i, w in enumerate(words))


def normalize_street_name(raw: str) -> str:
    """Développe les abréviations FANTOIR et rétablit une casse lisible.

    N'intervient que sur les noms tout en majuscules — c'est la signature du
    FANTOIR brut (97,3 % de `nom_collaboratif` dans la Vienne). Un nom déjà
    correctement orthographié (source BAN) est laissé intact : le corriger
    serait au mieux inutile, au pire destructeur.

    Heuristique assumée : un premier mot non reconnu n'est pas développé, et
    l'expansion ne s'applique qu'au type de voie en tête. Mieux vaut « Che des
    Vignes » non développé qu'un contresens.
    """
    text = " ".join(str(raw).split())
    if not text:
        return ""
    if text != text.upper():
        return text  # déjà correctement casé (BAN)

    table = _abreviations()
    words = title_case_fr(text).split()

    head = words[0].upper()
    if head in table["types"]:
        words[0] = table["types"][head]

    return " ".join(table["partout"].get(w.upper(), w) for w in words)


# ------------------------------------------------------------------ toponymie


def _clean(feature: dict, key: str | None) -> str | None:
    if not key:
        return None
    value = feature.get(key)
    if is_empty(value):
        return None
    cleaned = normalize_street_name(value)
    return cleaned or None


@computer("nom_de_voie")
def nom_de_voie(feature: dict, args: dict) -> dict[str, str]:
    """Arbitre le nom d'une voie entre ses côtés gauche et droit, et entre ses
    deux sources concurrentes.

    La BD Topo porte le toponyme séparément de part et d'autre du tronçon, ce
    qui reflète une réalité : une voie peut changer de nom en son milieu quand
    elle sert de limite entre deux communes ou deux quartiers.

    Priorité à la BAN malgré sa moindre couverture (32,6 % contre 86,6 %) :
    elle est correctement orthographiée, là où `nom_collaboratif` est du FANTOIR
    en majuscules abrégées (288 984 valeurs sur 296 962 dans la Vienne). Le
    repli passe par `normalize_street_name`, qui reconstitue une forme lisible
    sans jamais inventer ce qu'il ne reconnaît pas.

    Côtés identiques ou un seul renseigné → `name`. Côtés réellement divergents
    → `name:left` / `name:right`, sans `name`, plutôt que d'en élire un
    arbitrairement.
    """
    source = "BAN"
    left = _clean(feature, args.get("left"))
    right = _clean(feature, args.get("right"))

    if left is None and right is None:
        source = "BD TOPO nom_collaboratif"
        left = _clean(feature, args.get("fallback_left"))
        right = _clean(feature, args.get("fallback_right"))

    if left is None and right is None:
        return {}

    if left is None:
        return {"name": right, "source:name": source}
    if right is None or left == right:
        return {"name": left, "source:name": source}

    # Les deux côtés diffèrent parfois par la seule casse (« Rue des Deux
    # Communes » / « Rue des deux Communes ») : c'est une incohérence de saisie
    # BAN, pas une voie qui change de nom en son milieu. En faire un couple
    # name:left / name:right fabriquerait une divergence qui n'existe pas.
    if left.casefold() == right.casefold():
        return {"name": left, "source:name": source}

    return {"name:left": left, "name:right": right, "source:name": source}
