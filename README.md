---
title: BD France Édition
emoji: 🗺️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Démo iD sur des données IGN BD TOPO converties au modèle OSM
---

# bdtopo-osm — BD France Édition

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
| 3 | Socle OSM-utile : 28 couches converties (dont les limites administratives) | ✅ |
| 4 | Passage à l'échelle du département (moteur SQLite) | ✅ |
| 4b | Modules thématiques dans l'éditeur, filtrage serveur par couche, cadastre en surcouche | ✅ |
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

## Le socle : 28 couches

`--layers socle` convertit les couches listées dans `rules/socle.yaml`, **dans
l'ordre du manifeste** : linéaires et surfaciques d'abord, ponctuelles ensuite,
pour qu'un objet ponctuel en `point_mode: shared` trouve déjà en place le sommet
sur lequel se greffer. Vérifié sur Poitiers : les 92 pylônes sont tous des
sommets d'une `power=line` — la coïncidence exacte des coordonnées BD Topo
vaut aussi entre couches distinctes.

**Limites administratives** (`commune`, `canton`, `arrondissement`, `epci`,
`departement`) : chaque entité devient une relation `type=boundary` dont les
ways membres portent son contour (`polygon_mode: boundary` dans la règle,
relation systématique — c'est à `type=boundary` qu'iD reconnaît une limite).
Les contours restent propres à chaque entité : deux communes voisines ont
chacune leur anneau, à la différence de la pratique OSM des segments partagés
— mais les sommets, eux, sont mutualisés par la déduplication exacte, la couche
administrative de la BD Topo étant topologique comme les autres. Tags selon
les conventions OSM France : `admin_level` 8/7/6, `boundary=political` +
`political_division=canton` pour les cantons, `boundary=local_authority` +
`local_authority:FR=CC|CA|CU|metropole|EPT` pour les EPCI, `ref:INSEE`,
`ref:FR:SIREN`, `population` daté et sourcé. La région (214 524 sommets pour
un seul objet) reste hors socle, motif dans le manifeste.

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
déduplication des sommets dans une table `node_coords (lon, lat) → id`, outil
de conversion supprimé à la finalisation (et reconstruit depuis les sommets des
ways si l'on reprend au-dessus d'une base finalisée). Ce qui
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

## L'interface : BD France Édition

L'éditeur est iD, hébergé dans une page aux couleurs du **DSFR** (police
Marianne, bleu France) et débaptisé : plus aucune mention d'OpenStreetMap dans
l'interface hors des modules désactivés, attribution des données corrigée en
« IGN — BD France, Licence Ouverte 2.0 ». Trois pièces, aucune modification du
build d'iD :

- `web/index.html` — en-tête `fr-header` (sans bloc-marque République
  française, réservé), conteneur iD, pied de page avec la licence ;
- `web/bdfrance.css` — surcharge des variables CSS qu'iD expose
  (`--link-color`, `--accent-color`) et de la police ; masque le guide
  interactif (jeu de données fictif, tout en vocabulaire OSM) et les appels
  aux dons de l'écran de succès ;
- `web/locale-fr.json` — réécriture d'une cinquantaine de chaînes (accueil,
  enregistrement, statut d'API, calques) ; le serveur applique la surcharge sur
  `/locales/fr.min.json` et remplace globalement les mentions restantes, sauf
  dans l'index des communautés et le catalogue d'imagerie qui décrivent OSM.

Le DSFR est récupéré à la construction depuis le paquet npm `@gouvfr/dsfr`
(feuille de style et police), comme iD.

### Les modules thématiques

La barre sous l'en-tête (`web/modules.js`) propose des entrées thématiques —
Réseau routier, Bâti, Hydrographie, Limites administratives, Transports,
Énergie, Occupation du sol — qui ne montrent que les couches BD Topo de leur
thème. Un module est un sous-ensemble de couches ; l'activer allège la carte et
ouvre la voie à des outils propres à chaque thème. Deux mécanismes se
complètent :

- **côté éditeur**, une règle de filtrage iD par module, enregistrée à côté des
  règles natives (`context.features()`), qui reconnaît la couche d'origine au
  préfixe du `ref:FR:IGN:cleabs`. Activer un module désactive les règles
  natives et n'active que la sienne : iD masque un objet quand toutes les
  règles qu'il satisfait sont désactivées. Les objets créés dans l'éditeur,
  sans version, ne sont jamais masqués. Le panneau « Données de carte »
  l'explique quand un module est actif ;
- **côté serveur**, un cookie `bdf_layers` (ou le paramètre `layers=`) que
  `/api/0.6/map.json` honore : la réponse ne contient que les couches
  demandées, plus les objets sans provenance (créés à la main). Les tuiles
  deviennent légères, ce qui permet au module Limites administratives de
  charger dès le zoom 14 (`minEditableZoom`, tuiles de zoom 15) — une commune
  entière à l'écran, là où iD s'arrête au zoom 16.

Le module est porté par `#module=` dans l'URL (partageable) et mémorisé dans
le navigateur ; changer de module vide le cache de tuiles d'iD sans toucher à
l'historique des modifications en cours. Un effet de bord bienvenu : dans un
module, aucun seuil d'auto-masquage — iD cache d'ordinaire les bâtiments
au-delà de quelques centaines par écran.

### Le cadastre et Plan IGN en fond

