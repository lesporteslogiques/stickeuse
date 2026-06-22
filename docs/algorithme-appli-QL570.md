# Algorithme — Stickeuse QL-570

*Document fondateur. Décrit l'organisation, les algorithmes (en français clair, pas en pseudo-code) et l'interface de l'application **Stickeuse QL-570**, qui pilote l'imprimante d'étiquettes Brother QL-570. Projet du FabLab **Les Portes Logiques**.*

*Méthode : on écrit l'algorithme en français **avant** de coder ; on construit d'abord le **module cœur** (détection + impression), testable en ligne de commande, **avant** l'interface.*

> Le contexte matériel vérifié vit dans `notes-techniques-QL570.md`. La fabrication de l'image (par l'utilisateur) vit dans `prise-en-main-gimp.md`.

---

## 1. Vue d'ensemble

L'application repose sur **trois piliers** :

1. **Module cœur** — le moteur, sans interface, testable en ligne de commande : il sait parler à l'imprimante (détecter, vérifier l'accès, imprimer). Sous-étapes **C1 → C2 → C3**.
2. **Transversaux** — utilisés partout : le **catalogue d'erreurs** et la **journalisation**.
3. **Deux programmes** au-dessus du cœur :
   - **Programme A** — l'application d'impression (fenêtre), lancée à la demande ;
   - **Programme B** — l'agent de détection (pop-up au branchement), lancé en fond.

Point clé d'architecture : **A et B ne se parlent pas**. Ils partagent du *code* — la détection (C1) vit une seule fois dans le cœur, et chacun l'appelle de son côté. A fait détection **puis** impression (C1+C2+C3) ; B ne fait que détecter et signaler (C1).

La création de l'image **n'est pas** le travail de l'appli : c'est l'utilisateur qui la fabrique dans **GIMP** (voir `prise-en-main-gimp.md`). L'appli reçoit un PNG déjà prêt.

Cet exemplaire de QL-570 est de la **récupération** et n'imprime fiablement qu'**un seul format** (DK-11208). L'appli est donc **mono-étiquette** — non par simplification, mais par contrainte matérielle (voir Rappels).

### Rappels matériel porteurs (détail dans `notes-techniques-QL570.md`)

- L'identité Brother (`idVendor 04f9`, `idProduct 2028`, `product "QL-570"`) se lit sur le **parent USB** du nœud, jamais sur `lpX` lui-même.
- Les dimensions d'image acceptées sont **strictes** : **413 × 991 px** (portrait) **ou** leur transposée **991 × 413 px** (paysage, pivotée automatiquement par `brother_ql`). Toute autre taille → refus `Bad image dimensions`.
- **Rien en dur** : ni le port `lpX`, ni le modèle. **L'étiquette est une constante de configuration unique** (un seul point à changer), pas un menu : cet exemplaire est mono-format (DK-11208) par contrainte matérielle.
- **Portée** : grâce à la détection, l'appli tourne sur **n'importe quelle QL-570** et **n'importe quel poste Linux de famille Debian** — imprimante branchée requise. Elle n'est pas liée au FabLab ; les postes OP{NN} sont juste son lieu de déploiement.

---

## 2. Module cœur

### C1 — Détection *(figé)*

Trouver le port et le modèle de l'imprimante branchée.

1. Lister les nœuds `/dev/usb/lp*` (les ports imprimante exposés par le noyau).
2. Pour chaque nœud, demander à `pyudev` le périphérique correspondant, puis **remonter à son parent USB** (le périphérique physique) — c'est là que vit l'identité Brother, pas sur le nœud.
3. Sur ce parent, lire `idVendor`. Si c'est `04f9`, c'est notre imprimante : retenir le chemin du nœud (= le **port**), et lire au passage `idProduct` (attendu `2028`) et `product` (« QL-570 ») pour **identifier le modèle automatiquement**.
4. Premier nœud Brother trouvé → renvoyer (port, modèle). Tout parcouru sans rien → « aucune imprimante ».
5. Cas particulier : `/dev/usb/lp*` **vide** → ne pas conclure trop vite à « aucune imprimante » (peut être le pilote `usblp` absent). Ce repli est traité en C2.

