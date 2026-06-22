# Appli QL-570

Application pour piloter l'imprimante d'étiquettes **Brother QL-570** depuis un poste Debian, utilisable sans compétence technique. Développée pour le FabLab **Les Portes Logiques** (Quimper).

> **Statut : en construction.** La conception (algorithmes en français) est figée pour le module cœur ; le code et l'installeur sont en cours.

## Ce que fait l'appli

- Détecte automatiquement l'imprimante branchée (port et modèle) — rien n'est codé en dur.
- Imprime une étiquette à partir d'une **image PNG** préparée par l'utilisateur dans GIMP.
- Signale, au branchement, qu'une QL-570 est disponible (agent en fond).

L'image elle-même se fabrique dans **GIMP** (voir `docs/prise-en-main-gimp.md`) : l'appli ne crée pas l'image, elle l'imprime.

## Architecture (résumé)

Trois piliers, détaillés dans `docs/algorithme-appli-QL570.md` :

- **Module cœur** — le moteur (détection, accès, impression), testable en ligne de commande.
- **Transversaux** — catalogue d'erreurs et journalisation (un log par poste).
- **Deux programmes** — l'application d'impression (fenêtre) et l'agent de détection (pop-up), qui partagent le cœur sans communiquer entre eux.

## Documentation

- `docs/notes-techniques-QL570.md` — le contexte matériel vérifié.
- `docs/algorithme-appli-QL570.md` — l'organisation et les algorithmes.
- `docs/prise-en-main-gimp.md` — comment fabriquer l'image de l'étiquette.
- Le **récit de construction** est tenu sur le wiki des Portes Logiques (le dépôt reste la source de vérité technique).

## Dépendances

- `python3-tk` (apt)
- `brother_ql`, `pyudev` (pip, dans un environnement virtuel)
- Accès au périphérique : appartenance au groupe `lp` (posée à l'installation)

## Installation *(à venir)*

L'installation se fera via `install.sh` (à lancer en root) :

- pose l'appli dans **`/opt/ql570/`** (même emplacement sur chaque poste) ;
- installe les dépendances dans un environnement virtuel ;
- pose la règle udev (`/etc/udev/rules.d/`) et l'autostart de l'agent (`/etc/xdg/autostart/`) ;
- ajoute le compte au groupe `lp`.

Un `uninstall.sh` défera proprement l'installation (sans toucher au groupe `lp`, partagé avec d'autres usages).

## Licences

- **Code** : GNU Affero General Public License v3 (AGPL-3.0) — voir `LICENSE`.
- **Documentation** (ce dépôt + wiki) : Creative Commons Attribution (CC BY).

## Auteurice

Conçue et développée par **Vitally LUBIN** en 2026.

## Liens

- FabLab Les Portes Logiques : <https://lesporteslogiques.net>