`web/fonds.json` ajoute au catalogue d'imagerie d'iD deux flux WMTS de la
Géoplateforme, servis par le serveur sur `/data/imagery.min.json` : le
**Parcellaire Express (PCI)** en surcouche transparente — limites de parcelles
et numéros, un repère précis pour tracer ou ajuster une géométrie — et
**Plan IGN** en fond, tous deux dans le panneau Fond de carte (surcouches et
fonds). La BD Ortho, déjà au catalogue, reste le fond par défaut.

### La documentation BD TOPO Explorer dans l'éditeur

Le bouton ⓘ d'iD interroge un service (`osmWikibase`) qui renvoie un titre,
une définition et un lien — vers le wiki OSM. `web/index.html` intercepte ce
service : pour un tag `bdtopo:*` (ou `ref:FR:IGN:cleabs`), la réponse vient de
**BD TOPO Explorer** — définition de l'attribut ou de la valeur, et lien vers
son ancre exacte (`bdtopoexplorer.ign.fr/reservoir#attribute_value_465`). Pour
tout autre tag, le service d'origine répond comme d'habitude. La couche de
l'objet se déduit du préfixe de son `cleabs` (`RESERVOI…`, `TRONROUT…`).

La documentation est extraite hors ligne par `bdtopo-osm docs-explorer`
(`explorer.py`, 23 couches, 194 attributs, 1 151 valeurs) dans
`web/bdtopo-docs.json`, versionné et servi tel quel. Six couches n'ont pas de
définition de classe sur leur page (`troncon_de_route`, `zone_d_habitation`…) :
le champ reste vide plutôt que d'être rempli par la première définition
d'attribut rencontrée — c'est un piège de la structure HTML, et `bdtopo-extract`
y est tombé dans `_fetch_description`.

### Pourquoi ce tag ? — l'explication de chaque valeur

Le bouton ⓘ d'une clé OSM (`highway`, `building`, `building:material`…) sur un
objet issu de la BD Topo affiche d'abord **d'où vient la valeur** :

```
Déduit de la BD TOPO® : nature = « Route empierrée »
Règle : nature = Route empierrée (branche 7, classification exclusive)
Motif : Carrossable et publique selon la source (13 privées sur 56 369…) : donc
        unclassified, pas track, qui sous-entendrait un usage agricole non établi.
Référence OSM : (la documentation habituelle du wiki)
```

Trois mécanismes :

- `RuleSet.explain()` rejoue les règles en gardant, pour chaque tag, la règle
  qui l'a écrit, sa condition, les attributs lus et le `motif:` rédigé dans le
  YAML — ce champ, ajouté sur 31 règles dont la justification n'est pas
  évidente, est aussi exporté dans la table de correspondance.
- La table `provenance` conserve, par objet, les attributs BD Topo consultés
  par les règles (JSON compressé, ~240 octets par objet : 12 Mo pour Poitiers).
- `/api/bdfrance/explain/{type}/{id}` combine les deux ; la page d'iD l'appelle
  au clic et antépose l'explication à la référence OSM.

Un objet créé dans l'éditeur n'a pas de provenance : le panneau retombe sur la
référence OSM seule.

## Le serveur API 0.6

Endpoints implémentés : `/api/capabilities[.json]`, `/api/versions`,
`/api/0.6/map[.json]?bbox=`, la lecture unitaire `/api/0.6/{type}/{id}.json`,
`…/full.json`, `…/relations.json`, `/node/{id}/ways.json` et le multi-fetch
`/api/0.6/{type}s.json?{type}s=…` (iD s'en sert pour les liens profonds et
après enregistrement), plus `/healthz` et `/status`.
Les capabilities annoncent `api="readonly"`, ce qu'iD comprend nativement et qui
lui fait masquer les outils d'édition plutôt que d'échouer à l'enregistrement.

**Index spatial : R*Tree, pas quadtile.** Le serveur OSM officiel encode une
colonne *quadtile* parce que PostgreSQL n'offrait pas d'index spatial sans
PostGIS. SQLite embarque R*Tree en standard, qui fait le même travail sans
réimplémenter d'entrelacement de bits. Trois index : les nœuds
(`node_index`), l'emprise de chaque way (`way_index`) et les nœuds porteurs de
tags (`point_index`), ces deux derniers avec la couche BD Topo d'origine en
colonne auxiliaire. La sélection part des ways de l'emprise, ne garde que ceux
qui y ont un nœud, puis complète ; filtrer par couche (`?layers=` ou cookie
`bdf_layers`) revient à tester une colonne sur chaque candidat. Une tuile de
zoom 14 ne contenant que les limites administratives passe ainsi de 460 ms à
110 ms, une tuile de zoom 16 complète de 92 ms à 50 ms. Les index sont
construits à la finalisation et entretenus à chaque écriture (un nœud déplacé
recalcule l'emprise des ways qui l'utilisent) ; une base antérieure ouverte en
écriture les reçoit à la mise à niveau, en lecture seule elle reste servie par
le chemin d'origine, par les nœuds.

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

**Table de correspondance complète : [`docs/mapping.md`](docs/mapping.md)**
(1 256 lignes, aussi en classeur [`docs/mapping.xlsx`](docs/mapping.xlsx)), générée
depuis les règles par `bdtopo-osm mapping --md docs/mapping.md --xlsx docs/mapping.xlsx`
— à régénérer, jamais à éditer.

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
- **Limites administratives** en polygones simples : les contours ne sont pas
  décomposés en segments partagés entre communes voisines (les sommets, eux,
  le sont). Un déplacement de limite doit donc être fait deux fois.

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
