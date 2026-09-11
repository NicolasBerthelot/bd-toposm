from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Le service n'a besoin ni de geopandas ni de shapely : l'import du pipeline
# est différé pour que l'image Docker de la démo reste légère.
RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


def _cmd_convert(args) -> int:
    from .pipeline import convert, format_report, socle_layers

    if args.layers.strip() == "socle":
        layers = socle_layers(Path(args.rules) / "socle.yaml")
        print(f"Socle OSM-utile : {len(layers)} couches")
    else:
        layers = [name.strip() for name in args.layers.split(",") if name.strip()]
    if not args.output and not args.db:
        print("Il faut au moins --output (fichier .osm) ou --db (base SQLite).", file=sys.stderr)
        return 2
    engine = args.engine
    if engine == "auto":
        # Sans .osm demandé, rien n'oblige à garder le graphe en mémoire.
        engine = "sqlite" if (args.db and not args.output) else "memory"

    builder, reports, written = convert(
        layers, args.territoire, args.output, args.rules, db=args.db, engine=engine
    )
    print(format_report(reports, builder, written))

    if args.db:
        from . import store

        con = store.connect(args.db, read_only=True)
        try:
            counts = store.counts(con)
        finally:
            con.close()
        print(f"\n── base {args.db} ({engine}) " + "─" * 30)
        for table, n in counts.items():
            print(f"   {table:<12} {n:>10}")

    uncovered = any(r.coverage["uncovered"] for r in reports)
    if uncovered and args.strict:
        print("\nÉchec : couverture de mapping incomplète.", file=sys.stderr)
        return 1
    return 0


def _cmd_serve(args) -> int:
    import uvicorn

    from .api import create_app

    if not Path(args.db).exists():
        print(f"Base introuvable : {args.db}", file=sys.stderr)
        return 1

    local = args.host in ("127.0.0.1", "localhost", "::1")
    # Le mot de passe vient de l'environnement, jamais de la ligne de commande :
    # un argument serait visible dans la liste des processus et l'historique.
    demo_password = os.environ.get("BDTOPO_DEMO_PASSWORD") or None

    if args.writable and not local and not demo_password:
        # Sans mot de passe, l'OAuth2 de cette instance est une façade : tout
        # jeton désigne le même utilisateur et `/oauth2/authorize` en délivre un
        # à qui le demande. Exposer l'écriture au-delà de la machine sans
        # barrière, c'est ouvrir la base à tous.
        print(
            f"Refus : --writable sur {args.host} exige un mot de passe de démo.\n"
            "Définir BDTOPO_DEMO_PASSWORD dans l'environnement (cf. auth.py).",
            file=sys.stderr,
        )
        return 1

    app = create_app(
        args.db,
        readonly=not args.writable,
        id_dir=args.id,
        demo_password=demo_password if args.writable else None,
        ephemeral=args.ephemeral,
    )
    mode = "lecture/écriture" if args.writable else "lecture seule"
    if args.writable and demo_password:
        mode += ", mot de passe de démo"
    print(f"API 0.6 ({mode}) sur http://{args.host}:{args.port}")
    print(f"  capabilities  http://{args.host}:{args.port}/api/capabilities")
    print(f"  diagnostic    http://{args.host}:{args.port}/status")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        # Derrière le proxy TLS d'un hébergeur, ce sont les en-têtes
        # X-Forwarded-* qui portent l'origine réelle ; sans eux, le contrôle du
        # redirect_uri OAuth2 comparerait https://… à http://…:7860 et refuserait.
        proxy_headers=args.behind_proxy,
        forwarded_allow_ips="*" if args.behind_proxy else None,
    )
    return 0


def _cmd_mapping(args) -> int:
    from .mapping_export import write_markdown, write_xlsx

    if not args.md and not args.xlsx:
        print("Il faut --md et/ou --xlsx.", file=sys.stderr)
        return 2
    if args.md:
        n = write_markdown(Path(args.rules), args.md)
        print(f"{args.md} : {n} lignes")
    if args.xlsx:
        n = write_xlsx(Path(args.rules), args.xlsx)
        print(f"{args.xlsx} : {n} lignes")
    return 0


def _cmd_docs_explorer(args) -> int:
    from .explorer import fetch_all
    from .pipeline import socle_layers

    payload = fetch_all(socle_layers(Path(args.rules) / "socle.yaml"), args.out)
    n_attr = sum(len(c["attributes"]) for c in payload["couches"].values())
    n_val = sum(len(a["values"]) for c in payload["couches"].values() for a in c["attributes"].values())
    print(f"{args.out} : {len(payload['couches'])} couches, {n_attr} attributs, {n_val} valeurs documentées")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Le rapport contient des caractères hors cp1252 (tirets, avertissements) ;
    # sous Windows, un stdout redirigé retombe sur cette page de code et lève.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="bdtopo-osm",
        description="Conversion BD Topo (IGN) vers le modèle OpenStreetMap, et service API 0.6.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="convertir des couches BD Topo en .osm")
    p.add_argument(
        "--layers",
        required=True,
        help="couches séparées par des virgules, ou 'socle' pour le socle OSM-utile",
    )
    p.add_argument(
        "--territoire",
        required=True,
        help="commune:<insee|nom> | departement:<code|nom> | bbox:xmin,ymin,xmax,ymax",
    )
    p.add_argument("--output", type=Path, help="fichier .osm à écrire (moteur mémoire)")
    p.add_argument("--db", type=Path, help="base SQLite cible")
    p.add_argument(
        "--engine",
        choices=("auto", "memory", "sqlite"),
        default="auto",
        help="auto : sqlite si --db sans --output (échelle département), sinon mémoire",
    )
    p.add_argument("--rules", type=Path, default=RULES_DIR, help="répertoire des règles")
    p.add_argument(
        "--strict",
        action="store_true",
        help="échouer si un champ source n'est ni utilisé ni documenté dans `unmapped:`",
    )
    p.set_defaults(func=_cmd_convert)

    p = sub.add_parser("serve", help="servir l'API 0.6 (et iD) depuis une base")
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8111")))
    p.add_argument(
        "--behind-proxy",
        action="store_true",
        help="faire confiance aux en-têtes X-Forwarded-* (hébergement derrière un proxy TLS)",
    )
    p.add_argument(
        "--ephemeral",
        action="store_true",
        help="afficher que les modifications ne survivent pas au redémarrage",
    )
    p.add_argument("--id", type=Path, default=None, help="répertoire du build iD à servir")
    p.add_argument(
        "--writable",
        action="store_true",
        help="annoncer l'API comme modifiable (par défaut : lecture seule)",
    )
    p.add_argument("--log-level", default="warning")
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("mapping", help="exporter la table de correspondance BD Topo → OSM")
    p.add_argument("--md", type=Path, help="fichier Markdown à écrire")
    p.add_argument("--xlsx", type=Path, help="classeur Excel à écrire")
    p.add_argument("--rules", type=Path, default=RULES_DIR)
    p.set_defaults(func=_cmd_mapping)

    p = sub.add_parser("docs-explorer", help="extraire la documentation BD TOPO Explorer (hors ligne)")
    p.add_argument("--out", type=Path, default=Path("web/bdtopo-docs.json"))
    p.add_argument("--rules", type=Path, default=RULES_DIR)
    p.set_defaults(func=_cmd_docs_explorer)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
