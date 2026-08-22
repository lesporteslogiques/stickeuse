# Dépendances — Stickeuse QL-570

> **Rien à installer à la main** : `install.sh` pose tout. Ce document sert à
> diagnostiquer une panne, à installer hors du script, ou à comprendre pourquoi
> ces choix ont été faits.
>
> La liste qui fait foi est celle du script lui-même, commenté ligne à ligne.
> Ce qui est écrit ici peut vieillir ; `install.sh`, non.

## Ce qui est installé

**Paquets système (apt), essentiels**

- `python3-tk` — l'interface graphique (Tkinter).
- `python3-venv` — pour créer l'environnement virtuel.
- `libusb-1.0-0` — la bibliothèque système dont dépend pyusb, voie de repli.
- `xdg-user-dirs` — pour localiser le dossier « Images », où sont déposées les
  mires de test, quelle que soit la langue du poste.

**Paquets système (apt), optionnels**

- `libnotify-bin` — la notification de l'agent au branchement.
- `gimp` — pour fabriquer les images d'étiquettes sur le poste.

**Paquets Python (pip), dans `/opt/ql570/venv`**

- `brother_ql` — le pilote d'impression.
- `pyudev` — la lecture des branchements USB.
- `pyusb` — la voie de repli directe sur le bus.

**Accès au périphérique**

- appartenance de l'utilisateur au groupe `lp` ;
- règle udev posée dans `/etc/udev/rules.d/`.

## Pourquoi ces choix

### Un environnement virtuel, pas le Python du système

`brother_ql`, `pyudev` et `pyusb` sont installés dans `/opt/ql570/venv`, sans
jamais toucher aux paquets Python de Debian. L'application ne peut donc rien
casser d'autre sur le poste, et la désinstallation se réduit à supprimer un
dossier.

C'est aussi de là que `coeur.py` retrouve `brother_ql` : par `sys.prefix`, et non
par le `PATH`. Le défaut est resté latent deux déploiements durant, quand une
copie système de `brother_ql` traînait dans le `PATH` et se faisait appeler à la
place de celle du venv.

### `libnotify-bin` optionnel et non essentiel

Il ne porte que la pop-up de l'agent. Son absence a été rencontrée en conditions
réelles : l'agent a continué de fonctionner en écrivant dans son journal
(`~/.ql570/`). C'est cette dégradation en douceur qui justifie le classement —
l'application imprime, seule la notification manque.

### `gimp` hors du chemin critique

GIMP sert à *fabriquer* l'image, pas à l'imprimer. L'application accepte tout PNG
conforme, d'où qu'il vienne — préparé sur un autre poste, reçu par courriel,
produit par un autre logiciel. Elle se contente de signaler l'absence de GIMP à
l'accueil, sans bloquer.

## En cas de doute

Pour savoir ce qui est réellement installé sur un poste :

```bash
ls /opt/ql570              # l'application et son venv
/opt/ql570/venv/bin/pip list   # les paquets Python du venv
groups                     # « lp » doit y figurer
```

---

*Projet Stickeuse QL-570 — Vitally LUBIN, FabLab Les Portes Logiques (2026) — documentation sous CC BY.*