### C2 — Accès & robustesse *(figé)*

C2 prolonge C1 : il gère le repli et les droits. Sortie : le trio **(backend, adresse, modèle)** prêt pour C3, ou une erreur cataloguée.

**A. Par quoi parler à l'imprimante**

1. Nœud `/dev/usb/lpX` trouvé → backend `linux_kernel`, adresse `file:///dev/usb/lpX`, modèle lu sur le parent USB.
2. Aucun nœud `lp*` → chercher directement `04f9:2028` sur le bus via `pyusb`. Trouvé → backend `pyusb`, adresse `usb://0x04f9:0x2028`, modèle lu dans le descripteur USB. Pas trouvé → **E-C2-1**.
3. Résultat : le trio **(backend, adresse, modèle)**.

**B. Droit d'écrire**

4. Voie `linux_kernel` → peut-on écrire sur le nœud (en pratique : groupe `lp`) ? Voie `pyusb` → peut-on ouvrir le périphérique via `libusb` (en pratique : règle udev posée à l'installation) ?
5. Refus → **E-C2-2** ou **E-C2-3** ; on n'imprime pas, on ne plante pas.
6. *Quand* : vérification douce au 1ᵉʳ lancement **+** rattrapage de l'erreur à l'impression (un droit ou un branchement peut changer entre les deux).

### C3 — Impression + validation d'un PNG existant *(figé)*

Entrée : trio **(backend, adresse, modèle)** · étiquette (constante de config : dimensions valides + identifiant `brother_ql`) · chemin du fichier.

**A. Charger et valider** *(avant envoi)*

1. Le fichier est-il un **PNG lisible** (extension + contenu réel) ? Non → **E-C3-1**.
2. **Dimensions** exactement celles de l'étiquette **ou** leur transposée ? Autre → **E-C3-2**. *(seul gate dur de format)*
3. *(souple)* Image nette en N&B, ou pleine de gris ? Beaucoup de gris → **E-C3-3** (avertissement, n'empêche pas d'imprimer).
   **Aucune** validation du nombre de bits ni du ppp : l'image est légitimement en 8 bits (c'est `brother_ql` qui convertit en 1 bit), et l'outil raisonne en pixels.

**B. Envoyer**

4. Construire la commande `brother_ql` avec les valeurs **détectées** (backend, adresse, modèle) + l'identifiant d'étiquette + le PNG — l'équivalent de la commande validée, mais rien en dur. La commande `brother_ql` doit être présente sur le PATH, sinon → **E-C3-6**.
5. À l'envoi : accès refusé → **E-C3-5** (filet de C2) ; état matériel (capot, fin de rouleau…) → **E-C3-4** *(si l'imprimante le remonte — à vérifier matériel)*.

*Le nombre d'exemplaires est géré par l'appelant (Programme A) : C3 imprime **une** étiquette par appel ; pour N exemplaires, l'appli répète l'envoi N fois.*

**C. Annoncer**

6. Succès → « étiquette imprimée ». Erreur → message traduit. Dans tous les cas : **journaliser**.

---

## 3. Transversaux

### Catalogue d'erreurs

Chaque erreur porte **quatre infos** : *famille · où elle est détectée · niveau de résolution · le geste*. Le catalogue n'a pas à être complet : il a besoin d'une **bonne structure d'accueil**. Il s'enrichit à l'écriture du code, aux tests d'usage, puis en production.

**Familles**

1. **Présence/détection** — aucune imprimante, débranchée à chaud.
2. **Accès/droits** — pas dans le groupe `lp`, règle udev absente.
3. **État matériel** — capot ouvert, fin de rouleau, mauvais rouleau.
4. **Image/format** — pas un PNG, mauvaises dimensions, image floue (gris).
5. **Cycle de vie** — appli déjà lancée, agent en double.
6. **Installation/dépendances** — `brother_ql` introuvable, dépendance Python manquante, absente du PATH.

