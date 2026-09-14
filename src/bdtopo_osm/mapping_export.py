"""Table de correspondance BD Topo → OSM, générée depuis les règles YAML.

Les règles sont la source de vérité ; cette table en est une *lecture* à plat,
pour qui veut relire le mapping sans parcourir vingt-trois fichiers YAML.
Régénérer plutôt qu'éditer : `bdtopo-osm mapping --md docs/mapping.md
--xlsx docs/mapping.xlsx`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .mapping import RuleSet, _PLACEHOLDER

EXCLU = "(entité écartée)"
NON_CONVERTI = "(non converti)"
REPRIS = "(valeur reprise telle quelle)"


@dataclass
class Row:
    champ: str
    valeur: str
    tag: str
    valeur_osm: str
    note: str = ""


# ------------------------------------------------------------- conditions


def _fmt_spec(field: str, spec) -> str:
    if isinstance(spec, list):
        return f"{field} ∈ {{{', '.join(str(v) for v in spec)}}}"
    if isinstance(spec, dict):
        parts = []
        for op, val in spec.items():
            if op in ("present", "absent"):
                renseigne = (op == "present") == bool(val)
                parts.append(f"{field} {'renseigné' if renseigne else 'vide'}")
            elif op == "contains":
                parts.append(f"{field} contient « {val} »")
            elif op == "matches":
                parts.append(f"{field} ~ /{val}/")
            elif op in ("in", "not_in"):
                sym = "∈" if op == "in" else "∉"
                parts.append(f"{field} {sym} {{{', '.join(str(v) for v in val)}}}")
            elif op in ("gt", "gte", "lt", "lte"):
                sym = {"gt": ">", "gte": "≥", "lt": "<", "lte": "≤"}[op]
                parts.append(f"{field} {sym} {val}")
            else:
                parts.append(f"{field} {op} {val}")
        return " et ".join(parts)
    if isinstance(spec, bool):
        return f"{field} = {'vrai' if spec else 'faux'}"
    return f"{field} = {spec}"


def format_condition(cond) -> str:
    if not cond:
        return "(sinon)"
    parts = []
    for key, spec in cond.items():
        if key == "all_of":
            parts.append(" et ".join(f"({format_condition(c)})" for c in spec))
        elif key == "any_of":
            parts.append(" ou ".join(f"({format_condition(c)})" for c in spec))
        elif key == "not":
            parts.append(f"non ({format_condition(spec)})")
        else:
            parts.append(_fmt_spec(key, spec))
    return " et ".join(parts)


def condition_fields_text(cond) -> str:
    from .mapping import condition_fields

    return ", ".join(sorted(condition_fields(cond))) or "—"


# ----------------------------------------------------------------- lignes


def _rows_for_set(set_spec: dict, condition: str, cond_fields: str, note: str) -> list[Row]:
    rows: list[Row] = []
    for tag, spec in (set_spec or {}).items():
        if isinstance(spec, dict) and "from" in spec:
            champ = spec["from"]
            extra = []
            if spec.get("decimals") is not None:
                extra.append(f"arrondi à {spec['decimals']} décimale(s)")
            if spec.get("scale") is not None:
                extra.append(f"× {spec['scale']}")
            if spec.get("drop_values"):
                extra.append(
                    "ignoré si valeur ∈ {" + ", ".join(str(v) for v in spec["drop_values"]) + "}"
                )
            if "map" in spec:
                for src, dst in spec["map"].items():
                    rows.append(Row(champ, str(src), tag, str(dst), _join(note, condition, extra)))
                if spec.get("default") is not None:
                    rows.append(Row(champ, "(autre valeur)", tag, str(spec["default"]), _join(note, condition, extra)))
            else:
                rows.append(Row(champ, REPRIS, tag, "= valeur source", _join(note, condition, extra)))
        elif isinstance(spec, str) and _PLACEHOLDER.search(spec):
            fields = ", ".join(_PLACEHOLDER.findall(spec))
            rows.append(Row(fields, REPRIS, tag, spec, _join(note, condition, [])))
        else:
            rows.append(Row(cond_fields, condition, tag, str(spec).replace("True", "yes"), note))
    return rows


def _join(note: str, condition: str, extra: list[str]) -> str:
    parts = [p for p in [note, f"si {condition}" if condition not in ("", "(sinon)", "(toujours)") else "", *extra] if p]
    return " ; ".join(parts)


def rows_for_ruleset(rules: RuleSet) -> list[Row]:
    rows: list[Row] = []

    for entry in rules.drop:
        rows.append(
            Row(condition_fields_text(entry.get("when")), format_condition(entry.get("when")),
                EXCLU, "", " ".join(str(entry.get("reason", "")).split()))
        )

    for rule in rules.rules:
        when = rule.get("when")
        cond = format_condition(when) if when else "(toujours)"
        fields = condition_fields_text(when)

        if "first_match" in rule:
            for i, branch in enumerate(rule["first_match"], 1):
                bwhen = branch.get("when")
                bcond = format_condition(bwhen)
                bfields = condition_fields_text(bwhen)
                note = f"branche {i} — exclusif, première correspondance"
                if when:
                    note += f" ; sous condition {cond}"
                if branch.get("motif"):
                    note += " ; motif : " + " ".join(str(branch["motif"]).split())
                rows.extend(_rows_for_set(branch.get("set"), bcond, bfields, note))
        else:
            motif = " ".join(str(rule.get("motif", "") or "").split())
            rows.extend(_rows_for_set(rule.get("set"), cond, fields, f"motif : {motif}" if motif else ""))

        compute = rule.get("compute")
        if compute:
            args = compute.get("args", {})
            champs = ", ".join(str(v) for v in args.values())
            rows.append(
                Row(champs, "(arbitrage par fonction)", f"compute:{compute['use']}",
                    "name / name:left / name:right / source:name"
                    if compute["use"] == "nom_de_voie" else "",
                    "Voir computers.py — priorité BAN, normalisation FANTOIR, "
                    "gauche/droite conservés seulement s'ils divergent réellement"
                    if compute["use"] == "nom_de_voie" else "")
            )

    for field, reason in rules.unmapped.items():
        origin = "métadonnée commune" if field in rules.common_unmapped else ""
        rows.append(Row(field, "", NON_CONVERTI, "", _join(" ".join(str(reason).split()), "", [origin] if origin else [])))

    return rows


# --------------------------------------------------------------- sorties


def load_all(rules_dir: Path) -> list[RuleSet]:
    manifest = yaml.safe_load((rules_dir / "socle.yaml").read_text(encoding="utf-8"))
    layers = [e["layer"] for e in manifest["couches"]]
    return [RuleSet.load(rules_dir / f"{layer}.yaml") for layer in layers], manifest


def _md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_markdown(rules_dir: Path, path: Path) -> int:
    rulesets, manifest = load_all(rules_dir)
    out = ["# Table de correspondance BD Topo® 3.5 → OpenStreetMap", "",
           "Générée depuis `rules/*.yaml` par `bdtopo-osm mapping` — ne pas éditer à la main.", "",
           "Lecture : une ligne = une correspondance. « (sinon) » désigne la branche par défaut d'une",
           "classification exclusive ; « (non converti) » un champ écarté, avec son motif.", "",
           "## Sommaire", "", "| Couche | Tag principal | Lignes | Champs écartés |", "|---|---|---:|---:|"]
    all_rows = {}
    for rs in rulesets:
        rows = rows_for_ruleset(rs)
        all_rows[rs.layer] = rows
        out.append(f"| [{rs.layer}](#{rs.layer.replace('_', '-')}) | `{rs.report_key or ''}` | {len(rows)} | {len(rs.unmapped)} |")
    out += ["", "### Couches examinées et hors socle", ""]
    for name, why in manifest.get("exclues", {}).items():
        out.append(f"- **{name}** — {' '.join(str(why).split())}")

    for rs in rulesets:
        out += ["", f"## {rs.layer}", "", " ".join(rs.description.split()), ""]
        if rs.point_mode == "shared":
            out += ["Couche ponctuelle en `point_mode: shared` : le nœud est mutualisé avec les sommets existants.", ""]
        out += ["| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |", "|---|---|---|---|---|"]
        for r in all_rows[rs.layer]:
            out.append("| " + " | ".join(_md_escape(x) for x in (r.champ, r.valeur, f"`{r.tag}`" if r.tag and not r.tag.startswith("(") else r.tag, r.valeur_osm, r.note)) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return sum(len(v) for v in all_rows.values())


def write_xlsx(rules_dir: Path, path: Path) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    rulesets, manifest = load_all(rules_dir)
    wb = Workbook()
    font = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    head_fill = PatternFill("solid", fgColor="000091")
    head_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    grey = Font(name="Arial", size=10, color="666666")
    wrap = Alignment(wrap_text=True, vertical="top")

    def header(ws, cols, widths):
        ws.append(cols)
        for i, w in enumerate(widths, 1):
            c = ws.cell(row=1, column=i)
            c.font, c.fill, c.alignment = head_font, head_fill, wrap
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}1"

    total = 0
    summary = wb.active
    summary.title = "Sommaire"
    header(summary, ["Couche", "Tag principal", "Description", "Lignes", "Champs écartés"], [30, 16, 90, 9, 14])
    for rs in rulesets:
        rows = rows_for_ruleset(rs)
        total += len(rows)
        summary.append([rs.layer, rs.report_key or "", " ".join(rs.description.split()), len(rows), len(rs.unmapped)])

        ws = wb.create_sheet(rs.layer[:31])
        header(ws, ["Champ BD Topo", "Valeur / condition", "Tag OSM", "Valeur OSM", "Remarque"], [30, 44, 26, 34, 80])
        for r in rows:
            ws.append([r.champ, r.valeur, r.tag, r.valeur_osm, r.note])
            line = ws.max_row
            for c in ws[line]:
                c.font, c.alignment = font, wrap
            if r.tag in (EXCLU, NON_CONVERTI):
                for c in ws[line]:
                    c.font = grey
            else:
                ws.cell(row=line, column=3).font = bold

    for line in summary.iter_rows(min_row=2):
        for c in line:
            c.font, c.alignment = font, wrap
    excl = wb.create_sheet("Hors socle")
    header(excl, ["Couche", "Motif"], [26, 110])
    for name, why in manifest.get("exclues", {}).items():
        excl.append([name, " ".join(str(why).split())])
        for c in excl[excl.max_row]:
            c.font, c.alignment = font, wrap

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return total
