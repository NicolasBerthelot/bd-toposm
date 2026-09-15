/* BD France Édition — modules thématiques.
 *
 * Un module est un sous-ensemble de couches BD TOPO. L'activer ne montre que
 * les objets issus de ces couches : la carte s'allège, et l'on peut concevoir
 * pour chaque module ses propres outils sans les imposer aux autres.
 *
 * Mécanique : iD masque un objet quand TOUTES les règles de filtrage qu'il
 * satisfait sont désactivées (`context.features()`). On enregistre une règle
 * par module, qui reconnaît la couche d'origine au préfixe du
 * `ref:FR:IGN:cleabs` (les ways membres d'une relation héritent des règles de
 * leur relation). Activer un module = désactiver toutes les règles d'iD,
 * n'activer que celle du module. Les objets créés par l'utilisateur, sans
 * version ni cleabs, ne sont jamais masqués par iD : ils restent visibles.
 *
 * Le serveur filtre aussi : le module pose un cookie `bdf_layers` que l'API
 * lit sur `/api/0.6/map.json` (cf. api.py) et ne renvoie que les couches du
 * module. Les tuiles sont donc légères, ce qui permet à certains modules de
 * charger la donnée à un zoom plus faible (`minZoom`, `tileZoom`) — une
 * commune entière à l'écran pour les limites administratives.
 *
 * L'état est porté par le paramètre `module=` de l'URL (partageable) et
 * mémorisé dans le navigateur.
 */
