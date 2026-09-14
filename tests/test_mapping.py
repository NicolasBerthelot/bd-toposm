from __future__ import annotations

import math

import pytest
import yaml

from bdtopo_osm.computers import normalize_street_name, nom_de_voie, title_case_fr
from bdtopo_osm.mapping import RuleSet, evaluate, is_empty, resolve_value
from bdtopo_osm.pipeline import RULES_DIR


def ruleset(doc: dict) -> RuleSet:
    return RuleSet(
        layer=doc.get("layer", "test"),
        description="",
        drop=doc.get("drop", []),
        rules=doc.get("rules", []),
        unmapped=doc.get("unmapped", {}),
    )


# ------------------------------------------------------------------- vacuité


@pytest.mark.parametrize("value", [None, float("nan"), "", "   "])
def test_valeurs_vides(value):
    assert is_empty(value)


@pytest.mark.parametrize("value", [0, 0.0, False, "0", "a"])
def test_valeurs_non_vides(value):
    """Zéro et False sont des valeurs, pas des absences."""
    assert not is_empty(value)


def test_pandas_na_est_vide():
    pd = pytest.importorskip("pandas")
    assert is_empty(pd.NA)
    assert is_empty(pd.NaT)


# ---------------------------------------------------------------- conditions


def test_egalite_insensible_au_type():
    """`importance` est une chaîne dans la source, un entier dans le YAML."""
    assert evaluate({"importance": 5}, {"importance": "5"})
    assert evaluate({"nombre_de_voies": 2}, {"nombre_de_voies": 2.0})


def test_operateurs():
    feature = {"n": 7.0, "nom": "Route de Poitiers", "vide": None}
    assert evaluate({"n": {"gte": 7}}, feature)
    assert not evaluate({"n": {"gt": 7}}, feature)
    assert evaluate({"nom": {"contains": "Poitiers"}}, feature)
    assert evaluate({"nom": {"matches": "^Route"}}, feature)
    assert evaluate({"vide": {"absent": True}}, feature)
    assert evaluate({"n": {"present": True}}, feature)


def test_combinateurs():
    feature = {"a": "x", "b": "y"}
    assert evaluate({"all_of": [{"a": "x"}, {"b": "y"}]}, feature)
    assert evaluate({"any_of": [{"a": "z"}, {"b": "y"}]}, feature)
    assert evaluate({"not": {"a": "z"}}, feature)
    assert not evaluate({"not": {"a": "x"}}, feature)


def test_condition_vide_matche_tout():
    assert evaluate({}, {"quoi": "que ce soit"})
    assert evaluate(None, {})


# ------------------------------------------------------------ valeurs de tag


def test_interpolation_annulee_si_champ_vide():
    """Un tag à trou vaut moins que pas de tag."""
    assert resolve_value("{cleabs}", {"cleabs": "ABC"}) == "ABC"
    assert resolve_value("{cleabs}", {"cleabs": None}) is None


def test_entiers_flottants_rendus_proprement():
    """`lanes=2.0` serait rejeté par les validateurs OSM."""
    assert resolve_value({"from": "n"}, {"n": 2.0}) == "2"
    assert resolve_value({"from": "n", "decimals": 1}, {"n": 6.26}) == "6.3"
    # `round` applique l'arrondi au pair le plus proche : 6.25 → 6.2, pas 6.3.
    # Sans conséquence sur une largeur de chaussée, mais autant le fixer.
    assert resolve_value({"from": "n", "decimals": 1}, {"n": 6.25}) == "6.2"


def test_drop_values():
    """La BD Topo code l'inconnu par 0 sur les champs quantitatifs."""
    spec = {"from": "nombre_de_voies", "drop_values": [0]}
    assert resolve_value(spec, {"nombre_de_voies": 0.0}) is None
    assert resolve_value(spec, {"nombre_de_voies": 2.0}) == "2"


