# Prise en main de GIMP — créer une image

*Guide pas à pas, basé sur ce qu'on a vu ensemble. **Document évolutif** : à enrichir au fur et à mesure.*

*Contexte d'origine : fabriquer une image d'étiquette pour l'imprimante QL-570. Les valeurs propres à ce cas sont signalées « (exemple QL-570) » ; le reste est général.*

## 1. Créer une nouvelle image

`Fichier > Nouvelle image`

- **Largeur** et **Hauteur** : en **pixels** (vérifier que l'unité à droite est bien `px`).
  - *(exemple QL-570 : 413 × 991 px pour une étiquette DK-11208)*
- Déplier **Options avancées** :
  - **Résolution X et Y** : `300` (unité *pixels/in* = points par pouce, ppp) — la définition d'impression.
  - **Espace de couleurs** : **Niveaux de gris** si l'image finale est en noir et blanc ; sinon *Couleur RVB*.
  - **Précision** : *Entier 8-bit*.
  - **Gamma** : laisser le défaut (*gamma perceptuel*).
  - **Remplir avec** : **Blanc** (évite les surprises ; « couleur d'arrière-plan » dépend du réglage courant, pas forcément blanc).
- Valider.

## 2. Régler la couleur de premier plan en noir pur

- Double-cliquer sur le **carré de couleur de premier plan** (en haut de la boîte à outils) et saisir `000000`.
- Raccourci : touche **D** → réinitialise noir (premier plan) / blanc (arrière-plan).

## 3. Tracer des traits

Deux outils, dans `Outils > Outils de peinture` :

- **Crayon** (touche **N**) : bords **nets, sans anti-crénelage** → noir pur. Recommandé pour des traits propres.
- **Pinceau** (touche **P**) : bords adoucis (anti-crénelage) → quelques pixels gris sur les contours.

Régler la **taille** du trait dans les options de l'outil (à gauche).

- Trait à main levée : **cliquer-glisser**.
- Trait droit : cliquer un point, puis **Maj+clic** sur un autre → ligne droite entre les deux. Enchaîner les Maj+clic pour des segments reliés.

## 4. Écrire ou coller du texte

- Outil **Texte** : `Outils > Texte` (touche **T**, ou l'icône **A** dans la boîte à outils).
- Cliquer sur le canevas : une zone de texte apparaît. **Taper** le texte, ou **coller** avec `Ctrl+V`.
- Dans les options de l'outil : régler la **taille** et la **couleur** (noir).
- Le texte arrive sur un **calque séparé** (voir l'aplatissement, étape 5).
- Attention à la **largeur du canevas** : un texte trop long déborde → réduire la taille de police, ou écrire dans la longueur.

## 5. Aplatir l'image

`Image > Aplatir l'image`

- Fusionne tous les calques (texte, traits…) avec le fond.
- **À faire avant l'export**, sinon certains éléments (comme le texte resté sur son calque) risquent de ne pas être inclus.

## 6. Exporter en PNG

- `Fichier > Exporter sous…`
- Donner un nom finissant par `.png`, choisir le dossier, puis **Exporter**.
- Une fenêtre d'options PNG s'ouvre → **Exporter** à nouveau (les réglages par défaut conviennent).

---

## À enrichir plus tard

*(Sujets pas encore couverts — on les ajoutera au fil de l'eau.)*

- Les **calques** : créer, déplacer, masquer, fusionner.
- Les **sélections** (rectangle, ellipse, lasso) et le remplissage d'une zone.
- Le **déplacement / alignement** précis des éléments (outil Déplacer, touche **M**).
- **Importer ou coller** une image existante dans le canevas.
- **Redimensionner / recadrer** (`Image > Échelle et taille de l'image`, `Image > Taille du canevas`).