(function (global) {
  'use strict';

  var MODULES = [
    { id: 'general', label: 'Vue générale', tout: true,
      description: 'Toutes les couches converties.' },
    { id: 'voirie', label: 'Réseau routier',
      couches: ['troncon_de_route'],
      description: 'Tronçons de route seuls : classification, sens, noms, limitations.' },
    { id: 'bati', label: 'Bâti',
      couches: ['batiment', 'construction_surfacique', 'construction_lineaire',
                'construction_ponctuelle', 'reservoir'],
      description: 'Bâtiments et constructions, avec leurs matériaux et hauteurs.' },
    { id: 'hydro', label: 'Hydrographie',
      couches: ['troncon_hydrographique', 'surface_hydrographique', 'detail_hydrographique'],
      description: 'Cours d’eau, plans d’eau et détails hydrographiques.' },
    { id: 'admin', label: 'Limites administratives',
      couches: ['commune', 'canton', 'arrondissement', 'epci', 'departement'],
      // Peu d'objets, très étendus : on charge dès le zoom 14 (une commune
      // entière à l'écran), par tuiles de zoom 15 pour limiter les requêtes.
      minZoom: 14, tileZoom: 15,
      description: 'Communes, cantons, arrondissement, intercommunalité et département.' },
    { id: 'transport', label: 'Transports',
      couches: ['troncon_de_voie_ferree', 'equipement_de_transport', 'aerodrome', 'piste_d_aerodrome'],
      description: 'Voies ferrées, équipements de transport, aérodromes.' },
    { id: 'energie', label: 'Énergie',
      couches: ['ligne_electrique', 'pylone', 'poste_de_transformation'],
      description: 'Réseau électrique : lignes, pylônes, postes.' },
    { id: 'territoire', label: 'Occupation du sol',
      couches: ['zone_de_vegetation', 'zone_d_habitation', 'lieu_dit_non_habite',
                'zone_d_activite_ou_d_interet', 'terrain_de_sport', 'cimetiere', 'parc_ou_reserve'],
      description: 'Végétation, lieux habités ou non, zones d’activité, terrains de sport, cimetières, espaces protégés.' }
  ];

  var STOCKAGE = 'bdf-module';
  var CLE_REGLE = 'module_';
  var COOKIE = 'bdf_layers';               // lu par l'API, cf. api.py
  var ZOOM_EDITION = 16;                   // valeurs par défaut d'iD
  var ZOOM_TUILES = 16;

  var context, prefixes, actif = null, liste, badge;

  function couche(tags) {
    var cleabs = tags['ref:FR:IGN:cleabs'];
    return cleabs ? prefixes[cleabs.slice(0, 8)] : undefined;
  }

  // Une règle de filtrage iD par module, ajoutée à la suite des règles natives.
  // `features.features()` et `features.keys()` renvoient les structures
  // internes : les enrichir suffit, iD les parcourt à chaque calcul.
  function enregistrerRegles() {
    var features = context.features();
    var rules = features.features();
    var keys = features.keys();
    MODULES.forEach(function (m) {
      if (m.tout) return;
      var couches = {};
      m.couches.forEach(function (c) { couches[c] = true; });
      var key = CLE_REGLE + m.id;
      if (rules[key]) return;
      keys.push(key);
      rules[key] = {
        filter: function (tags) { return !!couches[couche(tags)]; },
        enabled: true,
        count: 0,
        currentMax: Infinity,
        defaultMax: Infinity,
        enable: function () { this.enabled = true; this.currentMax = this.defaultMax; },
        disable: function () { this.enabled = false; this.currentMax = 0; },
        hidden: function () { return this.count === 0 && !this.enabled || this.count > this.currentMax; },
        autoHidden: function () { return this.hidden() && this.currentMax > 0; }
      };
    });
  }

  function parId(id) {
    for (var i = 0; i < MODULES.length; i++) if (MODULES[i].id === id) return MODULES[i];
    return null;
  }

  function lireHash() {
    var q = iD.utilStringQs(window.location.hash);
    return q.module || null;
  }

  function ecrireHash(id) {
    var valeur = id === 'general' ? null : id;
    if (iD.patchHash) { iD.patchHash({ module: valeur }); return; }
    var q = iD.utilStringQs(window.location.hash);
    if (valeur) q.module = valeur; else delete q.module;
    window.history.replaceState(null, '', '#' + iD.utilQsString(q, true));
  }

  function memoriser(id) {
    try { window.localStorage.setItem(STOCKAGE, id); } catch (e) { /* navigation privée */ }
  }
  function memorise() {
    try { return window.localStorage.getItem(STOCKAGE); } catch (e) { return null; }
  }

  // Couches demandées au serveur. Le cookie est posé avant tout rechargement
  // de tuiles ; en vue générale il est effacé et l'API renvoie tout.
  function poserCookie(m) {
    var valeur = m.tout ? '' : m.couches.join(',');
    document.cookie = COOKIE + '=' + encodeURIComponent(valeur) + '; path=/; SameSite=Lax'
      + (valeur ? '' : '; max-age=0');
  }

  function activer(id, options) {
    var m = parId(id) || MODULES[0];
    var features = context.features();
    var changement = !actif || actif.id !== m.id;
    if (m.tout) {
      // On ne touche aux cases d'iD que si l'on SORT d'un module : en vue
      // générale, les choix de l'utilisateur dans « Données de carte » restent
      // les siens.
      if (!options || !options.conserver) features.enableAll();
    } else {
      features.disableAll();
      features.enable(CLE_REGLE + m.id);
    }
    poserCookie(m);
    // `minEditableZoom` aligne aussi le zoom des tuiles sur sa valeur : on
    // repose le nôtre après.
    context.minEditableZoom(m.minZoom || ZOOM_EDITION);
    var connexion = context.connection();
    if (connexion && connexion.tileZoom) connexion.tileZoom(m.tileZoom || ZOOM_TUILES);
    if (changement && connexion) {
      // Oublier les tuiles déjà chargées (pas les modifications en cours :
      // l'historique d'édition n'est pas touché) et recharger la vue avec le
      // nouveau filtre. Les objets déjà en mémoire restent masqués côté client.
      connexion.reset();
      context.loadTiles(context.projection);
    }
    actif = m;
    ecrireHash(m.id);
    memoriser(m.id);
    rafraichir();
  }

  function rafraichir() {
    if (liste) {
      liste.querySelectorAll('a').forEach(function (a) {
        var courant = a.dataset.module === actif.id;
        if (courant) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
      });
    }
    document.body.classList.toggle('bdf-module-actif', !actif.tout);
    document.body.style.setProperty('--bdf-module-note',
      JSON.stringify(actif.tout ? '' : 'Filtrage piloté par le module « ' + actif.label + ' ». Revenez à la vue générale pour choisir couche par couche.'));
    compter();
  }

  // Nombre d'objets du module dans la vue courante, d'après les statistiques
  // qu'iD calcule à chaque redessin (`features.gatherStats`).
  function compter() {
    if (!badge) return;
    if (actif.tout) { badge.textContent = ''; badge.hidden = true; return; }
    var n = context.features().stats()[CLE_REGLE + actif.id] || 0;
    badge.hidden = false;
    badge.textContent = n ? n.toLocaleString('fr-FR') + (n > 1 ? ' objets à l’écran' : ' objet à l’écran') : 'aucun objet à l’écran';
  }

  // ------------------------------------------------------------------ DOM

  function construire(conteneur) {
    liste = conteneur.querySelector('.fr-nav__list');
    MODULES.forEach(function (m) {
      var li = document.createElement('li');
      li.className = 'fr-nav__item';
      var a = document.createElement('a');
      a.className = 'fr-nav__link';
      a.href = '#';
      a.dataset.module = m.id;
      a.title = m.description;
      a.textContent = m.label;
      a.addEventListener('click', function (e) {
        e.preventDefault();
        activer(m.id);
      });
      li.appendChild(a);
      liste.appendChild(li);
    });

    badge = conteneur.querySelector('.bdf-module-compte');
  }

  // ------------------------------------------------------------ démarrage

  function init(ctx, docsPrefixes, conteneur) {
    context = ctx;
    prefixes = docsPrefixes || {};
    enregistrerRegles();
    construire(conteneur);
    context.map().on('drawn.bdf-modules', compter);
    // Un lien vers un autre module (même page, autre `#module=`) doit agir
    // comme un clic dans la barre.
    window.addEventListener('hashchange', function () {
      var id = lireHash() || 'general';
      if (!actif || id !== actif.id) activer(id);
    });

    var demande = lireHash() || 'general';
    var precedent = memorise();
    // Sans module dans l'URL et sans module mémorisé, iD garde ses propres
    // réglages ; si l'on revient d'un module, on rétablit tout.
    activer(demande, { conserver: demande === 'general' && (!precedent || precedent === 'general') });
  }

  global.bdfModules = { init: init, activer: activer, MODULES: MODULES };
})(window);
