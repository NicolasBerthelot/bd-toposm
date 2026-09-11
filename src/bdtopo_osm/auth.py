"""OAuth2 PKCE — façade locale, pas un mécanisme d'authentification.

iD ne sait se connecter à une API 0.6 qu'à travers OAuth2 avec PKCE. Cette
instance n'a pas de comptes : il faut donc lui présenter la forme du protocole
sans la substance.

**Ce module n'authentifie personne.** Tous les jetons désignent le même
utilisateur synthétique. Sans mot de passe de démo, `/oauth2/authorize` délivre
un code à quiconque le demande : acceptable sur 127.0.0.1, pas une seconde sur
un réseau ouvert — d'où le refus du CLI.

Avec `BDTOPO_DEMO_PASSWORD`, la fenêtre de connexion qu'iD ouvre affiche un
formulaire (`LOGIN_PAGE`) et le code n'est délivré qu'après un mot de passe
correct. C'est une barrière de démonstration — un secret partagé, comparé en
temps constant, avec une temporisation sur échec — pas un système de comptes.

La vérification PKCE, elle, est faite pour de bon : elle ne protège rien ici
(l'attaquant pourrait simplement démarrer son propre échange) mais elle garantit
que `authorize` et `token` restent cohérents, et fait échouer bruyamment un
client qui s'écarterait du protocole.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field

CODE_TTL_SECONDS = 300

# Utilisateur unique auquel tout jeton renvoie. `id` sert de `uid` dans les
# changesets, `display_name` s'affiche dans le bandeau d'iD.
SYNTHETIC_USER = {
    "id": 1,
    "display_name": "bdtopo",
    "account_created": "2026-01-01T00:00:00Z",
    "description": "Utilisateur unique de l'instance locale BD TOPO",
    "contributor_terms": {"agreed": True, "pd": False},
    "roles": [],
    "changesets": {"count": 0},
    "traces": {"count": 0},
    "blocks": {"received": {"count": 0, "active": 0}},
    "languages": ["fr"],
    "messages": {"received": {"count": 0, "unread": 0}, "sent": {"count": 0}},
}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@dataclass
class _PendingCode:
    challenge: str | None
    method: str
    redirect_uri: str
    issued_at: float


@dataclass
class AuthStore:
    """Codes et jetons en mémoire : ils ne survivent pas au redémarrage.

    C'est volontaire — rien ici ne mérite d'être persisté, et un jeton qui
    traîne dans un fichier est une mauvaise habitude à ne pas prendre.
    """

    codes: dict[str, _PendingCode] = field(default_factory=dict)
    tokens: set[str] = field(default_factory=set)

    def issue_code(
        self, redirect_uri: str, challenge: str | None, method: str | None
    ) -> str:
        self._purge()
        code = secrets.token_urlsafe(24)
        self.codes[code] = _PendingCode(
            challenge=challenge,
            method=(method or "plain").upper(),
            redirect_uri=redirect_uri,
            issued_at=time.time(),
        )
        return code

    def exchange(self, code: str, verifier: str | None) -> str:
        self._purge()
        pending = self.codes.pop(code, None)
        if pending is None:
            raise ValueError("code d'autorisation inconnu ou expiré")
        self._verify_pkce(pending, verifier)
        token = secrets.token_urlsafe(32)
        self.tokens.add(token)
        return token

    def _verify_pkce(self, pending: _PendingCode, verifier: str | None) -> None:
        if pending.challenge is None:
            return  # aucun challenge présenté : rien à vérifier
        if not verifier:
            raise ValueError("code_verifier manquant")
        if pending.method == "S256":
            digest = hashlib.sha256(verifier.encode("ascii")).digest()
            computed = _b64url(digest)
        else:
            computed = verifier
        if not secrets.compare_digest(computed, pending.challenge):
            raise ValueError("code_verifier ne correspond pas au code_challenge")

    def validate(self, token: str | None) -> bool:
        return bool(token) and token in self.tokens

    def revoke(self, token: str) -> None:
        self.tokens.discard(token)

    def _purge(self) -> None:
        limit = time.time() - CODE_TTL_SECONDS
        for code in [c for c, p in self.codes.items() if p.issued_at < limit]:
            del self.codes[code]


def password_matches(candidate: str | None, expected: str | None) -> bool:
    """Comparaison en temps constant, pour ne pas laisser fuir la longueur."""
    if not expected or candidate is None:
        return False
    return secrets.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Connexion — démo BD TOPO</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font: 15px/1.5 system-ui, sans-serif; margin: 0; background: #f6f6f6; color: #1b1b1b; }}
  main {{ max-width: 380px; margin: 12vh auto; background: #fff; padding: 28px 32px;
          border-top: 4px solid #000091; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  h1 {{ font-size: 18px; margin: 0 0 4px; }}
  p {{ margin: 6px 0 16px; color: #3a3a3a; }}
  label {{ display: block; font-weight: 600; margin-bottom: 6px; }}
  input[type=password] {{ width: 100%; box-sizing: border-box; font: inherit; padding: 8px 10px;
          border: 1px solid #929292; border-radius: 3px; }}
  button {{ margin-top: 16px; width: 100%; font: inherit; font-weight: 600; padding: 10px;
          background: #000091; color: #fff; border: 0; border-radius: 3px; cursor: pointer; }}
  .err {{ color: #ce0500; font-weight: 600; margin: 8px 0 0; }}
  .note {{ font-size: 12px; color: #666; margin-top: 18px; }}
</style></head><body><main>
  <h1>Démonstration BD TOPO® → OpenStreetMap</h1>
  <p>Instance locale hors OpenStreetMap. L'édition est ouverte aux personnes disposant du mot de passe de démonstration.</p>
  <form method="post">
    {hidden}
    <label for="pw">Mot de passe</label>
    <input id="pw" name="password" type="password" autocomplete="current-password" autofocus required>
    {error}
    <button type="submit">Se connecter</button>
  </form>
  <p class="note">Aucun compte n'est créé : tous les contributeurs partagent le même utilisateur « bdtopo ».
  {ephemeral}</p>
</main></body></html>"""


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None