def test_map_sans_correspondance_n_emet_rien():
    spec = {"from": "code", "map": {"10": "stone"}}
    assert resolve_value(spec, {"code": "10"}) == "stone"
    assert resolve_value(spec, {"code": "99"}) is None


def test_codes_materiaux_ne_sont_pas_lus_en_octal():
    """PyYAML lirait `01:` comme l'entier 1 ; les clés doivent rester des chaînes."""
    doc = yaml.safe_load((RULES_DIR / "batiment.yaml").read_text(encoding="utf-8"))
    rules = ruleset(doc)
    tags = rules.apply({"materiaux_des_murs": "01", "materiaux_de_la_toiture": "01"})
    assert tags["building:material"] == "stone"
    assert tags["roof:material"] == "roof_tiles"


# ----------------------------------------------------------------- premières


def test_first_match_est_exclusif():
    rules = ruleset(
        {
            "rules": [
                {
                    "first_match": [
                        {"when": {"nature": "Sentier"}, "set": {"highway": "path"}},
                        {"when": {}, "set": {"highway": "road"}},
                    ]
                }
            ]
        }
    )
    assert rules.apply({"nature": "Sentier"})["highway"] == "path"
    assert rules.apply({"nature": "Inconnue"})["highway"] == "road"


def test_drop_avec_motif():
    rules = ruleset({"drop": [{"when": {"etat": "En projet"}, "reason": "non construit"}]})
    assert rules.dropped_reason({"etat": "En projet"}) == "non construit"
    assert rules.apply({"etat": "En projet"}) is None
    assert rules.dropped_reason({"etat": "En service"}) is None


# ------------------------------------------------------------------ couverture


def test_couverture_signale_les_champs_oublies():
    rules = ruleset(
        {
            "rules": [{"set": {"source": "IGN", "ref": {"from": "cleabs"}}}],
            "unmapped": {"date_creation": "métadonnée"},
        }
    )
    cov = rules.coverage(["cleabs", "date_creation", "oublie", "geometry"])
    assert cov["used"] == {"cleabs"}
    assert cov["declared_unmapped"] == {"date_creation"}
    assert cov["uncovered"] == {"oublie"}


# ------------------------------------------------------- normalisation de nom


@pytest.mark.parametrize(
    "brut,attendu",
    [
        ("AV DU PARC D'ARTILLERIE", "Avenue du Parc d'Artillerie"),
        ("R DU HAUT DES SABLES", "Rue du Haut des Sables"),
        ("CHE DU COLONEL OCTAVE HONORAT", "Chemin du Colonel Octave Honorat"),
        ("IMP DES LILAS", "Impasse des Lilas"),
        ("RTE DE POITIERS", "Route de Poitiers"),
        ("PL DE LA LIBERTE", "Place de la Liberte"),
        ("BD DE PONT ACHARD", "Boulevard de Pont Achard"),
        ("R ST JEAN", "Rue Saint Jean"),
        ("R JEAN XXIII", "Rue Jean XXIII"),
        ("SAINT-JULIEN-L'ARS", "Saint-Julien-l'Ars"),
    ],
)
def test_normalisation_fantoir(brut, attendu):
    assert normalize_street_name(brut) == attendu


def test_nom_deja_correct_est_intact():
    """La source BAN est bien orthographiée : y toucher ne peut que nuire."""
    for nom in ("Rue du Haut des Sables", "Chemin de la Croix Blanche"):
        assert normalize_street_name(nom) == nom


def test_faux_amis_du_poitou_non_developpes():
    """CHEZ, LA, LES sont des mots du toponyme, pas des abréviations."""
    assert normalize_street_name("CHEZ BERNARD") == "Chez Bernard"
    assert normalize_street_name("LA GRANGE AUX MOINES") == "La Grange aux Moines"


def test_premier_mot_inconnu_non_developpe():
    assert normalize_street_name("ZZZ DES VIGNES") == "Zzz des Vignes"


def test_espaces_parasites():
    assert normalize_street_name("   R  DES  LILAS  ") == "Rue des Lilas"
    assert normalize_street_name("   ") == ""


