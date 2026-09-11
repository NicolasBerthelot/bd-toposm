---
title: BD TOPO → OpenStreetMap (Vienne)
emoji: 🗺️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Démo iD sur des données IGN BD TOPO converties au modèle OSM
---

# bdtopo-osm

Conversion de la **BD Topo® 3.5 (IGN)** vers le modèle de données **OpenStreetMap**
— nodes, ways, relations — en vue d'alimenter une instance de l'éditeur iD.
Terrain de démonstration : le département de la Vienne (86).

S'appuie sur [`bdtopo-extract`](../bdtopo-extract) pour la lecture en flux des
couches IGN.

## État

| Phase | Contenu | État |
|---|---|---|
| 0 | Reconnaissance, validation de l'hypothèse topologique | ✅ |
| 1 | Moteur de règles, mapping routes + bâti, écriture `.osm` | ✅ |
| 2a | Base SQLite + API 0.6 **en lecture**, iD branché dessus | ✅ |
| 2b | Écriture : changesets, upload osmChange, OAuth2 | ✅ |
| 3 | Socle OSM-utile : 23 couches converties | ✅ |
| 4 | Passage à l'échelle du département (moteur SQLite) | ✅ |
| 5 | Propagation de classe (bretelles, ronds-points), relations d'itinéraire et de cours d'eau | à faire |

## Usage

```powershell
.\.venv\Scripts\python.exe -m bdtopo_osm.cli `
    --layers troncon_de_route,batiment `
    --territoire commune:86194 `
    --output .\export\poitiers.osm --strict
```

`--territoire` accepte `commune:<insee|nom>`, `departement:<code|nom>`,
`bbox:xmin,ymin,xmax,ymax`. `--strict` fait échouer la conversion si un champ
source n'est ni utilisé ni documenté. `--db` charge en plus le résultat dans
une base SQLite servable.

```powershell
.\.venv\Scripts\python.exe -m bdtopo_osm.cli serve --db .\export\poitiers.db
```

## Le socle : 23 couches

`--layers socle` convertit les couches listées dans `rules/socle.yaml`, **dans
l'ordre du manifeste** : linéaires et surfaciques d'abord, ponctuelles ensuite,
pour qu'un objet ponctuel en `point_mode: shared` trouve déjà en place le sommet
sur lequel se greffer. Vérifié sur Poitiers : les 92 pylônes sont tous des
sommets d'une `power=line` — la coïncidence exacte des coordonnées BD Topo
vaut aussi entre couches distinctes.

Chaque exclusion du socle est motivée dans le manifeste. Trois méritent d'être
connues :

- **`haie` : 555 203 lignes dans la Vienne**, plus que le réseau routier
  entier, et les haies figurent *déjà* en 161 425 polygones dans
  `zone_de_vegetation` (écartés eux aussi). Les convertir saturerait iD.
- **`cours_d_eau` et `plan_d_eau`** sont des agrégations toponymiques des
  tronçons et surfaces hydrographiques : les convertir dupliquerait la
  géométrie. Leurs toponymes sont repris sur les couches de base.
- **`erp`** : 8 entités dans la Vienne pour 216 615 en France — la couche n'y
  est pas alimentée.

Deux mécanismes ont été ajoutés pour tenir 23 couches sans que le YAML devienne
illisible :

- `rules/_metadonnees_ign.yaml` mutualise les champs de métadonnées de
  production (dates, précisions, méthodes) écartés partout pour la même raison.
  Une déclaration locale reste prioritaire, et l'absence d'un champ commun dans
  une couche n'est pas signalée comme anomalie.
- Les natures sans équivalent OSM établi sortent avec `fixme=…` plutôt qu'avec
  un tag approchant. `fixme` est un vrai tag OSM, lu par les éditeurs et les
  outils de contrôle ; un `tourism=attraction` posé au jugé serait plus coûteux
  à corriger que l'aveu d'ignorance. Six `fixme` sur tout Poitiers.

Résultat sur Poitiers : 335 912 nœuds, 49 803 ways, 132 relations, aucun champ
non couvert en mode `--strict`.

## L'échelle du département

Le graphe d'un département ne tient pas en mémoire : `SqliteBuilder`
(`store_builder.py`) écrit au fil de l'eau dans la base cible et déplace la
déduplication des sommets dans une table `node_coords (lon, lat) → id`. Ce qui
rend l'exactitude possible : un REAL SQLite est le même double IEEE 754 que la
coordonnée shapely — l'égalité stricte garde exactement le sens qu'elle avait
en mémoire. Les règles topologiques (anneaux, multipolygones, découpage à
2 000 nœuds) sont partagées avec le moteur mémoire, qui reste celui des tests
et des communes ; `--engine auto` choisit SQLite dès qu'on demande `--db` sans
`.osm`.

```powershell
.\.venv\Scripts\python.exe -m bdtopo_osm.cli convert `
    --layers socle --territoire departement:86 --db .\exportienne.db --strict
```

