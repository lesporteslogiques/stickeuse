# QL-570 — Ce qu'on a appris

*Base de travail pour le futur programme Python. Tout a été vérifié sur le matériel réel (poste OP51).*

## Objectif

Piloter l'imprimante d'étiquettes **Brother QL-570** depuis un programme **Python à interface graphique** (Tkinter), utilisable par n'importe qui sans compétence technique, et **portable sur toute machine Debian**.

## Commande de référence (validée)

```bash
brother_ql -b linux_kernel -m QL-570 -p file:///dev/usb/lp3 print -l 39x90 image.png
```

Tout ce qui est codé en dur ici (`lp3`, `QL-570`) doit être remplacé par de la **détection** dans l'appli.

## Détection de l'imprimante

- Identité USB : `idVendor 04f9` (Brother) + `idProduct 2028` (QL-570).
- Le périphérique noyau est `/dev/usb/lpX` — **X varie selon les rebranchements**, ne jamais le coder en dur.
- L'identité Brother se lit sur le **périphérique USB parent** (remontée de l'arbre avec `udevadm info -a`), pas sur le nœud `lpX` lui-même.
- Le même attribute walk expose aussi `product=="QL-570"` (et `idProduct 2028`) : le **modèle** peut donc être auto-détecté au même titre que le port — `-m QL-570` n'a pas besoin d'être codé en dur non plus.

Prototype shell de la détection :

```bash
LP=$(for d in /dev/usb/lp*; do
  udevadm info -a -n "$d" 2>/dev/null | grep -q 'idVendor.*04f9' && { echo "$d"; break; }
done)
```

En Python : `pyudev`, récupérer le périphérique et remonter à son parent USB (`find_parent('usb', 'usb_device')`) pour lire `idVendor`.

## Étiquette

- Rouleau chargé : **DK-11208** = 38 × 90 mm, **prédécoupé** (die-cut).
- Identifiant `brother_ql` : **`39x90`** (⚠️ piège de nommage : l'outil dit « 39x90 » alors que l'étiquette fait 38 mm).
- Dimensions imprimables : **413 × 991 px**.

> ⚠️ Ces valeurs (`39x90`, 413 × 991 px) sont **spécifiques à la DK-11208**. Pour gérer d'autres rouleaux DK, chaque étiquette a son **propre identifiant et ses propres dimensions**, à lire via `brother_ql info labels`. Le piège de nommage « 38 mm → `39x90` » n'est qu'un travers parmi d'autres possibles : **ne pas coder l'appli en dur pour une seule étiquette**.

## Contraintes d'image

- **Taille STRICTE** pour le prédécoupé : exactement **413 × 991 px** (portrait), ou **991 × 413 px** (paysage, que `brother_ql` pivote automatiquement de 90°). Toute autre taille → refus `Bad image dimensions`. Le prédécoupé n'est **jamais** redimensionné par l'outil (contrairement au continu).
- **Couleur** : noir/blanc pur (imprimante thermique monochrome). Travailler en noir `#000000` sur blanc `#FFFFFF`. Pas de tramage (dither) pour texte/trait ; tramage uniquement pour les photos.
- **Résolution** : 300 ppp.
- **Orientation** : `-r auto` (le défaut) pivote uniquement la **transposée exacte** (991×413). La rotation s'appuie sur Pillow → sens **antihoraire**.

## Accès & robustesse

- Accès au périphérique sans root : compte membre du groupe **`lp`** (à vérifier au 1ᵉʳ lancement de l'appli).
- Les chemins `/dev/usb/lpX` et les attributs sysfs (`idVendor`…) sont des **interfaces noyau stables** : peu de risque de changement par une mise à jour Debian.
- **Vrai risque de portabilité** : le pilote `usblp` absent ou désactivé → `/dev/usb/lpX` n'existe pas du tout. Parade : repli sur le backend **`pyusb`** (`usb://0x04f9:0x2028`) et/ou **règle udev** posée à l'installation.

## Architecture cible (à construire)

1. **Agent de détection** — petit programme tournant dans la session de l'utilisateur, surveille udev (`pyudev`), affiche une **pop-up au branchement** de la QL-570. Lancé automatiquement à l'ouverture de session (*autostart*).
2. **Application d'impression** — fenêtre **Tkinter**, lancée à la demande pour composer et imprimer une étiquette.

Dépendances Debian : `python3-tk` (apt) ; `brother_ql` et `pyudev` (pip).

## À faire / à éclaircir

- Récupérer et examiner `template_paysage.png` (vestige de l'ancienne « Stickeuse ») — peut renseigner la mise en page d'origine.
- Confirmer si les dossiers personnels sont **partagés** entre les postes (OP42 / OP51).
- Définir la **forme exacte de l'interface** : champs de saisie, choix de l'étiquette, aperçu, orientation…