# ------------------------------------------------------- arbitrage gauche/droite


ARGS = {
    "left": "ban_g",
    "right": "ban_d",
    "fallback_left": "collab_g",
    "fallback_right": "collab_d",
}


def test_ban_prioritaire_sur_collaboratif():
    tags = nom_de_voie({"ban_g": "Rue des Lilas", "collab_g": "R DES LILAS"}, ARGS)
    assert tags == {"name": "Rue des Lilas", "source:name": "BAN"}


def test_repli_collaboratif_normalise():
    tags = nom_de_voie({"ban_g": None, "collab_g": "R DES LILAS"}, ARGS)
    assert tags["name"] == "Rue des Lilas"
    assert tags["source:name"] == "BD TOPO nom_collaboratif"


def test_divergence_de_casse_n_est_pas_une_divergence():
    """Incohérence de saisie BAN, pas une voie qui change de nom en son milieu."""
    tags = nom_de_voie(
        {"ban_g": "Rue des Deux Communes", "ban_d": "Rue des deux Communes"}, ARGS
    )
    assert tags["name"] == "Rue des Deux Communes"
    assert "name:left" not in tags


def test_cotes_divergents_ne_sont_pas_arbitres():
    tags = nom_de_voie({"ban_g": "Rue Nord", "ban_d": "Rue Sud"}, ARGS)
    assert tags["name:left"] == "Rue Nord"
    assert tags["name:right"] == "Rue Sud"
    assert "name" not in tags


def test_sans_nom():
    assert nom_de_voie({}, ARGS) == {}


# ------------------------------------------------------------------ socle


def test_chaque_regle_du_socle_se_charge():
    """Chaque couche du manifeste a une règle valide, et réciproquement."""
    from bdtopo_osm.pipeline import socle_layers

    layers = socle_layers()
    assert len(layers) >= 20
    for layer in layers:
        rules = RuleSet.load(RULES_DIR / f"{layer}.yaml")
        assert rules.layer == layer
        assert rules.rules, f"{layer} : aucune règle"
        # Chaque règle doit au moins produire la provenance.
        tags = rules.apply({"cleabs": "X"}) or {}
        assert tags.get("ref:FR:IGN:cleabs") == "X", f"{layer} : pas de traçabilité"


def test_metadonnees_communes_fusionnees():
    rules = RuleSet.load(RULES_DIR / "cimetiere.yaml")
    assert "date_creation" in rules.unmapped          # commun
    assert "importance" in rules.unmapped             # local


# --------------------------------------------------------- garde-fous socle


def test_aucune_regle_du_socle_n_a_de_condition_nulle():
    """Une clé `when:` vide (YAML `null`) équivaut à « toujours vrai ».

    C'est ainsi qu'un `motif: >-` mal placé a un jour avalé le bloc `all_of`
    qui le suivait et transformé chaque bâtiment de Poitiers en lieu de culte.
    Une règle qui *veut* s'appliquer partout n'écrit pas `when:` du tout.
    """
    from bdtopo_osm.pipeline import socle_layers

    for layer in socle_layers():
        rules = RuleSet.load(RULES_DIR / f"{layer}.yaml")
        for index, rule in enumerate(rules.rules):
            for candidate in [rule, *rule.get("first_match", [])]:
                assert not ("when" in candidate and candidate["when"] is None), (
                    f"{layer} : règle {index} a `when: null`"
                )


def test_une_maison_n_est_pas_un_lieu_de_culte():
    rules = RuleSet.load(RULES_DIR / "batiment.yaml")
    maison = rules.apply({"cleabs": "B1", "nature": "Indifférenciée", "usage_1": "Résidentiel",
                          "nombre_de_logements": 1.0})
    assert maison["building"] == "house"
    assert "amenity" not in maison and "religion" not in maison

    eglise = rules.apply({"cleabs": "B2", "nature": "Eglise", "usage_1": "Religieux"})
    assert eglise["building"] == "church"
    assert eglise["amenity"] == "place_of_worship"