**Niveaux d'escalade** (viser toujours le plus bas, et concevoir pour *faire descendre* les erreurs d'un cran) :

- **N1 — l'utilisateur, seul** : un geste simple, sans compétence technique.
- **N2 — le responsable du FabLab** : une action d'administration, le plus souvent **une fois, à l'installation**.
- **N3 — la fabricante de l'appli** : comportement inattendu ou trop spécifique = cas non prévu ou bug.

> **Prévention en amont** : l'écran d'accueil de Programme A (checklist : rouleau chargé, niveau de stock, machine sous tension…) est une **couche N1 préventive** pour ce que la QL-570 ne sait **pas** détecter (famille « état matériel »). On ne détecte pas l'indétectable : on le fait vérifier par l'humain avant de commencer.

**Registre des erreurs identifiées** *(famille · où · niveau · geste · log)*

- **E-C2-1 — Aucune imprimante.** Présence · C2-A · N1 (vérifier branchée/allumée, rebrancher) puis N2 (câble/port mort) · message court · log : *« aucun 04f9:2028 trouvé (ni lpX ni pyusb) »*.
- **E-C2-2 — Pas le droit d'écrire (voie `lpX`).** Accès · C2-B · N2 (ajouter au groupe `lp`, rouvrir la session) · message + pointer le log · log : *adresse tentée + « Permission denied »*.
- **E-C2-3 — Pas le droit d'écrire (voie `pyusb`).** Accès · C2-B · N2 (poser la règle udev à l'installation) · idem · log : *« accès USB refusé via libusb, règle udev probablement absente »*.
- **E-C3-1 — Pas un PNG / illisible.** Image/format · C3-A1 · N1 (fournir un vrai PNG) · log : *chemin + erreur*.
- **E-C3-2 — Mauvaises dimensions.** Image/format · C3-A2 · N1 (refaire dans GIMP, voir guide) · log : *trouvées vs attendues*.
- **E-C3-3 — Trop de gris (flou probable).** Image/format · C3-A3 · N1 (refaire au Crayon, voir guide) · *avertissement* · log : *proportion de gris*.
- **E-C3-4 — Capot / état matériel.** État matériel · C3-B5 · N1 (refermer/recharger puis réimprimer) · log : *statut imprimante* — *comportement exact à vérifier matériel*.
- **E-C3-5 — Accès refusé à l'envoi.** Accès · C3-B5 · N2 · réutilise E-C2-2/E-C2-3 (le filet).
- **E-C3-6 — `brother_ql` introuvable.** Installation/dépendances · C3-B4 · N2 (vérifier que `brother_ql` est installé et que son dossier — `~/.local/bin`, ou le venv `/opt/ql570/` — est sur le PATH) · log : *« commande brother_ql absente du PATH »*.

*Non encore codifiée :* « appli déjà lancée » (Cycle de vie, à traiter en A/B).

### Journalisation

