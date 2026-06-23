# Stickeuse QL-570

Application pour piloter l'imprimante d'étiquettes **Brother QL-570** depuis un poste Debian, utilisable sans compétence technique. Développée pour le FabLab **Les Portes Logiques** (Quimper).

> **Statut : fonctionnelle, en cours de déploiement.** Le module cœur, la journalisation et les deux programmes (impression + agent) sont codés et testés sur matériel. Les scripts `install.sh` / `uninstall.sh` sont écrits et restent à éprouver lors d'un premier déploiement complet.

## Ce que fait l'appli

- Détecte automatiquement l'imprimante branchée (port et modèle) — rien n'est codé en dur.
- Imprime une étiquette à partir d'une **image PNG** préparée par l'utilisateur dans GIMP.
- Signale, au branchement, qu'une QL-570 est disponible (agent en fond, notification de bureau).

L'image elle-même se fabrique dans **GIMP** (voir <:docs/prise-en-main-gimp.md>) : l'appli ne crée pas l'image, elle l'imprime.

## Architecture (résumé)

Trois piliers, détaillés dans `docs/algorithme-appli-QL570.md` :

- **Module cœur** (`src/coeur.py`) — le moteur (détection, accès, impression), testable en ligne de commande.
- **Transversaux** — catalogue d'erreurs et journalisation (`src/journal.py`, un log par poste).
- **Deux programmes** — l'application d'impression (`src/programme_a.py`, fenêtre) et l'agent de détection (`src/programme_b.py`, pop-up), qui partagent le cœur sans communiquer entre eux.

## Documentation

- `docs/notes-techniques-QL570.md` — le contexte matériel vérifié.
- `docs/algorithme-appli-QL570.md` — l'organisation et les algorithmes.
- `docs/prise-en-main-gimp.md` — comment fabriquer l'image de l'étiquette.
- **Guide d'usage** (côté utilisateur), sur le wiki : <https://lesporteslogiques.net/wiki/materiel/logicos/guideql570>.
- Le **récit de construction** est tenu sur le wiki des Portes Logiques (le dépôt reste la source de vérité technique).

## Dépendances

Tout est posé par `install.sh` (voir ci-dessous). Pour mémoire :

- **apt (système), essentielles** : `python3-tk` (interface Tkinter), `python3-venv` (pour créer l'environnement virtuel), `libusb-1.0-0` (voie de repli pyusb), `xdg-user-dirs` (pour localiser le Bureau).
- **apt (système), optionnelle** : `libnotify-bin` — uniquement la notification de l'agent ; sans elle, l'appli se dégrade en douceur (l'agent écrit dans le journal).
- **pip (dans l'environnement virtuel)** : `brother_ql`, `pyudev`, `pyusb`.
- **Accès au périphérique** : appartenance au groupe `lp` + règle udev (posées à l'installation).

## Installation

À lancer **en root**, une fois par machine, par le ou la responsable. Comme les comptes ne sont pas sudoers, on devient root par `su -` (session de login : le PATH contient alors les dossiers `sbin`) — et non `su -c`.

```bash
su -
cd /chemin/vers/stickeuse
./install.sh <login>      # <login> = le compte qui utilisera l'appli
```

(Sous `sudo`, `<login>` peut être omis : on retombe alors sur `$SUDO_USER`.)

`install.sh` :

- pose l'appli (et son icône) dans **`/opt/ql570/`** (même emplacement sur chaque poste) ;
- installe les dépendances dans un environnement virtuel ;
- ajoute le compte au groupe `lp` ;
- pose la règle udev (`/etc/udev/rules.d/`) ;
- met l'agent en autostart (`/etc/xdg/autostart/`) ;
- pose une **icône de lancement sur le bureau** (Programme A).

Après l'installation, l'utilisateur doit **fermer puis rouvrir sa session** (pour que le groupe `lp` prenne effet et que l'agent démarre).

`uninstall.sh <login>` défait proprement l'installation, en laissant volontairement : le compte dans le groupe `lp` (partagé avec d'autres usages), les paquets système (utilisés ailleurs), et les journaux (effacés seulement sur confirmation).

## Licences

- **Code** : GNU Affero General Public License v3 (AGPL-3.0) — voir `LICENSE`.
- **Documentation du dépôt** : Creative Commons Attribution (CC BY).
- **Wiki** : Creative Commons Attribution - Partage dans les mêmes conditions (CC BY-SA 4.0), licence par défaut du wiki Les Portes Logiques.

## Auteurice

Conçue et développée par **Vitally LUBIN** en 2026.

## Liens

- Wiki Les Portes Logiques : <https://lesporteslogiques.net/wiki/materiel/imprimante_thermique_brother_ql-570>
- Dépôt : <https://github.com/lesporteslogiques/stickeuse>
