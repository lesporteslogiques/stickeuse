# La QL-570 — notes techniques

*Ce que la machine impose, et qu'aucune lecture du code ne permet de retrouver :
son identité sur le bus USB, les formats d'image qu'elle exige au pixel près,
la façon de lui envoyer une impression, et ce qui peut l'empêcher de répondre.*

*Tout a été vérifié sur le matériel réel, avant l'écriture du code, puis en
conditions de déploiement. C'est le document à relire avant de toucher à la
détection ou aux formats d'étiquette — les autres se déduisent du code, celui-ci
non.*

## Sommaire

- [Comment l'ordinateur reconnaît la machine](#comment-lordinateur-reconnaît-la-machine)
- [Ce que la machine accepte comme image](#ce-que-la-machine-accepte-comme-image)
- [Comment on lui envoie une impression](#comment-on-lui-envoie-une-impression)
- [Ce qui peut l'empêcher de répondre](#ce-qui-peut-lempêcher-de-répondre)
- [Questions d'alors, aujourd'hui refermées](#questions-dalors-aujourdhui-refermées)

## Comment l'ordinateur reconnaît la machine

Trois niveaux, qu'il vaut mieux ne pas confondre : **la machine se déclare** sur
le bus USB, **le noyau la relaie** en créant un nœud et en exposant ses
attributs, **le programme les lit**.

- Identité USB : `idVendor 04f9` (Brother) + `idProduct 2028` (QL-570). Ces deux
  codes sont les mêmes sur **tous les exemplaires** de ce modèle : rien n'est lié
  à la machine du FabLab.
- Le périphérique noyau est `/dev/usb/lpX` — **X varie selon les rebranchements**,
  ne jamais le coder en dur.
- ⚠️ L'identité Brother se lit sur le **périphérique USB parent** (remontée de
  l'arbre avec `udevadm info -a`), **pas** sur le nœud `lpX` lui-même. C'est le
  piège principal de la détection.
- Le même parcours expose aussi `product=="QL-570"` : le **modèle** s'auto-détecte
  au même titre que le port.

Prototype shell de la détection :

```bash
LP=$(for d in /dev/usb/lp*; do
  udevadm info -a -n "$d" 2>/dev/null | grep -q 'idVendor.*04f9' && { echo "$d"; break; }
done)
```

En Python : `pyudev`, récupérer le périphérique et remonter à son parent USB
(`find_parent('usb', 'usb_device')`) pour lire `idVendor`.

## Ce que la machine accepte comme image

**Les rouleaux éprouvés**

- **DK-11208** — 38 × 90 mm, prédécoupé (*die-cut*). Identifiant `brother_ql` :
  **`39x90`**. Dimensions imprimables : **413 × 991 px**.
- **DK-11202** — 62 × 100 mm, prédécoupé. Dimensions : **696 × 1109 px**. Au
  catalogue de l'appli, marqué indisponible en attendant la réparation de la
  machine.

⚠️ **Piège de nommage** : `brother_ql` appelle « 39x90 » une étiquette qui mesure
38 mm. Chaque référence a son propre identifiant et ses propres dimensions, à
lire avec `brother_ql info labels`. Ne jamais coder l'appli en dur pour une seule
étiquette — d'où le catalogue `ETIQUETTES` de `src/coeur.py`, un rouleau par
ligne.

**Les contraintes d'image**

- **Taille stricte** sur du prédécoupé : exactement les dimensions du rouleau
  (portrait), ou leur transposée (paysage, que `brother_ql` pivote
  automatiquement de 90°). Toute autre taille → refus `Bad image dimensions`. Le
  prédécoupé n'est **jamais** redimensionné, contrairement au continu.
- **Couleur** : noir/blanc pur — l'imprimante est thermique et monochrome. Noir
  `#000000` sur blanc `#FFFFFF`. Pas de tramage (*dither*) pour le texte et le
  trait ; tramage uniquement pour les photos.
- **Résolution** : 300 ppp.
- **Orientation** : `-r auto` (le défaut) ne pivote que la **transposée exacte**.
  La rotation s'appuie sur Pillow, donc dans le sens **antihoraire**.

## Comment on lui envoie une impression

Commande de référence, validée sur matériel :

```bash
brother_ql -b linux_kernel -m QL-570 -p file:///dev/usb/lp3 print -l 39x90 image.png
```

Tout ce qui y est écrit en dur — `lp3`, `QL-570`, `39x90` — est remplacé dans
l'appli par de la détection ou par le catalogue.

Deux voies possibles vers la machine :

- **`linux_kernel`** — en passant par le nœud `/dev/usb/lpX`. C'est la voie
  normale.
- **`pyusb`** — en s'adressant directement au bus (`usb://0x04f9:0x2028`). C'est
  la voie de repli, quand la première n'est pas disponible.

## Ce qui peut l'empêcher de répondre

- **Le compte n'est pas dans le groupe `lp`** — pas d'accès au périphérique sans
  root. Vérifié au premier lancement de l'appli.
- **Le pilote `usblp` est absent ou désactivé** — `/dev/usb/lpX` n'existe alors
  pas du tout. C'est le vrai risque de portabilité. Parade : le repli `pyusb`, et
  la règle udev posée à l'installation.
- **En revanche**, les chemins `/dev/usb/lpX` et les attributs sysfs (`idVendor`…)
  sont des **interfaces noyau stables** : une mise à jour de Debian a peu de
  chances de les changer.

## Questions d'alors, aujourd'hui refermées

- **Forme de l'interface** → définie et codée : deux écrans, déclaration du
  rouleau à l'accueil, aperçu, exemplaires multiples, annulation
  (`src/programme_a.py`).
- **`template_paysage.png`**, vestige de l'ancienne « Stickeuse » → sans suite ;
  les formats sont désormais décrits en code par `test/generer-mire.py`.
- **Dossiers personnels partagés entre postes** → sans objet : l'installation ne
  code aucun nom de compte en dur, elle lit le dossier « Images » par
  `xdg-user-dir`.

L'organisation du programme est décrite dans
[`algorithme-appli-QL570.md`](algorithme-appli-QL570.md) ; les chantiers encore
ouverts y sont suivis.

---

*Projet Stickeuse QL-570 — Vitally LUBIN, FabLab Les Portes Logiques (2026) — documentation sous CC BY.*