- **Un fichier de log par poste** : `ql570-<hostname>.log` (chez nous `ql570-OP{NN}.log`), à un endroit fixe et documenté (`~/.ql570/`), ouvrable avec n'importe quel éditeur.
- **Horodaté**, une ligne par événement. Le nom de la machine est **dans le nom du fichier ET sur chaque ligne** (une ligne extraite reste auto-suffisante).
- Champs d'une ligne : *horodatage · machine · famille · où détecté · niveau · message système brut*. Le log = le catalogue daté et complété du détail système.
- **Journal cumulatif**, pas un fichier par erreur (sinon on perd la séquence d'événements qui dépanne).
- L'**agent B n'a pas de fenêtre** : le log est son **seul moyen de signaler** ce qui se passe.
- Le message à l'écran (N1/N2) peut **pointer vers le log** pour le dépannage.
- En Python, le module standard `logging` fournit horodatage, niveaux et rotation.
- *État actuel* (`src/journal.py`) : *logger* nommé `ql570`, partagé par le cœur et les deux programmes, configuré une fois au lancement, écrivant **en ajout** dans `~/.ql570/ql570-<hostname>.log` au format `horodatage [niveau] message`. Les champs structurés (machine · famille · où) sur chaque ligne et la rotation restent à enrichir (voir Chantiers).

---

## 4. Programme A — application d'impression « Stickeuse QL-570 »

Fenêtre (Tkinter), lancée à la demande, **consommatrice du cœur**. Deux écrans.

### 4.1 Écran d'accueil « Bienvenue ! » *(au lancement)*

Une fenêtre de **checklist préventive** (garde-fou humain N1, pour ce que la QL-570 ne sait pas détecter), avant la fenêtre principale :

- l'imprimante Brother QL-570 est branchée sur le secteur ;
- elle est sous tension (voyant vert allumé) ;
- les étiquettes **DK-11208 (38×90 mm)** sont chargées ;
- il y a suffisamment d'étiquettes pour le projet ;
- bouton **OK** pour continuer.

En arrière-plan de cet écran s'exécutent **C1 + C2** (détection + accès). En cas d'échec → message d'erreur catalogué (E-C2-*) au lieu d'ouvrir la fenêtre principale.

*L'accueil parle « 38×90 mm » (langage humain) ; le code, lui, utilisera l'identifiant `brother_ql` `39x90`.*

### 4.2 Fenêtre principale « Stickeuse QL-570 »

- **Bandeau d'en-tête** : titre + icône imprimante.
- **Section « Fichier à imprimer »** : bouton **« Parcourir… »** + libellé du fichier choisi (« Aucun fichier sélectionné » par défaut).
- **Section « Nombre d'exemplaires »** : sélecteur numérique (défaut **1**) + « étiquette(s) ».
- **Bouton « Imprimer »** (vert), **désactivé tant qu'aucun fichier valide n'est sélectionné**.
- **Pied de page** : © année, auteurice, FabLab, licence.

**Comportement**

- **Choisir un fichier** → validation **C3-A** (PNG ? dimensions ?). Invalide → message (E-C3-1/2/3) et le bouton reste/redevient inactif. Valide → bouton actif, libellé du fichier affiché.
- **Clic « Imprimer »** → **C3**, répété autant de fois que le **nombre d'exemplaires** choisi → message de résultat (succès « imprimé » / erreur traduite). **Journaliser** dans tous les cas.
- Dialogues de succès/erreur : fenêtres-message standard, contenu piloté par le **catalogue d'erreurs**.
- **Pas d'aperçu** en v1 (le libellé du fichier suffit).

---

## 5. Programme B — agent de détection *(squelette, à détailler)*

Petit programme tournant en fond dans la session, **consommateur du cœur (C1)**.

- Se lance tout seul à l'ouverture de session (*autostart*).
- Surveille les branchements/débranchements USB (`pyudev`).
- À l'apparition de la QL-570 → **pop-up** « QL-570 détectée ».
- N'imprime **jamais**.

---

## 6. Chantiers & questions ouvertes

*Liste vivante des angles morts, par ordre d'importance. À refermer au fil des phases.*

- **Programme A — interface d'impression** *(prochaine étape de code)* : fenêtre Tkinter, deux écrans spécifiés en §4, au-dessus du cœur ; rouvre le journal au démarrage et y consigne ses événements.
- **Programme B — agent de détection** *(à détailler puis coder)* : voir §5 ; réutilise C1 + le journal.
- **Installation / déploiement** *(chantier à part entière)* : `install.sh` (en root) — dépendances (`python3-tk` via apt ; `brother_ql`, `pyudev` via pip dans un venv sous `/opt/ql570/`), pose de la **règle udev** (`/etc/udev/rules.d/`), ajout au groupe **`lp`**, **autostart** de B (`/etc/xdg/autostart/`). Plus un `uninstall.sh` symétrique (sans retirer du groupe `lp`, partagé ; demander pour les logs), et une **auto-vérification des dépendances au démarrage**. *(Le déploiement manuel sur OP52 a déjà dressé une partie du cahier des charges : dépendances, groupe `lp`, et le constat que ces gestes N2 exigent root.)*
- **Documentation wiki (Les Portes Logiques)** *(à boucler)* : page « Utiliser l'application Stickeuse-QL570 » — **raconter l'usage et renvoyer au dépôt** (source de vérité technique), sans dupliquer les instructions d'install. À aligner : le spec d'image affiché côté wiki doit indiquer le `413×991` de l'appli ; ajouter le lien vers `github.com/lesporteslogiques/stickeuse`.
- **Cohabitation A/B** *(ouvert)* : que fait concrètement la pop-up de B (notifier seulement, ou proposer d'ouvrir A) ? Éviter une pop-up redondante si A est déjà ouverte.
- **Débranchement à chaud** *(ouvert)* : pendant que A est ouverte (détectée au lancement, partie avant l'impression).
- **Mineurs** : plusieurs imprimantes Brother branchées (C1 prend la première — simplification assumée) ; examiner `template_paysage.png` (vestige de l'ancienne « Stickeuse ») ; maquettes dédiées des dialogues succès/erreur si besoin ; enrichir les lignes de journal avec les champs structurés (*famille · où · niveau*) du spec, et envisager une rotation des logs.

**Refermés**

- **Module cœur (C1 + C2 + C3)** → codé, commenté, testé sur matériel (impression réelle sur OP42 ; détection portable sur OP52). `src/coeur.py`.
- **Journalisation** → codée (`src/journal.py`), un log par poste dans `~/.ql570/`.
- **Catalogue d'erreurs** → structure d'accueil + entrées E-C2-* / E-C3-* (dont `E-C3-6`, découverte en codant).
- **Version-control / GitHub** → dépôt public `lesporteslogiques/stickeuse` en place : README, `.gitignore` (logs, `__pycache__`, venv), LICENSE, docs ; cœur + journal poussés. Source de vérité = le dépôt ; le wiki raconte et renvoie.
- *Nombre d'exemplaires* → spécifié (Programme A).
- *Cliquer « Imprimer » sans fichier* → bouton désactivé tant qu'aucun fichier valide.
- *Étiquette ≠ rouleau chargé* → réglé : exemplaire mono-format (matériel) + garde-fou humain à l'accueil.
- *Aperçu* → écarté pour la v1.
- *Choix du format d'étiquette* → supprimé : mono-format ; l'étiquette est une constante de config.

---

## Statut

- **Module cœur (C1 + C2 + C3)** : **codé et validé sur matériel**. `src/coeur.py`. Impression réelle confirmée sur OP42 ; détection portable confirmée sur OP52 (bloquée seulement par l'accès root, par design).
- **Journalisation** : **codée**. `src/journal.py` — un log par poste dans `~/.ql570/ql570-<hostname>.log`.
- **Catalogue d'erreurs** : structure + entrées E-C2-* / E-C3-* (dont `E-C3-6`).
- **Dépôt** : `github.com/lesporteslogiques/stickeuse` (public) — cœur, journal et docs poussés.
- **Programme A** : interface **spécifiée** (2 écrans), **à coder**.
- **Programme B** : squelette, à détailler.
- **Chantiers ouverts** : `install.sh` / `uninstall.sh`, documentation du wiki.
- **Projet** : Stickeuse QL-570 — Vitally LUBIN / Les Portes Logiques — code **GPL-3.0**, docs **CC BY**.
- **Prochaine étape** : coder le **Programme A** (fenêtre d'impression), au-dessus du cœur.
