# Image de démonstration : sert une base déjà convertie + iD.
# La conversion BD Topo → OSM ne tourne pas ici (dépendances géo lourdes,
# lectures IGN) : on convertit en local et on embarque la base.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Installation *editable* : `web/index.html` et `rules/` sont résolus par
# rapport au dépôt (`Path(__file__).parents[2]`). Une installation classique
# copierait le paquet dans site-packages et iD retomberait sur sa page par
# défaut, qui pointe vers openstreetmap.org.
COPY pyproject.toml README.md ./
COPY src ./src
COPY web/index.html ./web/index.html
RUN pip install --no-cache-dir -e ".[serve]"

# Build iD pré-compilé : branche `release` du dépôt amont (cf. README).
RUN mkdir -p web/id \
 && curl -fsSL https://codeload.github.com/openstreetmap/iD/tar.gz/refs/heads/release \
    | tar -xz -C web/id --strip-components=2 iD-release/dist

# DSFR (police Marianne + feuille de style) depuis le paquet npm officiel.
# Même logique que pour iD : récupéré à la construction, jamais versionné.
RUN mkdir -p web/dsfr  && V=$(curl -fsSL https://registry.npmjs.org/@gouvfr/dsfr/latest | python -c "import sys,json;print(json.load(sys.stdin)['version'])")  && curl -fsSL "https://registry.npmjs.org/@gouvfr/dsfr/-/dsfr-$V.tgz"     | tar -xz -C web/dsfr --strip-components=2 package/dist/dsfr.min.css package/dist/fonts
COPY web/bdfrance.css web/locale-fr.json ./web/

# Base de démonstration (Poitiers, socle complet). Sur un disque éphémère,
# chaque redémarrage repart de cet état : c'est le comportement annoncé.
COPY demo/poitiers.db ./demo/poitiers.db

# Hugging Face exécute le conteneur en utilisateur 1000 ; SQLite en WAL doit
# pouvoir écrire dans le répertoire de la base.
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

ENV PORT=7860
EXPOSE 7860

# --writable exige BDTOPO_DEMO_PASSWORD (secret du Space) : sans lui, le
# serveur refuse de démarrer en écriture sur 0.0.0.0. Retirer --writable pour
# une instance en lecture seule.
CMD ["bdtopo-osm", "serve", \
     "--db", "demo/poitiers.db", "--id", "web/id", \
     "--host", "0.0.0.0", "--writable", "--behind-proxy", "--ephemeral"]
