"""Moteur de règles BD Topo → tags OSM.

Le mapping est décrit en YAML (un fichier par couche, dans `rules/`) plutôt qu'en
Python : c'est le livrable sémantique du projet, il doit rester relisible et
discutable par quelqu'un qui connaît la BD Topo sans lire de code.

Trois principes :

1. **Rien d'implicite.** Un champ source doit être soit utilisé par une règle,
   soit déclaré dans `unmapped:` avec un motif. `RuleSet.coverage()` vérifie
   l'exhaustivité ; un champ oublié est une erreur, pas un silence.
2. **Une valeur absente ne produit pas de tag.** Les champs BD Topo sont
   fréquemment vides (cf. les taux de remplissage) ; un `lanes=nan` serait pire
   que pas de tag du tout.
3. **Échappatoire assumée.** Les quelques cas qui ne se plient pas au déclaratif
   (arbitrage gauche/droite d'un nom de voie) passent par `compute:` et une
   fonction Python enregistrée, plutôt que par une contorsion du DSL.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

# --------------------------------------------------------------------- valeurs


try:  # pandas est présent en pratique, mais le moteur doit rester testable sans lui
    from pandas import isna as _isna
except ImportError:  # pragma: no cover
    _isna = None


def is_empty(value: Any) -> bool:
    """Vide au sens BD Topo : None, NaN, pandas.NA, chaîne vide ou blanche.

    `pandas.NA` mérite une mention : contrairement à `float('nan')`, il n'est
    pas détectable par `value != value` (la comparaison renvoie `NA`, dont la
    conversion en booléen lève). Avec le dtype chaîne de pandas 3, c'est la
    valeur manquante de la majorité des colonnes BD Topo — la rater produirait
    des tags `name=<NA>` en masse.
    """
    if value is None:
        return True
    if _isna is not None:
        try:
            missing = _isna(value)
            if missing is True or missing is False:
                if missing:
                    return True
            elif bool(missing):
                return True
        except (TypeError, ValueError):
            pass  # tableaux, géométries : non scalaires, donc non vides ici
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def format_value(value: Any, decimals: int | None = None) -> str:
    """Rend une valeur BD Topo en chaîne de tag OSM.

    Les entiers stockés en float64 (`nombre_de_voies` = 2.0) ressortent en "2" :
    un tag `lanes=2.0` serait rejeté par les validateurs OSM.
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, float):
        if decimals is not None:
            value = round(value, decimals)
        if value == int(value):
            return str(int(value))
        return repr(value).rstrip("0").rstrip(".")
    return str(value).strip()


# ------------------------------------------------------------------ conditions

_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {}


def _operator(name: str):
    def register(fn):
        _OPERATORS[name] = fn
        return fn

    return register


@_operator("present")
def _op_present(value, expected) -> bool:
    return (not is_empty(value)) == bool(expected)


@_operator("absent")
def _op_absent(value, expected) -> bool:
    return is_empty(value) == bool(expected)


@_operator("in")
def _op_in(value, expected) -> bool:
    return not is_empty(value) and format_value(value) in {format_value(e) for e in expected}


@_operator("not_in")
def _op_not_in(value, expected) -> bool:
    return not _op_in(value, expected)


@_operator("contains")
def _op_contains(value, expected) -> bool:
    return not is_empty(value) and str(expected) in str(value)


@_operator("matches")
def _op_matches(value, expected) -> bool:
    return not is_empty(value) and re.search(str(expected), str(value)) is not None