Vienne, 23 couches, **22 minutes** (dont ~9 de lecture réseau), 1 Go de RAM au
pic, une transaction par couche :

```
9 504 802 nœuds · 832 688 ways · 2 555 relations · 1,9 Go
219 216 tronçons de route · 501 611 bâtiments · 41 952 zones de végétation
23 722 tronçons hydrographiques · 14 629 surfaces en eau · 13 225 lieux habités
```

Intégrité : zéro référence orpheline, zéro bâtiment non fermé, zéro way au-delà
de 2 000 nœuds ; 2 734 pylônes sur 2 739 sont des sommets d'une ligne (les cinq
autres portent des lignes qui sortent du département) ; 129 `fixme`.

Servi tel quel, l'API répond en **73 ms** pour une tuile de zoom 18 et en
~300 ms au zoom 17 — les mêmes latences que sur Poitiers : l'index R*Tree ne
sent pas la taille de la base. Seul `/status` (six `count(*)`) coûte une
seconde, d'où la sonde `/healthz` pour l'hébergeur.

## Le serveur API 0.6

Endpoints implémentés : `/api/capabilities`, `/api/0.6/capabilities`,
`/api/versions`, `/api/0.6/map?bbox=`, plus `/status` pour le diagnostic.
Les capabilities annoncent `api="readonly"`, ce qu'iD comprend nativement et qui
lui fait masquer les outils d'édition plutôt que d'échouer à l'enregistrement.

**Index spatial : R*Tree, pas quadtile.** Le serveur OSM officiel encode une
colonne *quadtile* parce que PostgreSQL n'offrait pas d'index spatial sans
PostGIS. SQLite embarque R*Tree en standard, qui fait le même travail sans
réimplémenter d'entrelacement de bits.

**La sélection n'est pas « tout ce qui est dans la boîte ».** Un way dont un
seul nœud tombe dans l'emprise revient **entier**, avec tous ses nœuds y compris
au-dehors ; sinon l'éditeur reçoit des géométries tronquées et croit que l'objet
s'arrête au bord de l'écran.

### Performance mesurée (Poitiers, 271 673 nœuds)

| Emprise | Réponse | Temps |
|---|---|---|
| Quartier | 0,66 Mo | 117 ms |
| Centre-ville | 3,25 Mo | 535 ms |
| Commune entière | 66 Mo | 11 s |

Débit constant d'environ 6 Mo/s, dominé par le formatage XML. iD ne charge
qu'à partir du zoom 16 et ne demande donc jamais plus qu'un quartier.

### iD

Le build d'iD n'est plus publié en archive de release : il faut soit le
compiler (`npm run build`, donc Node), soit récupérer la branche `release` du
dépôt, qui contient le `dist` déjà construit. C'est cette seconde voie qui est
utilisée — 20 Mo compressés, extraits dans `web/id/` (non versionné).

```powershell
curl -L -o id.tar.gz https://codeload.github.com/openstreetmap/iD/tar.gz/refs/heads/release
tar -xzf id.tar.gz -C web\id --strip-components=2 iD-release/dist
```

`web/index.html` remplace la page livrée avec le build et bascule la connexion
avant `context.init()` :

```js
context.connection().switch({ url: origine, apiUrl: origine });
```

**iD parle JSON, pas XML.** Point non documenté, relevé dans son code source :
il interroge `/api/capabilities.json` et `/api/0.6/map.json?bbox=`, jamais les
variantes XML. Il déréférence aussi `policy.imagery.blacklist.map(...)` sans
garde — ce tableau absent, c'est une page blanche au démarrage. Le contrat est
verrouillé par les tests `test_capabilities_json_couvre_ce_que_id_deréférence`
et `test_map_json_respecte_les_parseurs_id`.

**iD masque automatiquement les bâtiments au-delà d'un certain nombre.** À
Poitiers au zoom 17, 926 bâtiments dans l'emprise : `features().autoHidden()`
renvoie `["buildings"]` et rien ne s'affiche. Ce n'est pas un défaut de
conversion — c'est le garde-fou d'iD, qui se déclenche aussi sur
openstreetmap.org en zone dense. Au zoom 19 (139 bâtiments), plus rien n'est
masqué et les surfaces s'affichent normalement. À garder en tête : la BD Topo
couvre le bâti de façon exhaustive, donc ce seuil sera atteint plus souvent que
sur OSM.

### L'écriture

```powershell
.\.venv\Scripts\python.exe -m bdtopo_osm.cli serve `
    --db .\export\poitiers.db --id .\web\id --writable
