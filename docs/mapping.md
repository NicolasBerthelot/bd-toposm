# Table de correspondance BD Topo® 3.5 → OpenStreetMap

Générée depuis `rules/*.yaml` par `bdtopo-osm mapping` — ne pas éditer à la main.

Lecture : une ligne = une correspondance. « (sinon) » désigne la branche par défaut d'une
classification exclusive ; « (non converti) » un champ écarté, avec son motif.

## Sommaire

| Couche | Tag principal | Lignes | Champs écartés |
|---|---|---:|---:|
| [troncon_de_route](#troncon-de-route) | `highway` | 180 | 63 |
| [troncon_hydrographique](#troncon-hydrographique) | `waterway` | 71 | 40 |
| [troncon_de_voie_ferree](#troncon-de-voie-ferree) | `railway` | 56 | 22 |
| [ligne_electrique](#ligne-electrique) | `power` | 29 | 20 |
| [construction_lineaire](#construction-lineaire) | `man_made` | 41 | 21 |
| [batiment](#batiment) | `building` | 161 | 24 |
| [zone_de_vegetation](#zone-de-vegetation) | `natural` | 36 | 19 |
| [surface_hydrographique](#surface-hydrographique) | `water` | 53 | 28 |
| [zone_d_habitation](#zone-d-habitation) | `place` | 42 | 21 |
| [zone_d_activite_ou_d_interet](#zone-d-activite-ou-d-interet) | `amenity` | 113 | 22 |
| [equipement_de_transport](#equipement-de-transport) | `amenity` | 65 | 21 |
| [terrain_de_sport](#terrain-de-sport) | `leisure` | 48 | 19 |
| [reservoir](#reservoir) | `man_made` | 39 | 25 |
| [cimetiere](#cimetiere) | `landuse` | 27 | 21 |
| [parc_ou_reserve](#parc-ou-reserve) | `protect_class` | 43 | 20 |
| [construction_surfacique](#construction-surfacique) | `man_made` | 33 | 21 |
| [poste_de_transformation](#poste-de-transformation) | `power` | 25 | 21 |
| [piste_d_aerodrome](#piste-d-aerodrome) | `aeroway` | 26 | 21 |
| [aerodrome](#aerodrome) | `aeroway` | 32 | 20 |
| [commune](#commune) | `admin_level` | 44 | 28 |
| [canton](#canton) | `political_division` | 30 | 23 |
| [arrondissement](#arrondissement) | `admin_level` | 29 | 23 |
| [epci](#epci) | `local_authority:FR` | 33 | 22 |
| [departement](#departement) | `admin_level` | 28 | 21 |
| [lieu_dit_non_habite](#lieu-dit-non-habite) | `place` | 26 | 20 |
| [construction_ponctuelle](#construction-ponctuelle) | `man_made` | 43 | 21 |
| [pylone](#pylone) | `power` | 25 | 20 |
| [detail_hydrographique](#detail-hydrographique) | `natural` | 42 | 21 |

### Couches examinées et hors socle

- **haie** — 555 203 lignes dans la Vienne — plus que le réseau routier entier. Les haies sont déjà représentées deux fois dans la BD Topo (cette couche linéaire, et 161 425 polygones dans zone_de_vegetation). Les convertir saturerait iD, qui masque déjà les bâtiments au-delà de quelques centaines par écran. Règle simple (`barrier=hedge`) si l'arbitrage change.
- **cours_d_eau** — Agrégation toponymique des tronçons hydrographiques : la convertir dupliquerait leur géométrie. Le toponyme est repris sur les tronçons via `cpx_toponyme_de_cours_d_eau`. Candidat naturel à une relation `type=waterway`, à traiter avec les relations.
- **plan_d_eau** — Même logique : agrégation des surfaces hydrographiques, toponyme repris via `cpx_toponyme_de_plan_d_eau`.
- **erp** — 8 entités seulement dans la Vienne pour 216 615 en France : la couche n'y est pas alimentée. Rien à convertir.
- **transport_par_cable** — 2 entités dans la Vienne.
- **region** — Le contour de Nouvelle-Aquitaine compte 214 524 sommets pour un seul objet (`admin_level=4`) : hors d'échelle pour une démonstration départementale, et il alourdirait la base de démonstration au-delà de ce que GitHub accepte. Règle triviale (`boundary=administrative` + `admin_level=4`) si le périmètre devient national.
- **arrondissement_municipal** — Paris, Lyon, Marseille seulement ; aucun dans la Vienne.
- **commune_associee_ou_deleguee** — Communes fusionnées (`admin_level=9`) ; à ajouter avec les mêmes règles que `commune` si l'on veut les fractions des communes nouvelles.
- **collectivite_territoriale** — Confondue avec le département hors statuts particuliers (Corse, Paris, Lyon, outre-mer).
- **condominium** — Île des Faisans, seul objet de la couche.
- **adresse_ban** — Import adresses à part entière (volumétrie et règles propres), hors socle.

## troncon_de_route

Réseau routier BD Topo 3.5 → OSM. La classification `highway` suit une matrice à deux étages : `cpx_classement_administratif` fait autorité quand il est renseigné (15,7 % des tronçons dans la Vienne), `nature × importance` sert de repli pour les 84,3 % restants. Mesures sur le département 86, 342 922 tronçons.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| etat_de_l_objet | etat_de_l_objet = En projet | (entité écartée) |  | Tracé non construit, sans existence physique sur le terrain (8 entités dans la Vienne). OSM proscrit `highway=proposed` en dehors de projets documentés et validés localement. |
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| nature_de_la_restriction | nature_de_la_restriction ∈ {Piste cyclable, Voie verte} | `highway` | cycleway | branche 1 — exclusif, première correspondance ; motif : La restriction décrit ce qu'EST la voie — un aménagement cyclable propre — pas une contrainte qui s'y ajoute. Elle prime donc sur la nature. |
| etat_de_l_objet | etat_de_l_objet = En construction | `highway` | construction | branche 2 — exclusif, première correspondance |
| nature | nature = Escalier | `highway` | steps | branche 3 — exclusif, première correspondance |
| nature | nature = Sentier | `highway` | path | branche 4 — exclusif, première correspondance |
| nature | nature = Bac ou liaison maritime | `route` | ferry | branche 5 — exclusif, première correspondance |
| nature | nature = Bac ou liaison maritime | `motor_vehicle` | yes | branche 5 — exclusif, première correspondance |
| nature | nature = Chemin | `highway` | track | branche 6 — exclusif, première correspondance ; motif : « Chemin » BD Topo : prévu pour les véhicules ou engins d'exploitation, pas forcément carrossable par tous les temps — c'est la définition d'un `track`. |
| nature | nature = Chemin | `surface` | unpaved | branche 6 — exclusif, première correspondance ; motif : « Chemin » BD Topo : prévu pour les véhicules ou engins d'exploitation, pas forcément carrossable par tous les temps — c'est la définition d'un `track`. |
| nature | nature = Route empierrée | `highway` | unclassified | branche 7 — exclusif, première correspondance ; motif : Carrossable et publique selon la source (13 privées sur 56 369 dans la Vienne, 54 502 en accès libre) : donc `unclassified`, pas `track`, qui sous-entendrait un usage agricole non établi. Le revêtement est porté par `surface`, requalifiable. |
| nature | nature = Route empierrée | `surface` | unpaved | branche 7 — exclusif, première correspondance ; motif : Carrossable et publique selon la source (13 privées sur 56 369 dans la Vienne, 54 502 en accès libre) : donc `unclassified`, pas `track`, qui sous-entendrait un usage agricole non établi. Le revêtement est porté par `surface`, requalifiable. |
| importance | 1 | `highway` | motorway_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| importance | 2 | `highway` | trunk_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| importance | 3 | `highway` | primary_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| importance | 4 | `highway` | secondary_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| importance | 5 | `highway` | tertiary_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| importance | 6 | `highway` | tertiary_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| importance | (autre valeur) | `highway` | tertiary_link | branche 8 — exclusif, première correspondance ; motif : La BD Topo ne dit pas quelle route la bretelle raccorde ; la classe est déduite de `importance`. IGN affecte à une bretelle « l'importance la moins importante des deux tronçons qu'elle joint ». Approximation à remplacer par une propagation depuis les tronçons connectés. ; si nature = Bretelle |
| nature | nature = Rond-point | `junction` | roundabout | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. |
| nature | nature = Rond-point | `oneway` | yes | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. |
| importance | 1 | `highway` | primary | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| importance | 2 | `highway` | primary | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| importance | 3 | `highway` | secondary | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| importance | 4 | `highway` | tertiary | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| importance | 5 | `highway` | unclassified | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| importance | 6 | `highway` | unclassified | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| importance | (autre valeur) | `highway` | unclassified | branche 9 — exclusif, première correspondance ; motif : `junction=roundabout` est une forme, pas une classe : la classe vient de `importance`, à défaut de connaître la route la plus importante qui aboutit à l'anneau. ; si nature = Rond-point |
| cpx_classement_administratif | cpx_classement_administratif contient « Autoroute » | `highway` | motorway | branche 10 — exclusif, première correspondance ; motif : Le classement administratif fait autorité quand il est renseigné (15,7 % des tronçons de la Vienne). |
| cpx_classement_administratif, nature | (cpx_classement_administratif contient « Nationale ») et (nature ∈ {Type autoroutier, Route à 2 chaussées}) | `highway` | trunk | branche 11 — exclusif, première correspondance |
| cpx_classement_administratif | cpx_classement_administratif contient « Nationale » | `highway` | primary | branche 12 — exclusif, première correspondance |
| importance | 1 | `highway` | primary | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| importance | 2 | `highway` | primary | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| importance | 3 | `highway` | secondary | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| importance | 4 | `highway` | tertiary | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| importance | 5 | `highway` | unclassified | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| importance | 6 | `highway` | unclassified | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| importance | (autre valeur) | `highway` | unclassified | branche 13 — exclusif, première correspondance ; motif : Départementale : la classe suit `importance`, qu'IGN définit comme une hiérarchisation fonctionnelle du réseau (non administrative). Mesuré : importance 4 = 29 790 D sur 34 022 tronçons. ; si cpx_classement_administratif contient « Départementale » |
| cpx_numero, nature | nature = Type autoroutier et cpx_numero ~ /^[Aa]/ | `highway` | motorway | branche 14 — exclusif, première correspondance ; motif : Type autoroutier sans classement Autoroute : le préfixe du numéro tranche (A10 → motorway ; N147 en voie express → trunk). |
| nature | nature = Type autoroutier | `highway` | trunk | branche 15 — exclusif, première correspondance |
| importance | 1 | `highway` | trunk | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance | 2 | `highway` | primary | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance | 3 | `highway` | secondary | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance | 4 | `highway` | tertiary | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance | 5 | `highway` | unclassified | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance | 6 | `highway` | unclassified | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance | (autre valeur) | `highway` | unclassified | branche 16 — exclusif, première correspondance ; si nature = Route à 2 chaussées |
| importance, nature, urbain | nature = Route à 1 chaussée et importance = 5 et urbain = vrai | `highway` | residential | branche 17 — exclusif, première correspondance ; motif : Importance 5 = desserte locale (129 135 tronçons, le gros du réseau). `urbain` sépare la voirie de lotissement (`residential`) de la voie communale rase-campagne (`unclassified`). |
| importance | 1 | `highway` | primary | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| importance | 2 | `highway` | primary | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| importance | 3 | `highway` | secondary | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| importance | 4 | `highway` | tertiary | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| importance | 5 | `highway` | unclassified | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| importance | 6 | `highway` | service | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| importance | (autre valeur) | `highway` | unclassified | branche 18 — exclusif, première correspondance ; motif : Repli nature × importance pour les 84,3 % de tronçons sans classement administratif. ; si nature = Route à 1 chaussée |
| — | (sinon) | `highway` | road | branche 19 — exclusif, première correspondance |
| nom_voie_ban_gauche, nom_voie_ban_droite, nom_collaboratif_gauche, nom_collaboratif_droite | (arbitrage par fonction) | `compute:nom_de_voie` | name / name:left / name:right / source:name | Voir computers.py — priorité BAN, normalisation FANTOIR, gauche/droite conservés seulement s'ils divergent réellement |
| cpx_numero | (valeur reprise telle quelle) | `ref` | = valeur source |  |
| cpx_numero_route_europeenne | (valeur reprise telle quelle) | `int_ref` | = valeur source |  |
| cpx_gestionnaire | (valeur reprise telle quelle) | `operator` | = valeur source |  |
| cpx_gestionnaire | Vienne | `operator` | Département de la Vienne |  |
| cpx_gestionnaire | Haute-Vienne | `operator` | Département de la Haute-Vienne |  |
| cpx_gestionnaire | Charente | `operator` | Département de la Charente |  |
| cpx_gestionnaire | Indre | `operator` | Département de l'Indre |  |
| cpx_gestionnaire | Indre-et-Loire | `operator` | Département d'Indre-et-Loire |  |
| cpx_gestionnaire | Deux-Sèvres | `operator` | Département des Deux-Sèvres |  |
| cpx_gestionnaire | Maine-et-Loire | `operator` | Département de Maine-et-Loire |  |
| cpx_gestionnaire | Vienne/Deux-Sèvres | `operator` | Département de la Vienne;Département des Deux-Sèvres |  |
| cpx_gestionnaire | Charente/Vienne | `operator` | Département de la Charente;Département de la Vienne |  |
| sens_de_circulation | Sens direct | `oneway` | yes |  |
| sens_de_circulation | Sens inverse | `oneway` | -1 |  |
| nombre_de_voies | (valeur reprise telle quelle) | `lanes` | = valeur source | ignoré si valeur ∈ {0} |
| largeur_de_chaussee | (valeur reprise telle quelle) | `width` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| position_par_rapport_au_sol | 1 | `bridge` | yes |  |
| position_par_rapport_au_sol | 2 | `bridge` | yes |  |
| position_par_rapport_au_sol | 3 | `bridge` | yes |  |
| position_par_rapport_au_sol | 4 | `bridge` | yes |  |
| position_par_rapport_au_sol | -1 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -2 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -3 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -4 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -4 | `layer` | -4 |  |
| position_par_rapport_au_sol | -3 | `layer` | -3 |  |
| position_par_rapport_au_sol | -2 | `layer` | -2 |  |
| position_par_rapport_au_sol | -1 | `layer` | -1 |  |
| position_par_rapport_au_sol | 1 | `layer` | 1 |  |
| position_par_rapport_au_sol | 2 | `layer` | 2 |  |
| position_par_rapport_au_sol | 3 | `layer` | 3 |  |
| position_par_rapport_au_sol | 4 | `layer` | 4 |  |
| position_par_rapport_au_sol | Gué ou radier | `ford` | yes |  |
| prive | 1 | `access` | private |  |
| acces_vehicule_leger | Physiquement impossible | `motor_vehicle` | no |  |
| acces_vehicule_leger | Restreint aux ayants droit | `motor_vehicle` | destination |  |
| acces_vehicule_leger | A péage | `toll` | yes |  |
| acces_pieton | Libre | `foot` | yes |  |
| acces_pieton | Restreint aux ayants droit | `foot` | destination |  |
| matieres_dangereuses_interdites | 1 | `hazmat` | no |  |
| reserve_aux_bus | reserve_aux_bus renseigné | `access` | no |  |
| reserve_aux_bus | reserve_aux_bus renseigné | `psv` | designated |  |
| nature_de_la_restriction | nature_de_la_restriction = Voie verte | `foot` | designated |  |
| nature_de_la_restriction | nature_de_la_restriction = Voie verte | `bicycle` | designated |  |
| nature_de_la_restriction | nature_de_la_restriction = Voie verte | `motor_vehicle` | no |  |
| restriction_de_hauteur | (valeur reprise telle quelle) | `maxheight` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| restriction_de_poids_total | (valeur reprise telle quelle) | `maxweight` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| restriction_de_poids_par_essieu | (valeur reprise telle quelle) | `maxaxleload` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| restriction_de_largeur | (valeur reprise telle quelle) | `maxwidth` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| restriction_de_longueur | (valeur reprise telle quelle) | `maxlength` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| amenagement_cyclable_gauche | Piste cyclable | `cycleway:left` | track |  |
| amenagement_cyclable_gauche | Bande cyclable | `cycleway:left` | lane |  |
| amenagement_cyclable_gauche | Aménagement mixte hors voie verte | `cycleway:left` | shared_lane |  |
| amenagement_cyclable_droit | Piste cyclable | `cycleway:right` | track |  |
| amenagement_cyclable_droit | Bande cyclable | `cycleway:right` | lane |  |
| amenagement_cyclable_droit | Aménagement mixte hors voie verte | `cycleway:right` | shared_lane |  |
| vitesse_moyenne_vl | (valeur reprise telle quelle) | `bdtopo:vitesse_moyenne_vl` | = valeur source | ignoré si valeur ∈ {0} |
| fictif | True | `bdtopo:fictif` | yes |  |
| urbain | True | `bdtopo:urbain` | yes |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. |
| date_modification |  | (non converti) |  | Idem. |
| date_d_apparition |  | (non converti) |  | Idem — vide à 100 % sur la Vienne. |
| date_de_confirmation |  | (non converti) |  | Idem. |
| sources |  | (non converti) |  | Provenance interne IGN (2,6 % rempli) ; `source` porte déjà l'attribution. |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont, vide à 100 %. |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). |
| precision_planimetrique |  | (non converti) |  | Idem. |
| precision_altimetrique |  | (non converti) |  | Idem. |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_mise_en_service |  | (non converti) |  | Vide à 100 % sur la Vienne. |
| itineraire_vert |  | (non converti) |  | Itinéraire poids lourds recommandé ; pas de tag OSM établi. |
| periode_de_fermeture |  | (non converti) |  | Vide à 100 % sur la Vienne ; `conditional restrictions` à étudier. |
| borne_debut_gauche |  | (non converti) |  | Référencement linéaire (PR) — relève de `point_de_repere`. |
| borne_debut_droite |  | (non converti) |  | Idem. |
| borne_fin_gauche |  | (non converti) |  | Idem. |
| borne_fin_droite |  | (non converti) |  | Idem. |
| insee_commune_gauche |  | (non converti) |  | Rattachement administratif déductible de la géométrie. |
| insee_commune_droite |  | (non converti) |  | Idem. |
| alias_gauche |  | (non converti) |  | Nom d'usage secondaire ; candidat `alt_name`, à arbitrer en phase 3. |
| alias_droit |  | (non converti) |  | Idem. |
| liens_vers_route_nommee |  | (non converti) |  | Relation vers `route_numerotee_ou_nommee` — traitée en phase 3 par une relation OSM `type=route`. |
| liens_vers_itineraire_autre |  | (non converti) |  | Idem, vide à 100 % sur la Vienne. |
| cpx_toponyme_route_nommee |  | (non converti) |  | Redondant avec la relation à construire en phase 3. |
| cpx_toponyme_itineraire_cyclable |  | (non converti) |  | Vide à 100 % sur la Vienne. |
| cpx_toponyme_voie_verte |  | (non converti) |  | Vide à 100 % sur la Vienne. |
| cpx_nature_itineraire_autre |  | (non converti) |  | Vide à 100 % sur la Vienne. |
| cpx_toponyme_itineraire_autre |  | (non converti) |  | Vide à 100 % sur la Vienne. |
| delestage |  | (non converti) |  | Itinéraire de délestage, vide à 100 % sur la Vienne. |
| source_voie_ban_gauche |  | (non converti) |  | Métadonnée de l'appariement BAN, pas la donnée elle-même. |
| source_voie_ban_droite |  | (non converti) |  | Idem. |
| lieux_dits_ban_gauche |  | (non converti) |  | Rattachement au lieu-dit ; relève de `zone_d_habitation`. |
| lieux_dits_ban_droite |  | (non converti) |  | Idem. |
| identifiant_voie_ban_gauche |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer en phase 3 avec l'import adresses. |
| identifiant_voie_ban_droite |  | (non converti) |  | Idem. |
| id_ban_odonyme_gauche |  | (non converti) |  | Idem, vide à 100 % sur la Vienne. |
| id_ban_odonyme_droite |  | (non converti) |  | Idem. |
| sens_amenagement_cyclable_gauche |  | (non converti) |  | Sens de l'aménagement ; nécessite `cycleway:left:oneway`, à affiner en phase 3. |
| sens_amenagement_cyclable_droit |  | (non converti) |  | Idem. |
| vitesse_collaborative |  | (non converti) |  | Vide à 100 % sur la Vienne. |
| aire_de_retournement_dfci |  | (non converti) |  | Défense forêt contre l'incendie — vide à 100 % sur la Vienne. |
| gabarit_dfci |  | (non converti) |  | Idem. |
| impasse_dfci |  | (non converti) |  | Idem. |
| nature_detaillee_dfci |  | (non converti) |  | Idem. |
| ouvrage_d_art_limitant_dfci |  | (non converti) |  | Idem. |
| pente_maximale_dfci |  | (non converti) |  | Idem. |
| piste_dfci |  | (non converti) |  | Idem. |
| piste_dfci_debroussaillee |  | (non converti) |  | Idem. |
| piste_dfci_fosses |  | (non converti) |  | Idem. |
| sens_de_circulation_dfci |  | (non converti) |  | Idem. |
| tout_terrain_dfci |  | (non converti) |  | Idem. |
| vitesse_moyenne_dfci |  | (non converti) |  | Idem. |
| zone_de_croisement_dfci |  | (non converti) |  | Idem. |
| categorie_dfci |  | (non converti) |  | Idem. |

## troncon_hydrographique

Réseau hydrographique linéaire. Comme le réseau routier, il est déjà topologique — les tronçons partagent leurs extrémités. La classe OSM se déduit de `classe_de_largeur` (rivière au-delà de 5 m, ruisseau en deçà), `fosse` et `nature` prenant le pas quand ils sont renseignés. Mesures sur le département 86, 42 310 tronçons.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| etat_de_l_objet | etat_de_l_objet = Disparu | (entité écartée) |  | Cours d'eau qui n'existe plus sur le terrain (13 entités dans la Vienne). |
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| fosse | fosse = vrai | `waterway` | ditch | branche 1 — exclusif, première correspondance ; motif : Un fossé reste un fossé quelle que soit sa largeur : la nature de l'ouvrage l'emporte sur la classe dimensionnelle. |
| nature | nature = Canal | `waterway` | canal | branche 2 — exclusif, première correspondance |
| nature | nature = Aqueduc | `waterway` | canal | branche 3 — exclusif, première correspondance |
| nature | nature = Aqueduc | `bridge` | aqueduct | branche 3 — exclusif, première correspondance |
| classe_de_largeur | classe_de_largeur ∈ {Plus de 50 m, Entre 15 et 50 m, Entre 5 et 15 m} | `waterway` | river | branche 4 — exclusif, première correspondance ; motif : `classe_de_largeur` est le seul critère dimensionnel disponible ; le seuil OSM usuel entre `stream` et `river` (≈ 5 m) tombe exactement sur une borne de la nomenclature IGN. |
| — | (sinon) | `waterway` | stream | branche 5 — exclusif, première correspondance |
| nature | nature = Conduit buse | `tunnel` | culvert | motif : Écoulement busé sous un remblai ou une voirie : `tunnel=culvert`. |
| nature | nature = Conduit buse | `layer` | -1 | motif : Écoulement busé sous un remblai ou une voirie : `tunnel=culvert`. |
| position_par_rapport_au_sol | -1 | `tunnel` | culvert |  |
| position_par_rapport_au_sol | -2 | `tunnel` | culvert |  |
| position_par_rapport_au_sol | -3 | `tunnel` | culvert |  |
| position_par_rapport_au_sol | -4 | `tunnel` | culvert |  |
| position_par_rapport_au_sol | 1 | `bridge` | yes |  |
| position_par_rapport_au_sol | 2 | `bridge` | yes |  |
| position_par_rapport_au_sol | 3 | `bridge` | yes |  |
| position_par_rapport_au_sol | 4 | `bridge` | yes |  |
| position_par_rapport_au_sol | -4 | `layer` | -4 |  |
| position_par_rapport_au_sol | -3 | `layer` | -3 |  |
| position_par_rapport_au_sol | -2 | `layer` | -2 |  |
| position_par_rapport_au_sol | -1 | `layer` | -1 |  |
| position_par_rapport_au_sol | 1 | `layer` | 1 |  |
| position_par_rapport_au_sol | 2 | `layer` | 2 |  |
| position_par_rapport_au_sol | 3 | `layer` | 3 |  |
| position_par_rapport_au_sol | 4 | `layer` | 4 |  |
| persistance | Intermittent | `intermittent` | yes |  |
| cpx_toponyme_de_cours_d_eau | (valeur reprise telle quelle) | `name` | = valeur source |  |
| fictif | True | `bdtopo:fictif` | yes |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| code_hydrographique |  | (non converti) |  | Identifiant du référentiel hydrographique ; `ref:FR:IGN:cleabs` suffit à la traçabilité. |
| navigabilite |  | (non converti) |  | Faux partout dans la Vienne ; candidat `boat=yes` ailleurs. |
| salinite |  | (non converti) |  | Faux partout (département sans façade maritime). |
| numero_d_ordre |  | (non converti) |  | Ordre de Strahler — information de réseau, sans tag OSM établi. |
| strategie_de_classement |  | (non converti) |  | Vide. |
| origine |  | (non converti) |  | Naturel / artificiel. Recoupe déjà `waterway=canal` et `ditch` pour les cas où OSM fait la distinction ; l'exposer ailleurs n'apporterait rien. |
| perimetre_d_utilisation_ou_origine |  | (non converti) |  | Métadonnée de périmètre de diffusion. |
| sens_de_l_ecoulement |  | (non converti) |  | Toujours « Sens direct » : l'écoulement suit la numérisation, ce qu'OSM considère comme acquis pour un `waterway`. |
| reseau_principal_coulant |  | (non converti) |  | Classification de réseau interne. |
| trace_connu |  | (non converti) |  | Indicateur de qualité du tracé. |
| type_de_bras |  | (non converti) |  | Principal / Secondaire. Candidat `waterway=side_channel`, mais 16 195 des 42 310 sont « Inconnu » — trop incertain pour trancher. |
| commentaire_sur_l_objet_hydro |  | (non converti) |  | Note de saisie libre (27 entités). |
| code_du_cours_d_eau_bdcarthage |  | (non converti) |  | Identifiant d'un référentiel antérieur. |
| inventaire_police_de_l_eau |  | (non converti) |  | Statut réglementaire, hors modèle OSM. |
| identifiant_police_de_l_eau |  | (non converti) |  | Idem. |
| liens_vers_cours_d_eau |  | (non converti) |  | Rattachement au cours d'eau nommé. Le toponyme est déjà repris via `cpx_toponyme_de_cours_d_eau` ; construire les relations `type=waterway` demanderait de regrouper les tronçons — à traiter avec les relations. |
| lien_vers_noeud_hydrographique_ini |  | (non converti) |  | Topologie de réseau, déjà portée par le partage de nœuds. |
| lien_vers_noeud_hydrographique_fin |  | (non converti) |  | Idem. |
| liens_vers_surface_hydrographique |  | (non converti) |  | Rattachement à la surface en eau correspondante. |
| lien_vers_entite_de_transition |  | (non converti) |  | Vide (entités estuariennes). |
| cpx_toponyme_d_entite_de_transition |  | (non converti) |  | Vide. |

## troncon_de_voie_ferree

Réseau ferré. Comme la route et l'hydrographie, déjà topologique. Mesures sur le département 86, 1 108 tronçons — dont la LGV Sud Europe Atlantique.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| etat_de_l_objet | etat_de_l_objet = Non exploité | `railway` | disused | branche 1 — exclusif, première correspondance |
| nature | nature = LGV | `railway` | rail | branche 2 — exclusif, première correspondance |
| nature | nature = LGV | `highspeed` | yes | branche 2 — exclusif, première correspondance |
| nature | nature = LGV | `usage` | main | branche 2 — exclusif, première correspondance |
| nature | nature = Voie ferrée principale | `railway` | rail | branche 3 — exclusif, première correspondance |
| nature | nature = Voie ferrée principale | `usage` | main | branche 3 — exclusif, première correspondance |
| nature | nature = Voie de service | `railway` | rail | branche 4 — exclusif, première correspondance |
| nature | nature = Voie de service | `service` | siding | branche 4 — exclusif, première correspondance |
| — | (sinon) | `railway` | rail | branche 5 — exclusif, première correspondance |
| electrifie | True | `electrified` | contact_line |  |
| electrifie | False | `electrified` | no |  |
| nombre_de_voies | (valeur reprise telle quelle) | `tracks` | = valeur source | ignoré si valeur ∈ {0} |
| cpx_toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| usage | Fret | `usage` | freight |  |
| position_par_rapport_au_sol | 1 | `bridge` | yes |  |
| position_par_rapport_au_sol | 2 | `bridge` | yes |  |
| position_par_rapport_au_sol | 3 | `bridge` | yes |  |
| position_par_rapport_au_sol | 4 | `bridge` | yes |  |
| position_par_rapport_au_sol | -1 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -2 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -3 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -4 | `tunnel` | yes |  |
| position_par_rapport_au_sol | -4 | `layer` | -4 |  |
| position_par_rapport_au_sol | -3 | `layer` | -3 |  |
| position_par_rapport_au_sol | -2 | `layer` | -2 |  |
| position_par_rapport_au_sol | -1 | `layer` | -1 |  |
| position_par_rapport_au_sol | 1 | `layer` | 1 |  |
| position_par_rapport_au_sol | 2 | `layer` | 2 |  |
| position_par_rapport_au_sol | 3 | `layer` | 3 |  |
| position_par_rapport_au_sol | 4 | `layer` | 4 |  |
| usage | usage = Vélo-rail | `railway` | disused |  |
| usage | usage = Vélo-rail | `tourism` | attraction |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| largeur |  | (non converti) |  | Toujours « Normale » (écartement standard) dans la Vienne. |
| vitesse_maximale |  | (non converti) |  | Vide. |
| liens_vers_voie_ferree_nommee |  | (non converti) |  | Rattachement à la ligne nommée. Le toponyme est déjà repris via `cpx_toponyme` ; les relations `type=route` sont à traiter séparément. |

## ligne_electrique

Lignes électriques haute tension (réseau de transport RTE). 213 tronçons dans la Vienne. Les pylônes (couche `pylone`) en sont les sommets : leur `point_mode: shared` les greffe sur ces lignes.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `power` | line |  |
| voltage | 400 kV | `voltage` | 400000 |  |
| voltage | 225 kV | `voltage` | 225000 |  |
| voltage | 90 kV | `voltage` | 90000 |  |
| voltage | <63 kV | `bdtopo:voltage` | <63 kV |  |
| gestionnaire | (valeur reprise telle quelle) | `operator` | = valeur source |  |
| siren_gestionnaire | (valeur reprise telle quelle) | `operator:siren` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| etat_de_l_objet |  | (non converti) |  | Toujours « En service » dans la Vienne. |

## construction_lineaire

Ouvrages linéaires : ponts, murs, barrages, tunnels. Mesures sur le département 86, 9 857 entités — dont 4 724 ponts et 3 001 ruines.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature, nature_detaillee | nature = Pont et nature_detaillee = Viaduc | `man_made` | bridge | branche 1 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Pont et nature_detaillee = Viaduc | `bridge:structure` | viaduct | branche 1 — exclusif, première correspondance |
| nature | nature = Pont | `man_made` | bridge | branche 2 — exclusif, première correspondance |
| nature | nature = Tunnel | `man_made` | tunnel | branche 3 — exclusif, première correspondance |
| nature | nature = Barrage | `waterway` | dam | branche 4 — exclusif, première correspondance |
| nature | nature = Quai | `man_made` | quay | branche 5 — exclusif, première correspondance |
| nature | nature = Mur de soutènement | `barrier` | retaining_wall | branche 6 — exclusif, première correspondance |
| nature | nature = Mur anti-bruit | `barrier` | wall | branche 7 — exclusif, première correspondance |
| nature | nature = Mur anti-bruit | `wall` | noise_barrier | branche 7 — exclusif, première correspondance |
| nature | nature = Mur | `barrier` | wall | branche 8 — exclusif, première correspondance |
| nature | nature = Clôture | `barrier` | fence | branche 9 — exclusif, première correspondance |
| nature | nature = Ruines | `historic` | ruins | branche 10 — exclusif, première correspondance |
| nature | nature = Fronton de pelote basque | `leisure` | pitch | branche 11 — exclusif, première correspondance |
| nature | nature = Fronton de pelote basque | `sport` | pelota | branche 11 — exclusif, première correspondance |
| — | (sinon) | `fixme` | Nature BD TOPO sans équivalent OSM établi — à qualifier | branche 12 — exclusif, première correspondance |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |

## batiment

Bâti BD Topo 3.5 → OSM. La classification `building` croise `nature` (la forme ou le caractère remarquable) et `usage_1` (la fonction). `nature` prime quand elle est spécifique (Église, Château, Serre…), `usage_1` prend le relais pour les 90 % de bâtiments « Indifférenciée ». Mesures sur le département 86, 777 481 bâtiments.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| identifiants_rnb | (valeur reprise telle quelle) | `ref:FR:RNB` | = valeur source |  |
| origine_du_batiment | Cadastre | `source:geometry` | cadastre |  |
| origine_du_batiment | Imagerie aérienne | `source:geometry` | aerial_imagery |  |
| origine_du_batiment | Lidar HD | `source:geometry` | lidar |  |
| origine_du_batiment | Autre | `source:geometry` | other |  |
| etat_de_l_objet | etat_de_l_objet = En construction | `building` | construction | branche 1 — exclusif, première correspondance |
| etat_de_l_objet | etat_de_l_objet = En ruine | `building` | ruins | branche 2 — exclusif, première correspondance |
| nature | nature = Eglise | `building` | church | branche 3 — exclusif, première correspondance |
| nature | nature = Chapelle | `building` | chapel | branche 4 — exclusif, première correspondance |
| nature | nature = Château | `building` | castle | branche 5 — exclusif, première correspondance |
| nature | nature = Château | `historic` | castle | branche 5 — exclusif, première correspondance |
| nature | nature = Fort, blockhaus, casemate | `building` | bunker | branche 6 — exclusif, première correspondance |
| nature | nature = Tour, donjon | `building` | tower | branche 7 — exclusif, première correspondance |
| nature | nature = Moulin à vent | `building` | yes | branche 8 — exclusif, première correspondance |
| nature | nature = Moulin à vent | `man_made` | windmill | branche 8 — exclusif, première correspondance |
| nature | nature = Serre | `building` | greenhouse | branche 9 — exclusif, première correspondance |
| nature | nature = Silo | `building` | silo | branche 10 — exclusif, première correspondance |
| nature | nature = Tribune | `building` | grandstand | branche 11 — exclusif, première correspondance |
| nature | nature ∈ {Monument, Arc de triomphe} | `building` | yes | branche 12 — exclusif, première correspondance |
| nature | nature ∈ {Monument, Arc de triomphe} | `historic` | monument | branche 12 — exclusif, première correspondance |
| nature | nature = Arène ou théâtre antique | `building` | yes | branche 13 — exclusif, première correspondance |
| nature | nature = Arène ou théâtre antique | `historic` | amphitheatre | branche 13 — exclusif, première correspondance |
| nombre_de_logements, usage_1 | usage_1 = Résidentiel et nombre_de_logements = 1 | `building` | house | branche 14 — exclusif, première correspondance ; motif : 229 978 bâtiments résidentiels à exactement 1 logement dans la Vienne : `nombre_de_logements` étaye solidement la distinction maison / immeuble. |
| nombre_de_logements, usage_1 | usage_1 = Résidentiel et nombre_de_logements ≥ 2 | `building` | apartments | branche 15 — exclusif, première correspondance ; motif : Plusieurs logements dans un bâtiment résidentiel : immeuble. |
| usage_1 | usage_1 = Résidentiel | `building` | residential | branche 16 — exclusif, première correspondance |
| construction_legere, usage_1 | usage_1 = Annexe et construction_legere = vrai | `building` | shed | branche 17 — exclusif, première correspondance ; motif : OSM n'a pas de valeur consensuelle pour « annexe » (garages, remises, abris confondus) ; `construction_legere` isole au moins les abris légers. |
| usage_1 | usage_1 = Annexe | `building` | yes | branche 18 — exclusif, première correspondance ; motif : Annexe sans autre précision : `building=yes` avec l'usage source conservé, plutôt qu'une valeur inventée. |
| usage_1 | usage_1 = Commercial et services | `building` | commercial | branche 19 — exclusif, première correspondance |
| usage_1 | usage_1 = Industriel | `building` | industrial | branche 20 — exclusif, première correspondance |
| usage_1 | usage_1 = Agricole | `building` | farm_auxiliary | branche 21 — exclusif, première correspondance |
| usage_1 | usage_1 = Religieux | `building` | religious | branche 22 — exclusif, première correspondance |
| usage_1 | usage_1 = Sportif | `building` | sports_hall | branche 23 — exclusif, première correspondance |
| nature | nature = Industriel, agricole ou commercial | `building` | yes | branche 24 — exclusif, première correspondance ; motif : La nature exclut le résidentiel mais ne tranche pas entre trois fonctions aux valeurs OSM distinctes : en choisir une serait fabriquer de l'information. La nature source est conservée, requalifiable. |
| — | (sinon) | `building` | yes | branche 25 — exclusif, première correspondance |
| nature, usage_1 | (nature ∈ {Eglise, Chapelle}) et (usage_1 = Religieux) | `amenity` | place_of_worship | motif : `nature` donne la forme du bâtiment, `usage_1` atteste l'usage courant : c'est leur conjonction qui justifie `amenity=place_of_worship`, pas la forme seule. |
| nature, usage_1 | (nature ∈ {Eglise, Chapelle}) et (usage_1 = Religieux) | `religion` | christian | motif : `nature` donne la forme du bâtiment, `usage_1` atteste l'usage courant : c'est leur conjonction qui justifie `amenity=place_of_worship`, pas la forme seule. |
| hauteur | (valeur reprise telle quelle) | `height` | = valeur source | arrondi à 1 décimale(s) |
| nombre_d_etages | (valeur reprise telle quelle) | `building:levels` | = valeur source |  |
| nombre_de_logements | (valeur reprise telle quelle) | `building:flats` | = valeur source | ignoré si valeur ∈ {0} |
| materiaux_des_murs | 1 | `building:material` | stone |  |
| materiaux_des_murs | 01 | `building:material` | stone |  |
| materiaux_des_murs | 10 | `building:material` | stone |  |
| materiaux_des_murs | 11 | `building:material` | stone |  |
| materiaux_des_murs | 12 | `building:material` | stone |  |
| materiaux_des_murs | 13 | `building:material` | stone |  |
| materiaux_des_murs | 14 | `building:material` | stone |  |
| materiaux_des_murs | 15 | `building:material` | stone |  |
| materiaux_des_murs | 16 | `building:material` | stone |  |
| materiaux_des_murs | 19 | `building:material` | stone |  |
| materiaux_des_murs | 2 | `building:material` | stone |  |
| materiaux_des_murs | 02 | `building:material` | stone |  |
| materiaux_des_murs | 20 | `building:material` | stone |  |
| materiaux_des_murs | 21 | `building:material` | stone |  |
| materiaux_des_murs | 22 | `building:material` | stone |  |
| materiaux_des_murs | 23 | `building:material` | stone |  |
| materiaux_des_murs | 24 | `building:material` | stone |  |
| materiaux_des_murs | 25 | `building:material` | stone |  |
| materiaux_des_murs | 26 | `building:material` | stone |  |
| materiaux_des_murs | 29 | `building:material` | stone |  |
| materiaux_des_murs | 3 | `building:material` | concrete |  |
| materiaux_des_murs | 03 | `building:material` | concrete |  |
| materiaux_des_murs | 30 | `building:material` | concrete |  |
| materiaux_des_murs | 31 | `building:material` | concrete |  |
| materiaux_des_murs | 32 | `building:material` | concrete |  |
| materiaux_des_murs | 33 | `building:material` | concrete |  |
| materiaux_des_murs | 34 | `building:material` | concrete |  |
| materiaux_des_murs | 35 | `building:material` | concrete |  |
| materiaux_des_murs | 36 | `building:material` | concrete |  |
| materiaux_des_murs | 39 | `building:material` | concrete |  |
| materiaux_des_murs | 4 | `building:material` | brick |  |
| materiaux_des_murs | 04 | `building:material` | brick |  |
| materiaux_des_murs | 40 | `building:material` | brick |  |
| materiaux_des_murs | 41 | `building:material` | brick |  |
| materiaux_des_murs | 42 | `building:material` | brick |  |
| materiaux_des_murs | 43 | `building:material` | brick |  |
| materiaux_des_murs | 44 | `building:material` | brick |  |
| materiaux_des_murs | 45 | `building:material` | brick |  |
| materiaux_des_murs | 46 | `building:material` | brick |  |
| materiaux_des_murs | 49 | `building:material` | brick |  |
| materiaux_des_murs | 5 | `building:material` | cement_block |  |
| materiaux_des_murs | 05 | `building:material` | cement_block |  |
| materiaux_des_murs | 50 | `building:material` | cement_block |  |
| materiaux_des_murs | 51 | `building:material` | cement_block |  |
| materiaux_des_murs | 52 | `building:material` | cement_block |  |
| materiaux_des_murs | 53 | `building:material` | cement_block |  |
| materiaux_des_murs | 54 | `building:material` | cement_block |  |
| materiaux_des_murs | 55 | `building:material` | cement_block |  |
| materiaux_des_murs | 56 | `building:material` | cement_block |  |
| materiaux_des_murs | 59 | `building:material` | cement_block |  |
| materiaux_des_murs | 6 | `building:material` | wood |  |
| materiaux_des_murs | 06 | `building:material` | wood |  |
| materiaux_des_murs | 60 | `building:material` | wood |  |
| materiaux_des_murs | 61 | `building:material` | wood |  |
| materiaux_des_murs | 62 | `building:material` | wood |  |
| materiaux_des_murs | 63 | `building:material` | wood |  |
| materiaux_des_murs | 64 | `building:material` | wood |  |
| materiaux_des_murs | 65 | `building:material` | wood |  |
| materiaux_des_murs | 66 | `building:material` | wood |  |
| materiaux_des_murs | 69 | `building:material` | wood |  |
| materiaux_de_la_toiture | 1 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 01 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 10 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 11 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 12 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 13 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 14 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 19 | `roof:material` | roof_tiles |  |
| materiaux_de_la_toiture | 2 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 02 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 20 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 21 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 22 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 23 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 24 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 29 | `roof:material` | slate |  |
| materiaux_de_la_toiture | 3 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 03 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 30 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 31 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 32 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 33 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 34 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 39 | `roof:material` | metal |  |
| materiaux_de_la_toiture | 4 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 04 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 40 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 41 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 42 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 43 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 44 | `roof:material` | concrete |  |
| materiaux_de_la_toiture | 49 | `roof:material` | concrete |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source | ignoré si valeur ∈ {Indifférenciée} |
| usage_1 | (valeur reprise telle quelle) | `bdtopo:usage` | = valeur source | ignoré si valeur ∈ {Indifférencié} |
| usage_2 | (valeur reprise telle quelle) | `bdtopo:usage_2` | = valeur source | ignoré si valeur ∈ {Indifférencié} |
| construction_legere | True | `bdtopo:construction_legere` | yes |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. |
| date_modification |  | (non converti) |  | Idem. |
| date_d_apparition |  | (non converti) |  | Idem. |
| date_de_confirmation |  | (non converti) |  | Idem. |
| sources |  | (non converti) |  | Provenance interne IGN ; `source` porte déjà l'attribution. |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem. |
| precision_planimetrique |  | (non converti) |  | Idem. |
| precision_altimetrique |  | (non converti) |  | Idem. |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| altitude_minimale_sol |  | (non converti) |  | Altimétrie — la dimension Z est supprimée à la conversion. |
| altitude_minimale_toit |  | (non converti) |  | Idem. |
| altitude_maximale_toit |  | (non converti) |  | Idem ; `height` porte déjà la hauteur du bâtiment. |
| altitude_maximale_sol |  | (non converti) |  | Idem. |
| appariement_fichiers_fonciers |  | (non converti) |  | Indicateur de qualité de l'appariement (lettre + score). Métadonnée de production, sans équivalent OSM. |

## zone_de_vegetation

Couverture végétale. Couche volumineuse — 260 779 polygones dans la Vienne, 13,9 M en France — dont **161 425 de nature « Haie »**, écartés ici : la BD Topo 3.5 livre par ailleurs une couche `haie` linéaire dédiée et plus précise, et conserver les deux représenterait chaque haie deux fois.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| nature | nature = Haie | (entité écartée) |  | Double représentation : 161 425 polygones dans la Vienne qui redoublent la couche linéaire `haie` (555 203 entités), plus précise et issue d'un levé dédié. Voir rules/socle.yaml pour l'arbitrage de volumétrie. |
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| nature | nature = Vigne | `landuse` | vineyard | branche 1 — exclusif, première correspondance |
| nature | nature = Verger | `landuse` | orchard | branche 2 — exclusif, première correspondance |
| nature | nature = Peupleraie | `landuse` | forest | branche 3 — exclusif, première correspondance ; motif : Plantation exploitée : `landuse=forest` plutôt que `natural=wood`, qui suggère un boisement spontané. |
| nature | nature = Peupleraie | `leaf_type` | broadleaved | branche 3 — exclusif, première correspondance ; motif : Plantation exploitée : `landuse=forest` plutôt que `natural=wood`, qui suggère un boisement spontané. |
| nature | nature = Lande ligneuse | `natural` | scrub | branche 4 — exclusif, première correspondance |
| nature | nature = Forêt ouverte | `natural` | scrub | branche 5 — exclusif, première correspondance ; motif : Couvert discontinu, plus proche du fourré que du bois. |
| nature | nature = Forêt fermée de feuillus | `natural` | wood | branche 6 — exclusif, première correspondance |
| nature | nature = Forêt fermée de feuillus | `leaf_type` | broadleaved | branche 6 — exclusif, première correspondance |
| nature | nature = Forêt fermée de conifères | `natural` | wood | branche 7 — exclusif, première correspondance |
| nature | nature = Forêt fermée de conifères | `leaf_type` | needleleaved | branche 7 — exclusif, première correspondance |
| nature | nature = Forêt fermée mixte | `natural` | wood | branche 8 — exclusif, première correspondance |
| nature | nature = Forêt fermée mixte | `leaf_type` | mixed | branche 8 — exclusif, première correspondance |
| — | (sinon) | `natural` | wood | branche 9 — exclusif, première correspondance |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |

## surface_hydrographique

Surfaces en eau. La couche `plan_d_eau` (1 403 entités) n'est pas convertie : c'est une agrégation toponymique bâtie sur ces mêmes surfaces, et la reprendre dupliquerait les polygones. Son toponyme est déjà disponible ici via `cpx_toponyme_de_plan_d_eau`. Mesures sur le département 86, 27 911 surfaces.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| nature | nature = Marais | `natural` | wetland | branche 1 — exclusif, première correspondance |
| nature | nature = Marais | `wetland` | marsh | branche 1 — exclusif, première correspondance |
| nature | nature ∈ {Lac, Plan d'eau de gravière} | `natural` | water | branche 2 — exclusif, première correspondance |
| nature | nature ∈ {Lac, Plan d'eau de gravière} | `water` | lake | branche 2 — exclusif, première correspondance |
| nature | nature ∈ {Retenue-barrage, Retenue-bassin portuaire} | `natural` | water | branche 3 — exclusif, première correspondance |
| nature | nature ∈ {Retenue-barrage, Retenue-bassin portuaire} | `water` | reservoir | branche 3 — exclusif, première correspondance |
| nature | nature = Réservoir-bassin piscicole | `natural` | water | branche 4 — exclusif, première correspondance |
| nature | nature = Réservoir-bassin piscicole | `water` | fish_pond | branche 4 — exclusif, première correspondance |
| nature | nature = Réservoir-bassin d'orage | `landuse` | basin | branche 5 — exclusif, première correspondance ; motif : Bassin technique : `landuse=basin` décrit l'ouvrage, `natural=water` décrirait l'eau — ici c'est l'ouvrage qui est cartographié. |
| nature | nature = Réservoir-bassin d'orage | `basin` | detention | branche 5 — exclusif, première correspondance ; motif : Bassin technique : `landuse=basin` décrit l'ouvrage, `natural=water` décrirait l'eau — ici c'est l'ouvrage qui est cartographié. |
| nature | nature = Réservoir-bassin | `landuse` | basin | branche 6 — exclusif, première correspondance |
| nature | nature = Canal | `natural` | water | branche 7 — exclusif, première correspondance |
| nature | nature = Canal | `water` | canal | branche 7 — exclusif, première correspondance |
| nature | nature ∈ {Ecoulement naturel, Ecoulement canalisé, Conduit buse} | `natural` | water | branche 8 — exclusif, première correspondance |
| nature | nature ∈ {Ecoulement naturel, Ecoulement canalisé, Conduit buse} | `water` | river | branche 8 — exclusif, première correspondance |
| — | (sinon) | `natural` | water | branche 9 — exclusif, première correspondance ; motif : « Retenue » (15 876) et « Mare » (7 057) forment l'essentiel du bocage poitevin : petites pièces d'eau, très majoritairement artificielles. |
| — | (sinon) | `water` | pond | branche 9 — exclusif, première correspondance ; motif : « Retenue » (15 876) et « Mare » (7 057) forment l'essentiel du bocage poitevin : petites pièces d'eau, très majoritairement artificielles. |
| persistance | Intermittent | `intermittent` | yes |  |
| cpx_toponyme_de_plan_d_eau | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| etat_de_l_objet | (valeur reprise telle quelle) | `bdtopo:etat` | = valeur source | ignoré si valeur ∈ {En service} |
| position_par_rapport_au_sol | -1 | `layer` | -1 |  |
| position_par_rapport_au_sol | -1 | `tunnel` | culvert |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| code_hydrographique |  | (non converti) |  | Identifiant du référentiel hydrographique. |
| salinite |  | (non converti) |  | Nul partout (département sans façade maritime). |
| origine |  | (non converti) |  | Naturel / artificiel. 20 048 surfaces sur 27 911 sont artificielles ; OSM n'a pas de tag consensuel pour cette distinction sur une pièce d'eau. |
| commentaire_sur_l_objet_hydro |  | (non converti) |  | Vide. |
| liens_vers_plan_d_eau |  | (non converti) |  | Rattachement à l'agrégation toponymique `plan_d_eau`, volontairement non convertie (elle dupliquerait ces mêmes polygones). |
| liens_vers_cours_d_eau |  | (non converti) |  | Vide. |
| lien_vers_entite_de_transition |  | (non converti) |  | Vide. |
| cpx_toponyme_de_cours_d_eau |  | (non converti) |  | Vide sur cette couche. |
| cpx_toponyme_d_entite_de_transition |  | (non converti) |  | Vide. |

## zone_d_habitation

Lieux habités, en polygones. OSM place plutôt ces objets sur des nœuds, mais la BD Topo en donne l'emprise et `place=*` s'applique aussi à une surface. Mesures sur le département 86, 23 853 zones.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature_detaillee | nature_detaillee ∈ {Château ruiné, Tour ruinée, Eglise ruinée} | `historic` | ruins | branche 1 — exclusif, première correspondance |
| nature | nature = Ruines | `historic` | ruins | branche 2 — exclusif, première correspondance |
| nature_detaillee | nature_detaillee = Château fort | `historic` | castle | branche 3 — exclusif, première correspondance |
| nature_detaillee | nature_detaillee = Château fort | `castle_type` | defensive | branche 3 — exclusif, première correspondance |
| nature | nature = Château | `historic` | castle | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Quartier et nature_detaillee = Quartier urbain | `place` | suburb | branche 5 — exclusif, première correspondance |
| nature | nature = Quartier | `place` | neighbourhood | branche 6 — exclusif, première correspondance |
| nature | nature ∈ {Moulin, Grange} | `place` | locality | branche 7 — exclusif, première correspondance ; motif : OSM n'a pas de valeur consensuelle pour ces lieux-dits bâtis, et la source ne dit pas s'il s'agit d'un moulin à vent ou à eau : on reste sur le toponyme, nature conservée. |
| importance | 1 | `place` | town | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| importance | 2 | `place` | village | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| importance | 3 | `place` | village | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| importance | 4 | `place` | hamlet | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| importance | 5 | `place` | isolated_dwelling | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| importance | 6 | `place` | isolated_dwelling | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| importance | (autre valeur) | `place` | locality | branche 8 — exclusif, première correspondance ; motif : « Lieu-dit habité » : `importance` est le seul critère de hiérarchie disponible. Calibration à relire : elle décide de ce qui s'affiche comme village ou comme écart. |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source | ignoré si valeur ∈ {Lieu-dit habité} |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| fictif | True | `bdtopo:fictif` | yes |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Consommé par la matrice `place` ci-dessus ; le déclarer ici évite de laisser croire qu'il serait exporté tel quel. |
| etat_de_l_objet |  | (non converti) |  | Toujours « En service » sur cette couche dans la Vienne. |

## zone_d_activite_ou_d_interet

Zones d'activité et d'intérêt — la couche la plus riche en points d'intérêt de la BD Topo : 92 natures distinctes réparties en 8 catégories. Mesures sur le département 86, 8 318 zones. Les natures sans équivalent OSM établi ne reçoivent pas de tag approchant : elles sortent avec `fixme`, qui est un vrai tag OSM signalant un objet à qualifier. Inventer une valeur plausible serait plus coûteux à corriger que de signaler l'ignorance.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| etat_de_l_objet | etat_de_l_objet = Non exploité | (entité écartée) |  | Équipement désaffecté (12 entités dans la Vienne). |
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | nature = Culte chrétien | `amenity` | place_of_worship | branche 1 — exclusif, première correspondance |
| nature | nature = Culte chrétien | `religion` | christian | branche 1 — exclusif, première correspondance |
| nature | nature = Culte musulman | `amenity` | place_of_worship | branche 2 — exclusif, première correspondance |
| nature | nature = Culte musulman | `religion` | muslim | branche 2 — exclusif, première correspondance |
| nature | nature = Culte divers | `amenity` | place_of_worship | branche 3 — exclusif, première correspondance |
| nature | nature = Tombeau | `historic` | tomb | branche 4 — exclusif, première correspondance |
| nature | nature = Station d'épuration | `man_made` | wastewater_plant | branche 5 — exclusif, première correspondance |
| nature | nature = Station de pompage | `man_made` | pumping_station | branche 6 — exclusif, première correspondance |
| nature | nature = Usine de production d'eau potable | `man_made` | water_works | branche 7 — exclusif, première correspondance |
| nature | nature = Mairie | `amenity` | townhall | branche 8 — exclusif, première correspondance |
| nature | nature = Poste | `amenity` | post_office | branche 9 — exclusif, première correspondance |
| nature | nature = Caserne de pompiers | `amenity` | fire_station | branche 10 — exclusif, première correspondance |
| nature | nature ∈ {Gendarmerie, Police} | `amenity` | police | branche 11 — exclusif, première correspondance |
| nature | nature = Palais de justice | `amenity` | courthouse | branche 12 — exclusif, première correspondance |
| nature | nature = Etablissement pénitentiaire | `amenity` | prison | branche 13 — exclusif, première correspondance |
| nature | nature ∈ {Enceinte militaire, Ouvrage militaire, Camp militaire non clos} | `landuse` | military | branche 14 — exclusif, première correspondance |
| nature | nature = Caserne | `landuse` | military | branche 15 — exclusif, première correspondance |
| nature | nature = Caserne | `military` | barracks | branche 15 — exclusif, première correspondance |
| nature | nature = Champ de tir | `landuse` | military | branche 16 — exclusif, première correspondance |
| nature | nature = Champ de tir | `military` | range | branche 16 — exclusif, première correspondance |
| nature | nature ∈ {Préfecture, Sous-préfecture, Hôtel de région, Hôtel de département, Administration centrale de l'Etat, Autre service déconcentré de l'Etat, Siège d'EPCI, Divers public ou administratif} | `office` | government | branche 17 — exclusif, première correspondance |
| nature | nature = Aire d'accueil des gens du voyage | `tourism` | caravan_site | branche 18 — exclusif, première correspondance ; motif : `caravan_site` est l'usage OSM français pour ces aires, malgré l'ambiguïté du terme touristique. |
| nature | nature = Aire d'accueil des gens du voyage | `permanent` | yes | branche 18 — exclusif, première correspondance ; motif : `caravan_site` est l'usage OSM français pour ces aires, malgré l'ambiguïté du terme touristique. |
| nature | nature ∈ {Enseignement primaire, Collège, Lycée, Autre établissement d'enseignement} | `amenity` | school | branche 19 — exclusif, première correspondance |
| nature | nature ∈ {Université, Enseignement supérieur} | `amenity` | university | branche 20 — exclusif, première correspondance |
| nature | nature = Science | `amenity` | research_institute | branche 21 — exclusif, première correspondance |
| nature | nature = Structure d'accueil pour personnes handicapées | `amenity` | social_facility | branche 22 — exclusif, première correspondance |
| nature | nature = Structure d'accueil pour personnes handicapées | `social_facility` | assisted_living | branche 22 — exclusif, première correspondance |
| nature | nature ∈ {Hôpital, Etablissement hospitalier} | `amenity` | hospital | branche 23 — exclusif, première correspondance |
| nature | nature = Maison de retraite | `amenity` | social_facility | branche 24 — exclusif, première correspondance |
| nature | nature = Maison de retraite | `social_facility` | nursing_home | branche 24 — exclusif, première correspondance |
| nature | nature = Etablissement thermal | `amenity` | public_bath | branche 25 — exclusif, première correspondance |
| nature | nature = Etablissement thermal | `bath:type` | thermal | branche 25 — exclusif, première correspondance |
| nature | nature ∈ {Zone industrielle, Divers industriel} | `landuse` | industrial | branche 26 — exclusif, première correspondance |
| nature | nature = Usine | `landuse` | industrial | branche 27 — exclusif, première correspondance |
| nature | nature = Usine | `man_made` | works | branche 27 — exclusif, première correspondance |
| nature | nature = Centrale électrique | `power` | plant | branche 28 — exclusif, première correspondance |
| nature | nature = Déchèterie | `amenity` | recycling | branche 29 — exclusif, première correspondance |
| nature | nature = Déchèterie | `recycling_type` | centre | branche 29 — exclusif, première correspondance |
| nature | nature ∈ {Carrière, Mine} | `landuse` | quarry | branche 30 — exclusif, première correspondance |
| nature | nature = Marché | `amenity` | marketplace | branche 31 — exclusif, première correspondance |
| nature | nature = Aquaculture | `landuse` | aquaculture | branche 32 — exclusif, première correspondance |
| nature | nature ∈ {Elevage, Haras, Divers agricole} | `landuse` | farmyard | branche 33 — exclusif, première correspondance |
| nature | nature = Divers commercial | `landuse` | retail | branche 34 — exclusif, première correspondance |
| nature | nature = Stade | `leisure` | stadium | branche 35 — exclusif, première correspondance |
| nature | nature = Golf | `leisure` | golf_course | branche 36 — exclusif, première correspondance |
| nature | nature = Centre équestre | `leisure` | horse_riding | branche 37 — exclusif, première correspondance |
| nature | nature = Hippodrome | `leisure` | track | branche 38 — exclusif, première correspondance |
| nature | nature = Hippodrome | `sport` | horse_racing | branche 38 — exclusif, première correspondance |
| nature | nature = Piscine | `leisure` | sports_centre | branche 39 — exclusif, première correspondance |
| nature | nature = Piscine | `sport` | swimming | branche 39 — exclusif, première correspondance |
| nature | nature = Baignade surveillée | `leisure` | swimming_area | branche 40 — exclusif, première correspondance |
| nature | nature = Baignade surveillée | `supervised` | yes | branche 40 — exclusif, première correspondance |
| nature | nature = Patinoire | `leisure` | sports_centre | branche 41 — exclusif, première correspondance |
| nature | nature = Patinoire | `sport` | ice_skating | branche 41 — exclusif, première correspondance |
| nature | nature = Stand de tir | `leisure` | sports_centre | branche 42 — exclusif, première correspondance |
| nature | nature = Stand de tir | `sport` | shooting | branche 42 — exclusif, première correspondance |
| nature | nature = Equipement de cyclisme | `leisure` | sports_centre | branche 43 — exclusif, première correspondance |
| nature | nature = Equipement de cyclisme | `sport` | cycling | branche 43 — exclusif, première correspondance |
| nature | nature = Sports mécaniques | `leisure` | sports_centre | branche 44 — exclusif, première correspondance |
| nature | nature = Sports mécaniques | `sport` | motor | branche 44 — exclusif, première correspondance |
| nature | nature = Sports en eaux vives | `leisure` | sports_centre | branche 45 — exclusif, première correspondance |
| nature | nature = Sports en eaux vives | `sport` | canoe | branche 45 — exclusif, première correspondance |
| nature | nature = Sports nautiques | `leisure` | sports_centre | branche 46 — exclusif, première correspondance |
| nature | nature = Sports nautiques | `sport` | sailing | branche 46 — exclusif, première correspondance |
| nature | nature = Site d'escalade | `sport` | climbing | branche 47 — exclusif, première correspondance |
| nature | nature = Site de vol libre | `sport` | free_flying | branche 48 — exclusif, première correspondance |
| nature | nature ∈ {Complexe sportif couvert, Autre équipement sportif} | `leisure` | sports_centre | branche 49 — exclusif, première correspondance |
| nature | nature ∈ {Musée, Ecomusée} | `tourism` | museum | branche 50 — exclusif, première correspondance |
| nature | nature = Parc zoologique | `tourism` | zoo | branche 51 — exclusif, première correspondance |
| nature | nature = Camping | `tourism` | camp_site | branche 52 — exclusif, première correspondance |
| nature | nature = Point de vue | `tourism` | viewpoint | branche 53 — exclusif, première correspondance |
| nature | nature ∈ {Office de tourisme, Maison du parc} | `tourism` | information | branche 54 — exclusif, première correspondance |
| nature | nature ∈ {Office de tourisme, Maison du parc} | `information` | office | branche 54 — exclusif, première correspondance |
| nature | nature = Monument | `historic` | monument | branche 55 — exclusif, première correspondance |
| nature | nature = Mégalithe | `historic` | archaeological_site | branche 56 — exclusif, première correspondance |
| nature | nature = Mégalithe | `site_type` | megalith | branche 56 — exclusif, première correspondance |
| nature | nature = Vestige archéologique | `historic` | archaeological_site | branche 57 — exclusif, première correspondance |
| nature | nature = Centre de documentation | `amenity` | library | branche 58 — exclusif, première correspondance |
| nature | nature ∈ {Salle de spectacle ou conférence, Salle de danse ou de jeux} | `amenity` | community_centre | branche 59 — exclusif, première correspondance ; motif : En milieu rural ces salles sont le plus souvent des salles des fêtes : `community_centre` plutôt que `theatre`. |
| nature | nature = Parc des expositions | `amenity` | exhibition_centre | branche 60 — exclusif, première correspondance |
| nature | nature ∈ {Espace public, Aire de détente, Parc de loisirs} | `leisure` | park | branche 61 — exclusif, première correspondance |
| — | (sinon) | `fixme` | Nature BD TOPO sans équivalent OSM établi — à qualifier | branche 62 — exclusif, première correspondance ; motif : Nature sans correspondance OSM assumée : `fixme` est un vrai tag, lu par les éditeurs et les outils de contrôle — préférable à un `tourism=attraction` posé au jugé. |
| categorie | (valeur reprise telle quelle) | `bdtopo:categorie` | = valeur source |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| fictif | True | `bdtopo:fictif` | yes |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| adresse_postale |  | (non converti) |  | Adresse en texte libre et de qualité inégale (« rue basse », champs vides). Découper en `addr:housenumber` / `addr:street` exigerait un travail de normalisation qui relève de l'import adresses, pas de cette couche. |
| nom_commercial |  | (non converti) |  | Vide dans la Vienne. |

## equipement_de_transport

Équipements liés aux transports : parkings, gares, aires, bornes de recharge. Mesures sur le département 86, 2 039 entités — dont 739 « Service dédié aux véhicules » qui sont toutes des bornes de recharge électrique.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| etat_de_l_objet | etat_de_l_objet = Non exploité | (entité écartée) |  | Équipement désaffecté (1 entité dans la Vienne). |
| nature | nature = Carrefour | (entité écartée) |  | Emprise de carrefour (431 entités) redondante avec le réseau routier, qui porte déjà ronds-points et bretelles. |
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Parking souterrain | `amenity` | parking | branche 1 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Parking souterrain | `parking` | underground | branche 1 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Parking couvert | `amenity` | parking | branche 2 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Parking couvert | `parking` | multi-storey | branche 2 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Parking relais | `amenity` | parking | branche 3 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Parking relais | `park_ride` | yes | branche 3 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Aire de covoiturage | `amenity` | parking | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Aire de covoiturage | `parking` | surface | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Aire de covoiturage | `carpool` | yes | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Parking et nature_detaillee = Aire de camping-cars | `tourism` | caravan_site | branche 5 — exclusif, première correspondance |
| nature | nature = Parking | `amenity` | parking | branche 6 — exclusif, première correspondance |
| nature | nature = Parking | `parking` | surface | branche 6 — exclusif, première correspondance |
| nature | nature = Service dédié aux véhicules | `amenity` | charging_station | branche 7 — exclusif, première correspondance ; motif : 739 entités, toutes « Borne de rechargement électrique » d'après `nature_detaillee` ; la source Etalab (opérateurs IRVE) le confirme. |
| nature | nature = Service dédié aux véhicules | `motorcar` | yes | branche 7 — exclusif, première correspondance ; motif : 739 entités, toutes « Borne de rechargement électrique » d'après `nature_detaillee` ; la source Etalab (opérateurs IRVE) le confirme. |
| nature, nature_detaillee | nature = Aire de repos ou de service et nature_detaillee = Aire de service | `highway` | services | branche 8 — exclusif, première correspondance |
| nature | nature = Aire de repos ou de service | `highway` | rest_area | branche 9 — exclusif, première correspondance |
| nature | nature = Péage | `barrier` | toll_booth | branche 10 — exclusif, première correspondance |
| nature | nature = Gare voyageurs uniquement | `railway` | station | branche 11 — exclusif, première correspondance |
| nature | nature = Gare voyageurs uniquement | `public_transport` | station | branche 11 — exclusif, première correspondance |
| nature | nature = Gare voyageurs uniquement | `train` | yes | branche 11 — exclusif, première correspondance |
| nature | nature = Gare voyageurs et fret | `railway` | station | branche 12 — exclusif, première correspondance |
| nature | nature = Gare voyageurs et fret | `public_transport` | station | branche 12 — exclusif, première correspondance |
| nature | nature = Gare voyageurs et fret | `train` | yes | branche 12 — exclusif, première correspondance |
| nature | nature = Gare fret uniquement | `railway` | station | branche 13 — exclusif, première correspondance |
| nature | nature = Gare fret uniquement | `usage` | freight | branche 13 — exclusif, première correspondance |
| nature | nature = Arrêt voyageurs | `railway` | halt | branche 14 — exclusif, première correspondance |
| nature | nature = Arrêt voyageurs | `public_transport` | station | branche 14 — exclusif, première correspondance |
| nature | nature = Arrêt voyageurs | `train` | yes | branche 14 — exclusif, première correspondance |
| nature | nature = Aire de triage | `landuse` | railway | branche 15 — exclusif, première correspondance |
| nature | nature = Aire de triage | `railway` | yard | branche 15 — exclusif, première correspondance |
| nature | nature = Gare routière | `amenity` | bus_station | branche 16 — exclusif, première correspondance |
| nature | nature = Gare routière | `public_transport` | station | branche 16 — exclusif, première correspondance |
| nature | nature = Aérogare | `aeroway` | terminal | branche 17 — exclusif, première correspondance |
| nature | nature = Tour de contrôle aérien | `aeroway` | control_tower | branche 18 — exclusif, première correspondance |
| — | (sinon) | `fixme` | Nature BD TOPO sans équivalent OSM établi — à qualifier | branche 19 — exclusif, première correspondance |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| fictif | True | `bdtopo:fictif` | yes |  |
| numero | (valeur reprise telle quelle) | `ref` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| adresse_postale |  | (non converti) |  | Adresse en texte libre, qualité inégale ; relève de l'import adresses. |

## terrain_de_sport

Terrains de sport de plein air. `nature` donne le type d'équipement, `nature_detaillee` (42 % rempli) précise la discipline. Mesures sur le département 86, 1 899 terrains.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| etat_de_l_objet | etat_de_l_objet = En ruine | (entité écartée) |  | Terrain hors d'usage (7 entités dans la Vienne). |
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| nature | nature = Bassin de natation | `leisure` | swimming_pool | branche 1 — exclusif, première correspondance |
| nature | nature = Bassin de natation | `sport` | swimming | branche 1 — exclusif, première correspondance |
| nature | nature = Carrière équestre | `leisure` | pitch | branche 2 — exclusif, première correspondance |
| nature | nature = Carrière équestre | `sport` | equestrian | branche 2 — exclusif, première correspondance |
| nature | nature = Terrain de tennis | `leisure` | pitch | branche 3 — exclusif, première correspondance |
| nature | nature = Terrain de tennis | `sport` | tennis | branche 3 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Stade d'athlétisme | `leisure` | track | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Stade d'athlétisme | `sport` | athletics | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste d'hippodrome | `leisure` | track | branche 5 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste d'hippodrome | `sport` | horse_racing | branche 5 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste de vélodrome | `leisure` | track | branche 6 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste de vélodrome | `sport` | cycling | branche 6 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste de sports mécaniques | `leisure` | track | branche 7 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste de sports mécaniques | `sport` | motor | branche 7 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste de cynodrome | `leisure` | track | branche 8 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Piste de sport et nature_detaillee = Piste de cynodrome | `sport` | dog_racing | branche 8 — exclusif, première correspondance |
| nature | nature = Piste de sport | `leisure` | track | branche 9 — exclusif, première correspondance |
| — | (sinon) | `leisure` | pitch | branche 10 — exclusif, première correspondance |
| nature_detaillee | Terrain de football | `sport` | soccer |  |
| nature_detaillee | Terrain de rugby | `sport` | rugby |  |
| nature_detaillee | Terrain de basket-ball | `sport` | basketball |  |
| nature_detaillee | Terrain de handball | `sport` | handball |  |
| nature_detaillee | Terrain de volley-ball | `sport` | volleyball |  |
| nature_detaillee | City-stade | `sport` | multi |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |

## reservoir

Réservoirs et châteaux d'eau, en emprise. 831 entités dans la Vienne.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| nature | nature = Château d'eau | `man_made` | water_tower | branche 1 — exclusif, première correspondance ; motif : Réservoir surélevé : `man_made=water_tower` ; c'est aussi un bâtiment. |
| nature | nature = Château d'eau | `building` | yes | branche 1 — exclusif, première correspondance ; motif : Réservoir surélevé : `man_made=water_tower` ; c'est aussi un bâtiment. |
| nature | nature = Réservoir d'eau ou château d'eau au sol | `man_made` | storage_tank | branche 2 — exclusif, première correspondance |
| nature | nature = Réservoir d'eau ou château d'eau au sol | `content` | water | branche 2 — exclusif, première correspondance |
| nature | nature = Réservoir industriel | `man_made` | storage_tank | branche 3 — exclusif, première correspondance |
| — | (sinon) | `man_made` | storage_tank | branche 4 — exclusif, première correspondance |
| hauteur | (valeur reprise telle quelle) | `height` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| origine_du_batiment | Cadastre | `source:geometry` | cadastre |  |
| origine_du_batiment | Imagerie aérienne | `source:geometry` | aerial_imagery |  |
| origine_du_batiment | Lidar HD | `source:geometry` | lidar |  |
| origine_du_batiment | Autre | `source:geometry` | other |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |
| volume |  | (non converti) |  | Vide dans la Vienne. |
| altitude_minimale_sol |  | (non converti) |  | Altimétrie — la dimension Z est supprimée à la conversion. |
| altitude_minimale_toit |  | (non converti) |  | Idem. |
| altitude_maximale_toit |  | (non converti) |  | Idem ; `height` porte déjà la hauteur. |
| altitude_maximale_sol |  | (non converti) |  | Idem. |

## cimetiere

Cimetières. Une seule nature (« Civil ») dans la Vienne ; 669 emprises.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `landuse` | cemetery |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source | ignoré si valeur ∈ {Civil} |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| etat_de_l_objet |  | (non converti) |  | Toujours « En service » dans la Vienne. |

## parc_ou_reserve

Espaces naturels protégés. 150 dans la Vienne. OSM les modélise en `boundary=protected_area` avec `protect_class` selon le statut juridique.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `boundary` | protected_area |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | nature = Parc naturel régional | `protect_class` | 5 | branche 1 — exclusif, première correspondance |
| nature | nature = Parc naturel régional | `leisure` | nature_reserve | branche 1 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Réserve naturelle et nature_detaillee = Réserve naturelle nationale | `protect_class` | 1 | branche 2 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Réserve naturelle et nature_detaillee = Réserve naturelle nationale | `leisure` | nature_reserve | branche 2 — exclusif, première correspondance |
| nature | nature = Réserve naturelle | `protect_class` | 4 | branche 3 — exclusif, première correspondance |
| nature | nature = Réserve naturelle | `leisure` | nature_reserve | branche 3 — exclusif, première correspondance |
| nature | nature = Arrêté de protection | `protect_class` | 4 | branche 4 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Site Natura 2000 et nature_detaillee = Site inscrit au titre de la Directive Habitats | `protect_class` | 97 | branche 5 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Site Natura 2000 et nature_detaillee = Site inscrit au titre de la Directive Habitats | `protection_title` | Natura 2000 (Habitats) | branche 5 — exclusif, première correspondance |
| nature | nature = Site Natura 2000 | `protect_class` | 97 | branche 6 — exclusif, première correspondance |
| nature | nature = Site Natura 2000 | `protection_title` | Natura 2000 (Oiseaux) | branche 6 — exclusif, première correspondance |
| nature | nature = Site Ramsar | `protect_class` | 98 | branche 7 — exclusif, première correspondance |
| nature | nature = Site Ramsar | `protection_title` | Ramsar | branche 7 — exclusif, première correspondance |
| nature | nature = Site acquis ou assimilé des conservatoires d'espaces naturels | `protect_class` | 7 | branche 8 — exclusif, première correspondance |
| nature | nature = Site acquis ou assimilé des conservatoires d'espaces naturels | `operator` | Conservatoire d'espaces naturels | branche 8 — exclusif, première correspondance |
| — | (sinon) | `protect_class` | 7 | branche 9 — exclusif, première correspondance |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| fictif | True | `bdtopo:fictif` | yes |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |

## construction_surfacique

Ouvrages surfaciques : emprises de ponts et écluses. 136 entités dans la Vienne.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature, nature_detaillee | nature = Pont et nature_detaillee = Viaduc | `man_made` | bridge | branche 1 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Pont et nature_detaillee = Viaduc | `bridge:structure` | viaduct | branche 1 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Pont et nature_detaillee = Viaduc | `layer` | 1 | branche 1 — exclusif, première correspondance |
| nature | nature = Pont | `man_made` | bridge | branche 2 — exclusif, première correspondance |
| nature | nature = Pont | `layer` | 1 | branche 2 — exclusif, première correspondance |
| nature | nature = Ecluse | `waterway` | lock | branche 3 — exclusif, première correspondance |
| — | (sinon) | `fixme` | Nature BD TOPO sans équivalent OSM établi — à qualifier | branche 4 — exclusif, première correspondance |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |

## poste_de_transformation

Postes électriques (emprises), 67 dans la Vienne.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `power` | substation |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |

## piste_d_aerodrome

Pistes d'aérodrome, 30 dans la Vienne.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `aeroway` | runway |  |
| nature | Piste en herbe | `surface` | grass |  |
| nature | Piste en dur | `surface` | paved |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| fonction |  | (non converti) |  | Vide dans la Vienne. |
| etat_de_l_objet |  | (non converti) |  | Toujours « En service » dans la Vienne. |

## aerodrome

Aérodromes et héliports, en emprise. 21 dans la Vienne, dont l'aéroport de Poitiers-Biard.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | Aérodrome | `aeroway` | aerodrome |  |
| nature | Héliport | `aeroway` | heliport |  |
| categorie | Internationale | `aerodrome:type` | international |  |
| categorie | Nationale | `aerodrome:type` | regional |  |
| usage | Privé | `access` | private |  |
| code_icao | (valeur reprise telle quelle) | `icao` | = valeur source |  |
| code_iata | (valeur reprise telle quelle) | `iata` | = valeur source |  |
| altitude | (valeur reprise telle quelle) | `ele` | = valeur source | arrondi à 0 décimale(s) |
| fictif | True | `bdtopo:fictif` | yes |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| etat_de_l_objet |  | (non converti) |  | Toujours « En service » dans la Vienne. |

## commune

Communes → relations `type=boundary` + `boundary=administrative` + `admin_level=8`. Chaque commune garde son propre contour (polygone simple) : les limites communes à deux voisines ne sont pas mutualisées, contrairement à la pratique OSM, mais l'identité `cleabs` reste entière et la géométrie est celle de la BD TOPO. 34 877 communes en France, 13 intersectant Poitiers.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `boundary` | administrative |  |
| — | (toujours) | `admin_level` | 8 |  |
| nom_officiel | (valeur reprise telle quelle) | `name` | = valeur source |  |
| code_insee | (valeur reprise telle quelle) | `ref:INSEE` | = valeur source |  |
| code_siren | (valeur reprise telle quelle) | `ref:FR:SIREN` | = valeur source |  |
| code_postal | (valeur reprise telle quelle) | `postal_code` | = valeur source |  |
| population | (valeur reprise telle quelle) | `population` | = valeur source | motif : Population légale publiée par l'INSEE et reprise par la BD TOPO ; OSM attend l'année du recensement (`population:date`) et l'organisme (`source:population`) pour qu'elle soit interprétable. ; si population > 0 |
| date_du_recensement | (valeur reprise telle quelle) | `population:date` | = valeur source | motif : Population légale publiée par l'INSEE et reprise par la BD TOPO ; OSM attend l'année du recensement (`population:date`) et l'organisme (`source:population`) pour qu'elle soit interprétable. ; si population > 0 |
| organisme_recenseur | (valeur reprise telle quelle) | `source:population` | = valeur source | motif : Population légale publiée par l'INSEE et reprise par la BD TOPO ; OSM attend l'année du recensement (`population:date`) et l'organisme (`source:population`) pour qu'elle soit interprétable. ; si population > 0 |
| chef_lieu_d_arrondissement | (valeur reprise telle quelle) | `bdtopo:chef_lieu_d_arrondissement` | = valeur source | ignoré si valeur ∈ {False} |
| chef_lieu_de_departement | (valeur reprise telle quelle) | `bdtopo:chef_lieu_de_departement` | = valeur source | ignoré si valeur ∈ {False} |
| chef_lieu_de_region | (valeur reprise telle quelle) | `bdtopo:chef_lieu_de_region` | = valeur source | ignoré si valeur ∈ {False} |
| chef_lieu_de_collectivite_terr | (valeur reprise telle quelle) | `bdtopo:chef_lieu_de_collectivite_terr` | = valeur source | ignoré si valeur ∈ {False} |
| capitale_d_etat | (valeur reprise telle quelle) | `bdtopo:capitale_d_etat` | = valeur source | ignoré si valeur ∈ {False} |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| code_insee_du_canton |  | (non converti) |  | Rattachement hiérarchique, porté par la géométrie (le canton est converti). |
| code_insee_de_l_arrondissement |  | (non converti) |  | Idem (l'arrondissement est converti). |
| code_insee_de_la_collectivite_terr |  | (non converti) |  | Idem. |
| code_insee_du_departement |  | (non converti) |  | Idem (le département est converti). |
| code_insee_de_la_region |  | (non converti) |  | Idem. |
| codes_siren_des_epci |  | (non converti) |  | Idem (l'EPCI est converti, avec son SIREN). |
| superficie_cadastrale |  | (non converti) |  | Surface en hectares ; OSM ne stocke pas une surface calculable. |
| lien_vers_chef_lieu |  | (non converti) |  | Lien interne vers la zone d'habitation chef-lieu. |
| liens_vers_autorite_administrative |  | (non converti) |  | Lien interne vers la mairie (zone_d_activite_ou_d_interet). |

## canton

Cantons → relations `type=boundary` + `boundary=political` + `political_division=canton`. Circonscriptions électorales départementales, pas des collectivités : OSM les range sous `political`, pas `administrative`. 2 054 en France, 8 intersectant Poitiers.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `boundary` | political |  |
| — | (toujours) | `political_division` | canton |  |
| nom_officiel | (valeur reprise telle quelle) | `name` | = valeur source |  |
| code_insee | (valeur reprise telle quelle) | `ref:INSEE` | = valeur source |  |
| composition_du_canton | (valeur reprise telle quelle) | `bdtopo:composition_du_canton` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| numero_du_canton |  | (non converti) |  | Deux derniers chiffres de `code_insee`, redondant. |
| code_insee_du_departement |  | (non converti) |  | Rattachement hiérarchique, porté par la géométrie. |
| code_insee_de_la_region |  | (non converti) |  | Idem. |
| codes_insee_des_arrondissements |  | (non converti) |  | Idem. |

## arrondissement

Arrondissements départementaux → relations `type=boundary` + `boundary=administrative` + `admin_level=7`. 332 en France.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `boundary` | administrative |  |
| — | (toujours) | `admin_level` | 7 |  |
| nom_officiel | (valeur reprise telle quelle) | `name` | = valeur source |  |
| code_insee_de_l_arrondissement | (valeur reprise telle quelle) | `ref:INSEE` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| numero_de_l_arrondissement |  | (non converti) |  | Dernier chiffre de `code_insee_de_l_arrondissement`, redondant. |
| code_insee_du_departement |  | (non converti) |  | Rattachement hiérarchique, porté par la géométrie. |
| code_insee_de_la_region |  | (non converti) |  | Idem. |
| liens_vers_autorite_administrative |  | (non converti) |  | Lien interne vers la sous-préfecture (zone_d_activite_ou_d_interet). |

## epci

Intercommunalités → relations `type=boundary` + `boundary=local_authority`, la nature juridique dans `local_authority:FR` (convention OSM France). 1 265 EPCI à fiscalité propre en France.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `boundary` | local_authority |  |
| nom_officiel | (valeur reprise telle quelle) | `name` | = valeur source |  |
| code_siren | (valeur reprise telle quelle) | `ref:FR:SIREN` | = valeur source |  |
| nature | Communauté de communes | `local_authority:FR` | CC |  |
| nature | Communauté d'agglomération | `local_authority:FR` | CA |  |
| nature | Communauté urbaine | `local_authority:FR` | CU |  |
| nature | Métropole | `local_authority:FR` | metropole |  |
| nature | Etablissement public territorial | `local_authority:FR` | EPT |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| codes_insee_des_communes_membres |  | (non converti) |  | Composition, portée par la géométrie (les communes sont converties). |
| codes_insee_des_departements_membres |  | (non converti) |  | Idem. |
| liens_vers_autorite_administrative |  | (non converti) |  | Lien interne vers le siège (zone_d_activite_ou_d_interet). |

## departement

Départements → relations `type=boundary` + `boundary=administrative` + `admin_level=6`. 101 en France.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `boundary` | administrative |  |
| — | (toujours) | `admin_level` | 6 |  |
| nom_officiel | (valeur reprise telle quelle) | `name` | = valeur source |  |
| code_insee | (valeur reprise telle quelle) | `ref:INSEE` | = valeur source |  |
| code_siren | (valeur reprise telle quelle) | `ref:FR:SIREN` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| code_insee_de_la_region |  | (non converti) |  | Rattachement hiérarchique, porté par la géométrie. |
| liens_vers_autorite_administrative |  | (non converti) |  | Lien interne vers la préfecture (zone_d_activite_ou_d_interet). |

## lieu_dit_non_habite

Toponymes de lieux non habités, en points. Mesures sur le département 86, 14 696 points — dont 3 109 bois nommés.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | nature = Arbre | `natural` | tree | branche 1 — exclusif, première correspondance |
| — | (sinon) | `place` | locality | branche 2 — exclusif, première correspondance ; motif : Un bois nommé reste un toponyme : son emprise, quand elle existe, est portée par `zone_de_vegetation`. `natural=wood` sur un point dupliquerait l'information. |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source | ignoré si valeur ∈ {Lieu-dit non habité} |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique. Sans équivalent pour un `place=locality`, qui n'a pas de gradation dans OSM. |

## construction_ponctuelle

Constructions ponctuelles remarquables : croix, antennes, clochers, éoliennes. Mesures sur le département 86, 4 161 points.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | nature = Croix | `historic` | wayside_cross | branche 1 — exclusif, première correspondance |
| nature | nature = Calvaire | `historic` | wayside_cross | branche 2 — exclusif, première correspondance |
| nature | nature = Calvaire | `wayside_cross` | calvary | branche 2 — exclusif, première correspondance |
| nature | nature = Antenne | `man_made` | mast | branche 3 — exclusif, première correspondance |
| nature | nature = Antenne | `tower:type` | communication | branche 3 — exclusif, première correspondance |
| nature | nature = Eolienne | `power` | generator | branche 4 — exclusif, première correspondance |
| nature | nature = Eolienne | `generator:source` | wind | branche 4 — exclusif, première correspondance |
| nature | nature = Eolienne | `generator:method` | wind_turbine | branche 4 — exclusif, première correspondance |
| nature | nature = Clocher | `man_made` | tower | branche 5 — exclusif, première correspondance |
| nature | nature = Clocher | `tower:type` | bell_tower | branche 5 — exclusif, première correspondance |
| nature | nature = Minaret | `man_made` | tower | branche 6 — exclusif, première correspondance |
| nature | nature = Minaret | `tower:type` | minaret | branche 6 — exclusif, première correspondance |
| nature | nature = Cheminée | `man_made` | chimney | branche 7 — exclusif, première correspondance |
| nature | nature = Transformateur | `power` | transformer | branche 8 — exclusif, première correspondance |
| nature | nature = Autre construction élevée | `man_made` | tower | branche 9 — exclusif, première correspondance |
| — | (sinon) | `fixme` | Nature BD TOPO sans équivalent OSM établi — à qualifier | branche 10 — exclusif, première correspondance |
| hauteur | (valeur reprise telle quelle) | `height` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |

## pylone

Pylônes des lignes haute tension, 3 994 dans la Vienne. Un pylône est un sommet de la ligne qu'il porte : `point_mode: shared` réutilise le nœud de `ligne_electrique` à la même coordonnée, ce qui fait du pylône un vrai nœud de la ligne dans le modèle OSM (`power=tower` sur un nœud de `power=line`).

Couche ponctuelle en `point_mode: shared` : le nœud est mutualisé avec les sommets existants.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| — | (toujours) | `power` | tower |  |
| numero | (valeur reprise telle quelle) | `ref` | = valeur source |  |
| hauteur | (valeur reprise telle quelle) | `height` | = valeur source | arrondi à 1 décimale(s) ; ignoré si valeur ∈ {0} |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |

## detail_hydrographique

Points d'eau remarquables : sources, fontaines, lavoirs, citernes. Mesures sur le département 86, 2 906 points.

| Champ BD Topo | Valeur / condition | Tag OSM | Valeur OSM | Remarque |
|---|---|---|---|---|
| — | (toujours) | `source` | IGN BD TOPO® 3.5 |  |
| cleabs | (valeur reprise telle quelle) | `ref:FR:IGN:cleabs` | {cleabs} |  |
| toponyme | (valeur reprise telle quelle) | `name` | = valeur source |  |
| nature | nature ∈ {Source, Source captée, Résurgence} | `natural` | spring | branche 1 — exclusif, première correspondance |
| nature | nature = Fontaine | `amenity` | fountain | branche 2 — exclusif, première correspondance |
| nature | nature = Lavoir | `amenity` | washing_place | branche 3 — exclusif, première correspondance |
| nature | nature = Lavoir | `historic` | wash_house | branche 3 — exclusif, première correspondance |
| nature, nature_detaillee | nature = Point d'eau et nature_detaillee = Puits | `man_made` | water_well | branche 4 — exclusif, première correspondance |
| nature | nature = Citerne | `emergency` | water_tank | branche 5 — exclusif, première correspondance |
| nature_detaillee | nature_detaillee = DFCI | `emergency` | fire_water_pond | branche 6 — exclusif, première correspondance |
| nature | nature = Point d'eau | `natural` | water | branche 7 — exclusif, première correspondance |
| nature | nature = Point d'eau | `water` | pond | branche 7 — exclusif, première correspondance |
| nature | nature = Cascade | `waterway` | waterfall | branche 8 — exclusif, première correspondance |
| nature | nature = Marais | `natural` | wetland | branche 9 — exclusif, première correspondance |
| nature | nature = Marais | `wetland` | marsh | branche 9 — exclusif, première correspondance |
| nature | nature = Perte | `natural` | sinkhole | branche 10 — exclusif, première correspondance |
| nature | nature = Perte | `sinkhole` | ponor | branche 10 — exclusif, première correspondance |
| — | (sinon) | `fixme` | Nature BD TOPO sans équivalent OSM établi — à qualifier | branche 11 — exclusif, première correspondance |
| persistance | Intermittent | `intermittent` | yes |  |
| nature | (valeur reprise telle quelle) | `bdtopo:nature` | = valeur source |  |
| nature_detaillee | (valeur reprise telle quelle) | `bdtopo:nature_detaillee` | = valeur source |  |
| date_creation |  | (non converti) |  | Métadonnée de production IGN, sans équivalent OSM. ; métadonnée commune |
| date_modification |  | (non converti) |  | Idem. ; métadonnée commune |
| date_d_apparition |  | (non converti) |  | Idem. ; métadonnée commune |
| date_de_confirmation |  | (non converti) |  | Idem. ; métadonnée commune |
| sources |  | (non converti) |  | Provenance interne IGN ; le tag `source` porte déjà l'attribution. ; métadonnée commune |
| identifiants_sources |  | (non converti) |  | Identifiants du producteur amont. ; métadonnée commune |
| methode_d_acquisition_planimetrique |  | (non converti) |  | Qualité de saisie, hors modèle OSM. ; métadonnée commune |
| methode_d_acquisition_altimetrique |  | (non converti) |  | Idem, et l'altimétrie est écartée (Z supprimé). ; métadonnée commune |
| precision_planimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| precision_altimetrique |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_des_coordonnees |  | (non converti) |  | Idem. ; métadonnée commune |
| mode_d_obtention_de_l_altitude |  | (non converti) |  | Idem. ; métadonnée commune |
| statut |  | (non converti) |  | État de validation interne ; toujours « Validé » en diffusion. ; métadonnée commune |
| statut_du_toponyme |  | (non converti) |  | Qualité du toponyme (Validé / Collecté), métadonnée de saisie. ; métadonnée commune |
| code_du_pays |  | (non converti) |  | Toujours « FR » sur le territoire traité. ; métadonnée commune |
| insee_commune |  | (non converti) |  | Rattachement administratif, déductible de la géométrie. ; métadonnée commune |
| commune |  | (non converti) |  | Idem, et redondant avec `insee_commune`. ; métadonnée commune |
| identifiant_voie_ban |  | (non converti) |  | Candidat `ref:FR:BAN` — à arbitrer avec l'import adresses. ; métadonnée commune |
| id_ban_odonyme |  | (non converti) |  | Idem. ; métadonnée commune |
| importance |  | (non converti) |  | Hiérarchie d'affichage cartographique, sans équivalent OSM. |
| etat_de_l_objet |  | (non converti) |  | Non discriminant sur cette couche. |