def _numeric(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@_operator("gt")
def _op_gt(value, expected) -> bool:
    n = _numeric(value)
    return n is not None and n > float(expected)


@_operator("gte")
def _op_gte(value, expected) -> bool:
    n = _numeric(value)
    return n is not None and n >= float(expected)


@_operator("lt")
def _op_lt(value, expected) -> bool:
    n = _numeric(value)
    return n is not None and n < float(expected)


@_operator("lte")
def _op_lte(value, expected) -> bool:
    n = _numeric(value)
    return n is not None and n <= float(expected)


def condition_fields(cond: Any) -> set[str]:
    """Champs source lus par une condition (pour le contrôle de couverture)."""
    if not isinstance(cond, dict):
        return set()
    fields: set[str] = set()
    for key, spec in cond.items():
        if key in ("any_of", "all_of"):
            for sub in spec:
                fields |= condition_fields(sub)
        elif key == "not":
            fields |= condition_fields(spec)
        else:
            fields.add(key)
    return fields


def evaluate(cond: Any, feature: dict) -> bool:
    """Évalue une condition. Les clés d'un même dict sont combinées en ET."""
    if cond is None:
        return True
    if not isinstance(cond, dict):
        raise ValueError(f"condition invalide : {cond!r}")

    for key, spec in cond.items():
        if key == "any_of":
            if not any(evaluate(sub, feature) for sub in spec):
                return False
        elif key == "all_of":
            if not all(evaluate(sub, feature) for sub in spec):
                return False
        elif key == "not":
            if evaluate(spec, feature):
                return False
        else:
            if not _match_field(feature.get(key), spec):
                return False
    return True


def _match_field(value: Any, spec: Any) -> bool:
    if isinstance(spec, dict):
        for op, expected in spec.items():
            fn = _OPERATORS.get(op)
            if fn is None:
                raise ValueError(f"opérateur inconnu : {op!r}")
            if not fn(value, expected):
                return False
        return True
    if isinstance(spec, list):
        return _op_in(value, spec)
    if isinstance(spec, bool):
        return (not is_empty(value)) and bool(value) == spec
    return not is_empty(value) and format_value(value) == format_value(spec)


# ---------------------------------------------------------------- valeurs de tag

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def value_fields(spec: Any) -> set[str]:
    if isinstance(spec, str):
        return set(_PLACEHOLDER.findall(spec))
    if isinstance(spec, dict) and "from" in spec:
        return {spec["from"]}
    return set()


def resolve_value(spec: Any, feature: dict) -> str | None:
    """Calcule la valeur d'un tag. None => le tag n'est pas émis."""
    if isinstance(spec, str):
        refs = _PLACEHOLDER.findall(spec)
        if not refs:
            return spec
        # Un seul champ absent suffit à annuler le tag : mieux vaut pas de tag
        # qu'un `name=None` ou un `ref=D {numero}` à trou.
        values = {}
        for name in refs:
            v = feature.get(name)
            if is_empty(v):
                return None
            values[name] = format_value(v)
        return _PLACEHOLDER.sub(lambda m: values[m.group(1)], spec)

    if isinstance(spec, bool):
        return "yes" if spec else "no"
    if not isinstance(spec, dict):
        return format_value(spec)

    raw = feature.get(spec["from"]) if "from" in spec else None
    if "from" in spec and is_empty(raw):
        return None
    if raw is not None and spec.get("drop_values") and format_value(raw) in {
        format_value(v) for v in spec["drop_values"]
    }:
        return None

    if "map" in spec:
        table = {format_value(k): v for k, v in spec["map"].items()}
        mapped = table.get(format_value(raw), spec.get("default"))
        return None if mapped is None else str(mapped)

    if raw is None:
        return None
    if "scale" in spec:
        n = _numeric(raw)
        if n is None:
            return None
        raw = n * float(spec["scale"])
    out = format_value(raw, decimals=spec.get("decimals"))
    if "template" in spec:
        out = str(spec["template"]).replace("{value}", out)
    return out or None


# ------------------------------------------------------------------- computed

COMPUTERS: dict[str, Callable[[dict, dict], dict[str, str]]] = {}


def computer(name: str):
    """Enregistre une fonction `compute:` utilisable depuis le YAML.

    Signature : (feature, args) -> dict de tags. Réservé aux cas que le
    déclaratif ne couvre pas honnêtement ; chaque ajout ici est une dette de
    lisibilité et doit être justifié dans le YAML appelant.
    """

    def register(fn):
        COMPUTERS[name] = fn
        return fn

    return register


# ----------------------------------------------------------------------- règles


_METADONNEES_CACHE: dict[Path, dict[str, str]] = {}


def _metadonnees_communes(rules_dir: Path) -> dict[str, str]:
    if rules_dir not in _METADONNEES_CACHE:
        path = rules_dir / "_metadonnees_ign.yaml"
        _METADONNEES_CACHE[rules_dir] = (
            yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        )
    return _METADONNEES_CACHE[rules_dir]


@dataclass
class RuleSet:
    layer: str
    description: str
    drop: list[dict] = field(default_factory=list)
    rules: list[dict] = field(default_factory=list)
    unmapped: dict[str, str] = field(default_factory=dict)
    # Tag dont on veut la répartition dans le rapport de conversion, et mode de
    # création des nœuds pour les couches ponctuelles (cf. topology.add_point).
    report_key: str | None = None
    point_mode: str = "standalone"
    # Champs écartés hérités de _metadonnees_ign.yaml : leur absence dans une
    # couche donnée n'est pas une anomalie, contrairement à une déclaration locale.
    common_unmapped: frozenset = frozenset()
    source_path: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> "RuleSet":
        path = Path(path)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))

        unmapped = dict(doc.get("unmapped", {}) or {})
        common_keys: frozenset = frozenset()
        if doc.get("unmapped_commun", True):
            # Les métadonnées de production IGN se répètent dans presque toutes
            # les couches ; les mutualiser garde chaque fichier centré sur ses
            # propres arbitrages. Une déclaration locale reste prioritaire.
            commun = _metadonnees_communes(path.parent)
            common_keys = frozenset(set(commun) - set(unmapped))
            unmapped = {**commun, **unmapped}

        return cls(
            layer=doc["layer"],
            description=doc.get("description", ""),
            drop=doc.get("drop", []) or [],
            rules=doc.get("rules", []) or [],
            unmapped=unmapped,
            report_key=doc.get("report_key"),
            point_mode=doc.get("point_mode", "standalone"),
            common_unmapped=common_keys,
            source_path=path,
        )

    # -- application

    def dropped_reason(self, feature: dict) -> str | None:
        for entry in self.drop:
            if evaluate(entry.get("when"), feature):
                return entry.get("reason", "(motif non précisé)")
        return None

    def apply(self, feature: dict) -> dict[str, str] | None:
        """Retourne les tags OSM, ou None si l'entité est écartée."""
        if self.dropped_reason(feature) is not None:
            return None

        tags: dict[str, str] = {}
        for rule in self.rules:
            if not evaluate(rule.get("when"), feature):
                continue
            if "first_match" in rule:
                for branch in rule["first_match"]:
                    if evaluate(branch.get("when"), feature):
                        self._merge(tags, branch, feature)
                        break
            else:
                self._merge(tags, rule, feature)
        return tags

    def _merge(self, tags: dict[str, str], rule: dict, feature: dict) -> None:
        for key, spec in (rule.get("set") or {}).items():
            value = resolve_value(spec, feature)
            if value is not None and value != "":
                tags[key] = value
        for key in rule.get("unset") or []:
            tags.pop(key, None)
        compute = rule.get("compute")
        if compute:
            fn = COMPUTERS.get(compute["use"])
            if fn is None:
                raise ValueError(f"fonction compute inconnue : {compute['use']!r}")
            for key, value in fn(feature, compute.get("args", {})).items():
                if value is not None and value != "":
                    tags[key] = str(value)

    # -- contrôle de couverture

    def referenced_fields(self) -> set[str]:
        fields: set[str] = set()
        for entry in self.drop:
            fields |= condition_fields(entry.get("when"))
        for rule in self._walk_rules():
            fields |= condition_fields(rule.get("when"))
            for spec in (rule.get("set") or {}).values():
                fields |= value_fields(spec)
            compute = rule.get("compute")
            if compute:
                fields |= {v for v in compute.get("args", {}).values() if isinstance(v, str)}
        return fields

    def _walk_rules(self) -> Iterable[dict]:
        for rule in self.rules:
            yield rule
            for branch in rule.get("first_match", []):
                yield branch

    def coverage(self, source_fields: Iterable[str]) -> dict[str, set[str]]:
        """Compare les champs de la couche aux champs traités par les règles.

        `uncovered` non vide = le mapping est incomplet et doit être complété ou
        expliciter le motif d'abandon. C'est le garde-fou qui distingue un socle
        documenté d'un empilement de règles ad hoc.
        """
        source = {f for f in source_fields if f != "geometry"}
        used = self.referenced_fields()
        declared = set(self.unmapped)
        return {
            "used": used & source,
            "declared_unmapped": declared & source,
            "uncovered": source - used - declared,
            # Seule une déclaration LOCALE visant un champ inexistant est suspecte.
            "unknown": (used | (declared - self.common_unmapped)) - source,
        }