```

Endpoints : `/oauth2/authorize`, `/oauth2/token`, `/api/0.6/user/details.json`,
`/api/0.6/changesets.json`, et le triptyque `changeset/create` →
`changeset/{id}/upload` → `changeset/{id}/close`.

⚠️ **L'OAuth2 est une façade, pas une authentification.** `/oauth2/authorize`
délivre un code à quiconque le demande et tous les jetons désignent le même
utilisateur synthétique : qui atteint le port peut modifier la base. `--writable`
est donc refusé sur un autre hôte que `127.0.0.1`. La vérification PKCE, elle,
est réelle — elle ne protège rien mais garantit la cohérence du protocole.

Quatre règles gouvernent l'application d'un diff, toutes reprises du serveur OSM
et couvertes par `tests/test_edit.py` :

| Règle | Comportement |
|---|---|
| Atomicité | Une erreur au dernier élément annule tout le diff. Sans cela un way survivrait en pointant vers un nœud jamais créé. |
| Identifiants de remplacement | Les objets créés arrivent en négatif, y compris dans `<nd ref="-3"/>`. Le serveur alloue et renvoie la correspondance dans le diffResult. |
| Conflit de version | Version annoncée ≠ version en base → `409 Version mismatch`. |
| Intégrité référentielle | Supprimer un nœud encore porté par un chemin → `412`, sauf `if-unused` qui laisse l'élément en place sans échouer. |

Les identifiants d'éléments supprimés ne sont jamais réattribués : une référence
obsolète chez un client pointerait sinon vers un objet sans rapport.

**Piège : iD compresse l'osmChange.** Quand le navigateur expose
`CompressionStream`, iD envoie le diff gzippé avec `Content-Encoding: gzip`.
Starlette ne décompresse pas les corps entrants — sans traitement explicite, le
parseur XML reçoit des octets gzip et l'enregistrement échoue sur une erreur de
syntaxe incompréhensible. Autre détail non évident : `/oauth2/token` reçoit ses
paramètres **en query string**, avec un corps vide.

Vérification de bout en bout effectuée depuis iD lui-même (`putChangeset`, donc
création du changeset, génération de l'osmChange, compression, envoi, clôture) :
un bâtiment de Poitiers est passé en version 2 avec `name` et
`building:levels=4` ajoutés, tous ses autres tags préservés.

Deux pièges rencontrés côté lecture, tous deux instructifs :

- **Le streaming balise par balise coûtait ×137.** Starlette itère un
  générateur synchrone via son pool de threads : *chaque* `yield` paie un
  aller-retour thread/async. 58 280 yields et 25,6 s pour 3,2 Mo, contre 0,19 s
  pour le même rendu en mémoire. Un tampon de 256 Ko règle le problème sans
  renoncer au streaming. Verrouillé par `test_tampon_regroupe_les_fragments`.
- **Un « coût serveur » de 3,5 s par requête qui n'existait pas.** Le banc
  d'essai construisait un `httpx.Client` neuf à chaque appel. Client réutilisé :
  266 ms. Mesurer l'instrument avant d'optimiser le code.

## Ce qui fonde le projet

### La BD Topo est déjà topologique

Mesuré sur Poitiers (11 991 tronçons, 23 982 extrémités) : les extrémités qui
coïncident le sont **exactement en float64** — arrondir à 1e-7 ne fusionne pas un
nœud de plus. La distribution des degrés est celle d'un vrai graphe routier
(5 662 nœuds de degré 3, 824 de degré 4).

La déduplication est donc un regroupement par coordonnée, **sans tolérance ni
snapping**. C'est ce qui rend l'étape sûre plutôt qu'heuristique, et c'est
l'hypothèse à revérifier avant d'ajouter une couche qui ne viendrait pas du même
modèle topologique.

### Le mapping est un livrable, pas du code

Les règles vivent dans `rules/*.yaml`, un fichier par couche. Le moteur
(`mapping.py`) impose trois disciplines :

1. **Rien d'implicite.** Chaque champ source est soit utilisé, soit déclaré dans
   `unmapped:` avec un motif. `--strict` échoue sinon.
2. **Une valeur absente ne produit pas de tag.** `lanes=nan` est pire que pas de
   `lanes`.
3. **Échappatoire explicite.** Les cas réfractaires au déclaratif passent par
   `compute:` et une fonction Python enregistrée, jamais par une contorsion du DSL.

### On ne fabrique pas d'information

Trois refus assumés, chacun documenté dans le YAML concerné :

- **`vitesse_moyenne_vl` n'est pas `maxspeed`.** C'est une vitesse moyenne
  observée, pas une limitation réglementaire. Elle sort sous
  `bdtopo:vitesse_moyenne_vl` — conservée, jamais travestie.
- **`Industriel, agricole ou commercial` sans usage précisé** (32 994 bâtiments)
  reste `building=yes`. Les trois fonctions candidates ont des valeurs OSM
  distinctes ; en choisir une serait inventer.
- **`usage_1=Annexe`** reste `building=yes` (ou `shed` si construction légère).
  OSM n'a pas de valeur consensuelle pour une annexe.

## Arbitrages notables

| Sujet | Décision | Motif |
|---|---|---|
| `Route empierrée` (16 % du réseau) | `highway=unclassified` + `surface=unpaved` | Carrossable et publique selon la source (13 privées sur 56 369). `track` sous-entendrait un usage agricole non établi. Requalifiable ; l'inverse perdrait de l'information. |
| Classification `highway` | `cpx_classement_administratif` prioritaire, `nature × importance` en repli | Le classement fait autorité mais n'est rempli qu'à 15,7 %. `importance` est un proxy du statut administratif, pas une classe fonctionnelle. |
| Nom de voie | BAN prioritaire malgré 32,6 % de couverture, contre 86,6 % pour `nom_collaboratif` | `nom_collaboratif` est du FANTOIR en majuscules abrégées (288 984 valeurs sur 296 962). Le repli est normalisé par `rules/abreviations_fantoir.yaml`. |
| Matériaux | Codes MAJIC DMATGM / DMATTO, premier chiffre = dominant | Le secondaire est perdu : OSM n'a qu'une valeur par clé. |
| Tronçons `fictif` | Conservés, tagués `bdtopo:fictif=yes` | Les retirer casserait la connexité du graphe routier. |

## Approximations connues

- **Bretelles et ronds-points** héritent leur classe de `importance`, faute
  d'information sur la route de raccordement. La bonne réponse est une
  propagation depuis les tronçons connectés — gratuite une fois le graphe
  construit, prévue en phase 3.
- **Nœuds de degré 2** conservés tels quels. Fusionner les tronçons adjacents à
  tags identiques (≈ 8 %) compliquerait la correspondance `cleabs → osm_id`, un
  way OSM valant alors plusieurs `cleabs`.
- **Limites administratives** hors périmètre : elles exigeraient une
  décomposition des contours en ways partagés entre communes voisines.

## Résultat sur Poitiers

```
11 991 tronçons + 35 529 bâtiments
→ 271 673 nodes, 47 667 ways, 111 relations   (51 Mo)
```

Contrôles passés : aucune référence orpheline, aucun bâtiment non fermé, aucun
way hors limite de 2 000 nœuds, aucun tag membre sur un way de multipolygone.

## Déploiement de la démo (Render)

L'image Docker sert une base déjà convertie — Poitiers, socle complet
(`demo/poitiers.db`, 66 Mo, versionné tel quel : Render ne récupère pas Git
LFS) — et iD, récupéré à la construction depuis la branche `release` du dépôt
amont. Le service n'embarque aucune dépendance géo : la conversion se fait en
local, seule la base voyage.

`render.yaml` décrit le service (Docker, plan gratuit, Francfort, contrôle de
santé sur `/status`). Depuis le tableau de bord Render : **New → Blueprint**,
choisir ce dépôt (`NicolasBerthelot/bd-toposm`), saisir `BDTOPO_DEMO_PASSWORD` quand il est demandé, appliquer.
Sans ce mot de passe le conteneur refuse de démarrer en écriture sur `0.0.0.0`
(garde-fou du CLI) ; pour une instance en lecture seule, retirer `--writable`
de la commande du `Dockerfile`.

Ce que ça donne : la fenêtre de connexion qu'iD ouvre affiche le formulaire de
mot de passe (le mot de passe s'insère dans le circuit OAuth2 sans le modifier),
tous les contributeurs partagent l'utilisateur « bdtopo », et **les modifications
sont réinitialisées à chaque redémarrage** — disque éphémère, annoncé dans la
page de connexion. Le plan gratuit endort le service après 15 minutes sans
visite ; le réveil prend une trentaine de secondes.

`--behind-proxy` fait confiance aux en-têtes `X-Forwarded-*` du proxy TLS de
l'hébergeur : sans cela, le contrôle d'origine du `redirect_uri` OAuth2
comparerait `https://…onrender.com` à `http://…:10000` et refuserait toute
connexion.

Le bloc YAML en tête de ce fichier vise Hugging Face Spaces ; il est inoffensif
ailleurs. Les Spaces Docker y exigent désormais un abonnement PRO — c'est ce
qui a conduit à Render.

Pour la Vienne entière (base de 1,9 Go), un hébergement gratuit ne suffit plus :
volume persistant (VM Oracle *Always Free*) ou VPS — même image, autre base,
récupérable à la construction depuis une *Release* GitHub (2 Go par fichier).

## Attention

Ces données ne doivent **pas** être versées dans `openstreetmap.org`. La BD Topo
est en Licence Ouverte 2.0, ce qui autorise cette instance locale (avec
attribution IGN), mais tout import réel relève de la procédure de validation de
la communauté OSM.
