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

Cet exemplaire de QL-570 est de la **récupération**. Il n'imprime aujourd'hui de façon éprouvée que le **DK-11208** ; le **DK-11202** est au catalogue mais marqué indisponible, en attente de réparation. L'appli est donc **multi-rouleaux dans sa structure** et momentanément limitée dans les faits — la contrainte est matérielle, elle n'est plus inscrite dans le code.

### Rappels matériel porteurs (détail dans `notes-techniques-QL570.md`)

- L'identité Brother (`idVendor 04f9`, `idProduct 2028`, `product "QL-570"`) se lit sur le **parent USB** du nœud, jamais sur `lpX` lui-même.
- Les dimensions d'image acceptées sont **strictes**, et **dépendent du rouleau déclaré** : 413 × 991 px pour le DK-11208, 696 × 1109 px pour le DK-11202 — ou leur transposée (paysage, pivotée automatiquement par `brother_ql`). Toute autre taille → refus `Bad image dimensions`.
- **Rien en dur** : ni le port `lpX`, ni le modèle. Les étiquettes forment un **catalogue de configuration** (`ETIQUETTES` dans `src/coeur.py`) : un rouleau = une ligne, avec ses dimensions, sa référence et, le cas échéant, le motif de son indisponibilité. La personne déclare à l'accueil lequel est chargé — la machine ne sait pas le dire.
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
2. **Dimensions** exactement celles de l'étiquette **ou** leur transposée ? Autre → **E-C3-2**. *(seul gate dur de format)* L'étiquette de référence n'est plus une constante unique mais celle que la personne a **déclarée chargée** à l'accueil.
3. *(souple)* Image nette en N&B, ou pleine de gris ? Beaucoup de gris → **E-C3-3** (avertissement, n'empêche pas d'imprimer).
   **Aucune** validation du nombre de bits ni du ppp : l'image est légitimement en 8 bits (c'est `brother_ql` qui convertit en 1 bit), et l'outil raisonne en pixels.

**B. Envoyer**

4. Construire la commande `brother_ql` avec les valeurs **détectées** (backend, adresse, modèle) + l'identifiant d'étiquette + le PNG — l'équivalent de la commande validée, mais rien en dur. L'exécutable `brother_ql` est **déduit**, pas cherché : il vit dans le dossier `bin/` de l'environnement virtuel qui exécute l'appli (`sys.prefix`). Absent de là → **E-C3-6**. *On ne passe volontairement pas par le PATH : celui-ci dépend de qui lance l'appli, ne contient pas le venv, et pourrait désigner une autre copie de `brother_ql` posée ailleurs sur le poste — c'est exactement ce qui a masqué le défaut pendant deux déploiements.*
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
- **E-C3-6 — `brother_ql` absent de l'environnement virtuel.** Installation/dépendances · C3-B4 · N2 (réinstaller l'application : le venv `/opt/ql570/venv/` est incomplet) · log : *« brother_ql absent de sys.prefix/bin »*. *Une seule cause possible, par construction : l'exécutable est déduit du venv et de nulle part ailleurs. Avant le correctif, ce même code pouvait signifier « pas installé », « installé ailleurs » ou « PATH mal formé ».*

- **E-C3-7 — Rouleau inconnu.** Installation/dépendances · lancement en ligne de commande · N3 (identifiant absent du catalogue `ETIQUETTES`) · log : *identifiant demandé + liste des identifiants connus*. *Inaccessible depuis l'interface, qui ne propose que les rouleaux du catalogue.*

- **E-C3-8 — Rouleau indisponible.** État matériel · lancement en ligne de commande · N2 (attendre la remise en service, ou vider le champ `indisponible` si elle a eu lieu) · log : *référence + motif*. *Inatteignable depuis l'interface, qui grise ces rouleaux.*

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
- le rouleau **déclaré juste au-dessus** est bien celui qui est chargé (la ligne reprend sa référence et les pixels attendus) ;
- il y a suffisamment d'étiquettes pour le projet ;
- une case **« Tout cocher »**, en tête, qui applique son état à toutes les autres — et qui se décoche d'elle-même dès qu'une case ne l'est plus, pour ne jamais afficher un état faux ;
- bouton **OK** pour continuer.

En arrière-plan de cet écran s'exécutent **C1 + C2** (détection + accès). En cas d'échec → message d'erreur catalogué (E-C2-*) au lieu d'ouvrir la fenêtre principale.

*L'accueil parle « 38×90 mm » (langage humain) ; le code, lui, utilisera l'identifiant `brother_ql` `39x90`.*

**Choix du rouleau** — la QL-570 ne sait pas dire quel rouleau elle contient : rien dans son protocole ne le renseigne. C'est donc déclaré par l'humain, à l'accueil, au milieu des autres vérifications qu'on ne peut pas automatiser. Deux rouleaux au catalogue (`src/coeur.py`) : **DK-11208** (38 × 90 mm → 413 × 991 px) et **DK-11202** (62 × 100 mm → 696 × 1109 px), tous deux prédécoupés, donc aux dimensions imposées au pixel près.

Boutons **ronds** et non carrés : la forme dit la règle — un seul rouleau est chargé à la fois. La ligne de checklist « le rouleau … est chargé » reprend le libellé et les pixels attendus, et **se décoche** si l'on change de rouleau après l'avoir cochée : une confirmation portant sur autre chose ne vaut plus rien.

**Rouleau préparé mais indisponible** — un rouleau peut figurer au catalogue sans être utilisable aujourd'hui (matériel en réparation, rouleau commandé…). Son entrée porte alors le motif dans le champ `indisponible`, et l'interface le montre **grisé, avec la raison écrite dessous**. Trois comportements étaient possibles : le masquer (on perd la trace de ce qui est prévu, et il faut re-livrer le jour venu), le laisser actif avec un avertissement (l'échec surviendrait après le travail dans GIMP, trop tard), ou le griser en disant pourquoi. Le troisième est le seul qui transmette l'information complète : *ce format existe, il est prévu, il n'est pas utilisable aujourd'hui*. Le réactiver = vider une chaîne dans `coeur.py`.

*Un mauvais choix ne produit aucune erreur technique* : l'image du bon format sera refusée (E-C3-2) et celle du mauvais format sortira mal cadrée. C'est le prix d'une information que la machine ne donne pas.

L'accueil **vérifie aussi la présence de GIMP** sur le poste (paquet système ou Flatpak). Absent → un message d'avertissement s'affiche sous la checklist, avec la commande à transmettre au responsable du FabLab (`apt install gimp`). Ce n'est **pas** un blocage : GIMP sert à *fabriquer* l'image, pas à l'imprimer.

### 4.2 Fenêtre principale « Stickeuse QL-570 »

**Redimensionnement** — chaque fenêtre selon son usage. L'**accueil** et les **fenêtres-message** sont figés : leur taille est celle de leur contenu, les étirer n'ajouterait que du vide. La **fenêtre d'impression** est libre, et c'est le cadre d'aperçu — lui seul — qui absorbe la place gagnée : on agrandit pour mieux voir l'étiquette, pas pour agrandir les libellés. La vignette est alors redessinée depuis le fichier d'origine (jamais depuis la vignette précédente, qui deviendrait floue), avec un anti-rebond de 150 ms pour ne pas la refaire à chaque pixel du geste. Le **sélecteur de fichiers** est agrandi à son ouverture : c'est Tk qui le fabrique, on le retrouve donc par son nom (`.__tk_filedialog`) juste après son apparition, et on lui donne 55 % × 65 % de l'écran — c'est la fenêtre où l'on cherche, elle a tout à gagner à être grande.

**Dimensions** — aucune taille en pixels codée en dur : la fenêtre prend une **part de l'écran** mesuré au lancement (50 % de la largeur, 75 % de la hauteur ; l'accueil, plus court, prend 40 % × 45 %) et se centre. 

**Taille de l'interface** — une constante, `TAILLE_BASE`, en points, et **une mesure** pour tout le reste. Une taille de police est en points ; Tk les convertit en pixels selon la densité de l'écran (14 points ≈ 19 px sur un écran ordinaire, ≈ 50 px sur un écran fin). Tout ce qui se mesure en pixels — cases à cocher, largeur de coupe des messages, icône, aperçu — est donc déduit de la hauteur **mesurée** d'une ligne de texte (`font metrics -linespace`), et non du nombre de points. Le déduire des points laissait ces éléments deux fois trop petits sur écran haute densité. Elle est appliquée à toutes les **polices nommées** de Tk (`TkDefaultFont`, `TkMenuFont`…), donc aussi aux fenêtres qu'on n'a pas écrites — sélecteur de fichiers, fenêtres-message, menus. En dérivent : trois variantes de police (titre, ligne d'état, pied de page), la taille des cases à cocher, de l'icône et de l'aperçu. Un seul chiffre commande l'interface entière.

**Cases à cocher dessinées** — la case native de Tk a, sous X11, une taille **fixe** : ni la police ni le facteur d'échelle (`tk scaling`) ne la font bouger, ce qui la rend illisible dès qu'on grossit le texte. On la remplace donc par deux images fabriquées avec Pillow (case vide, case cochée), posées via `indicatoron=False` + `image`/`selectimage`. Elles sont dessinées en quadruple puis réduites, pour lisser les obliques du ✓.

*Trois erreurs traversées avant d'arriver là.* (1) Multiplier la taille de chaque widget par un coefficient : nos widgets grossissaient, les fenêtres standard de Tk gardaient leur taille par défaut — un titre énorme au-dessus d'un sélecteur de fichiers minuscule. (2) Ne régler que les polices : les textes grandissaient, les cases à cocher restaient illisibles. (3) Croire que le facteur d'échelle de Tk les ferait grandir : un essai à `tk scaling 10` a montré qu'elles ne bougent pas d'un pixel. D'où les images. Garde-fou inverse pour les petits écrans : une fois les widgets posés, on compare cette part à la place que le contenu **réclame** et on retient la plus grande (sans dépasser l'écran) — sinon le bouton « Imprimer », tout en bas, serait coupé.

**Intégration au bureau** — l'entrée de menu ne déclare **aucune catégorie** : sur GNOME, une catégorie (Utility, System…) range l'application dans un sous-dossier de la grille, où personne ne pense à la chercher. Elle déclare en revanche `StartupWMClass`, qui doit correspondre au `className` des fenêtres Tkinter : c'est ce qui permet au dock de reconnaître l'appli **pendant qu'elle tourne**, avec sa vraie icône. Elle n'est **pas** épinglée aux favoris : le dock l'affiche le temps de son exécution, comme n'importe quelle application, et chacun reste libre de l'épingler. Poser le `.desktop` suffit à la faire apparaître dans le lanceur : GNOME ajoute seul les nouvelles applications à sa grille. L'installation **ne touche donc pas** au rangement de la grille — c'est l'arrangement personnel de l'utilisateur. Une exception, et une seule : si le `.desktop` déjà présent déclarait une catégorie (installation antérieure), GNOME a mémorisé un rangement plaçant l'appli dans « Utilitaires », dont retirer la catégorie ne la sort pas. Ce cas est détecté avant l'écrasement du fichier, et lui seul déclenche une remise à plat (`app-picker-layout`) — une fois, à la migration.

- **Bandeau d'en-tête** : icône de l'appli (cherchée à côté du programme, comme dans B) + titre + état de l'imprimante détectée.
- **Section « Fichier à imprimer »** : bouton **« Parcourir… »** + libellé du fichier choisi (« Aucun fichier sélectionné » par défaut).
- **Aperçu** : vignette du PNG validé, proportions préservées.
- **Section « Nombre d'exemplaires »** : sélecteur numérique (défaut **1**) + « étiquette(s) ».
- **Boutons « Imprimer »** (vert) et **« Annuler »**, côte à côte. Imprimer est désactivé tant qu'aucun fichier valide n'est sélectionné ; Annuler l'est hors impression — *un bouton cliquable sans effet est un mensonge d'interface*.
- **Ligne d'état** : « Impression 2 / 5… », puis vide au repos.
- **Pied de page** : © année, auteurice, FabLab, licence.

**Comportement**

- **Choisir un fichier** → la boîte de dialogue s'ouvre sur le **dossier « Images »** de l'utilisateur (obtenu par `xdg-user-dir`, donc juste quelle que soit la langue du poste) : c'est là que GIMP exporte et là que l'installation dépose les mires de test. Puis validation **C3-A** (PNG ? dimensions ?). Invalide → message (E-C3-1/2/3), pas d'aperçu, bouton inactif. Valide → aperçu affiché, bouton actif.
- **Clic « Imprimer »** → **C3**, répété autant de fois que le nombre d'exemplaires choisi → message de résultat. **Journaliser** dans tous les cas.
- **L'impression tourne dans un fil d'exécution séparé.** Sans cela, la boucle occuperait Tkinter du premier au dernier exemplaire : la fenêtre serait gelée et le bouton « Annuler » — précisément celui dont on a besoin — impossible à cliquer. Le fil ne touche jamais aux widgets directement : il passe ses messages par `after(0, …)`, qui les fait exécuter par le fil de l'interface.
- **Clic « Annuler »** → lève un « interrupteur » (`threading.Event`) que le fil consulte **avant chaque exemplaire**. Ce qui est annulé, ce sont les exemplaires **restants** : l'étiquette déjà envoyée sortira, la machine ayant les données. Le message le dit, plutôt que de laisser croire à un arrêt immédiat. Bilan annoncé et journalisé : « 2 étiquette(s) imprimée(s) sur 5 demandée(s) ».
- Dialogues de succès/erreur : **fenêtres-message écrites pour l'appli**, contenu piloté par le **catalogue d'erreurs**. Celles de Tkinter (`messagebox`) ont été écartées : sous Linux, elles figent leur largeur de coupe à leur création, si bien qu'avec des polices agrandies un message d'une ligne se retrouve coupé en trois — et que les élargir à la main n'y change rien. Les nôtres calculent cette largeur depuis la taille du texte, gardent la police de l'appli, et ne sont pas redimensionnables (il n'y avait rien à y gagner).

---

## 5. Programme B — agent de détection

Petit programme tournant en fond dans la session, **consommateur du cœur (C1)**.

- Se lance tout seul à l'ouverture de session (*autostart*).
- Surveille les branchements/débranchements USB (`pyudev`).
- À l'apparition de la QL-570 → **pop-up** « QL-570 détectée ».
- N'imprime **jamais**.

---

## 6. Chantiers & questions ouvertes

*Liste vivante des angles morts, par ordre d'importance. À refermer au fil des phases.*

- **Documentation wiki (Les Portes Logiques)** *(à boucler)* : page « Utiliser l'application Stickeuse-QL570 » — **raconter l'usage et renvoyer au dépôt** (source de vérité technique), sans dupliquer les instructions d'install. À aligner : le spec d'image affiché côté wiki doit indiquer le `413×991` de l'appli ; ajouter le lien vers `github.com/lesporteslogiques/stickeuse`.
- **Cohabitation A/B** *(ouvert)* : que fait concrètement la pop-up de B (notifier seulement, ou proposer d'ouvrir A) ? Éviter une pop-up redondante si A est déjà ouverte.
- **Débranchement à chaud** *(ouvert)* : pendant que A est ouverte (détectée au lancement, partie avant l'impression).
- **Mineurs** : plusieurs imprimantes Brother branchées (C1 prend la première — simplification assumée) ; examiner `template_paysage.png` (vestige de l'ancienne « Stickeuse ») ; maquettes dédiées des dialogues succès/erreur si besoin ; enrichir les lignes de journal avec les champs structurés (*famille · où · niveau*) du spec, et envisager une rotation des logs.

**Refermés**

- **Module cœur (C1 + C2 + C3)** → codé, commenté, testé sur matériel (impression réelle sur OP42 ; détection portable sur OP52). `src/coeur.py`.
- **Journalisation** → codée (`src/journal.py`), un log par poste dans `~/.ql570/`.
- **Catalogue d'erreurs** → structure d'accueil + entrées E-C2-* / E-C3-* (dont `E-C3-6`, découverte en codant).
- **Programme A — interface d'impression** → codé (`src/programme_a.py`) : deux écrans, fenêtre proportionnelle à l'écran, aperçu, impression en fil séparé avec annulation des exemplaires restants, vérification de GIMP à l'accueil.
- **Programme B — agent de détection** → codé (`src/programme_b.py`) : autostart, notification au branchement, arrêt propre au Ctrl-C.
- **Installation / déploiement** → `install.sh` / `uninstall.sh` écrits et éprouvés sur postes réels (Debian 12 et 13) : venv sous `/opt/ql570/`, règle udev, groupe `lp`, autostart de B, entrée de menu, mires de test posées dans `/opt/ql570/` et dans le dossier « Images » de l'utilisateur.
- **Localisation de `brother_ql`** → déduite du venv (`sys.prefix`) et non cherchée sur le PATH. Le défaut, resté latent deux déploiements durant (une copie système traînait dans le PATH), a été isolé puis corrigé ; `E-C3-6` n'a plus qu'une seule cause possible.
- **Mires de test** → quatre fichiers `src/test-stickeuse-<référence>-<orientation>.png`, un par rouleau et par orientation, et leur générateur `test/generer-mire.py`, qui documente les formats en code. Le nom de fichier commence par `test-` et non `mire-` : « mire » est un mot de métier, illisible pour qui ouvre « Parcourir… » sans connaître l'imprimerie. Le mot reste en revanche **sur l'étiquette imprimée**, où le contexte le rend clair. Chaque mire porte sa **référence de rouleau** imprimée (`DK-11208`, `DK-11202`) : sans elle, deux mires posées côte à côte sur la table sont impossibles à distinguer. La **désinstallation ne connaît aucun de ces noms** : elle relève ce que l'installation a posé dans `/opt/ql570/` avant de l'effacer, et retire exactement cela du dossier « Images ». Une liste écrite dans les deux scripts finirait par diverger — on ajoute un rouleau d'un côté, on l'oublie de l'autre, et un fichier orphelin reste chez l'utilisateur. Le même défaut, sous une autre forme, a déjà coûté une installation silencieusement incomplète : un nom de mire écrit hors de la liste, oublié lors d'un renommage.

Le **nom de fichier** porte en plus les dimensions en pixels — `test-stickeuse-DK11208-413x991px-portrait.png` — parce que la fenêtre « Parcourir… » de Tk n'affiche que ce nom : ni colonne de description, ni infobulle, et rien ne permet d'en ajouter. Deux références qui ne diffèrent que d'un chiffre ne disent rien à qui n'est pas du métier. Réglette de 30 mm, damier de 8 px, traits de 1 à 5 px, aplat noir, échelle de lisibilité, repères d'angle, mention « BAS DE L'ÉTIQUETTE ».
- **Version-control / GitHub** → dépôt public `lesporteslogiques/stickeuse` en place : README, `.gitignore` (logs, `__pycache__`, venv), LICENSE, docs ; cœur + journal poussés. Source de vérité = le dépôt ; le wiki raconte et renvoie.
- *Nombre d'exemplaires* → spécifié (Programme A).
- *Cliquer « Imprimer » sans fichier* → bouton désactivé tant qu'aucun fichier valide.
- *Étiquette ≠ rouleau chargé* → réglé autrement depuis l'ajout du second rouleau : ce n'est plus le mono-format qui protège, mais la **déclaration explicite** à l'accueil, dont découlent les dimensions acceptées.
- *Aperçu* → écarté pour la v1.
- *Choix du format d'étiquette* → **rouvert puis traité** : deux rouleaux prédécoupés au catalogue, déclarés à l'accueil. La décision initiale (mono-format, constante de config) tenait tant que le FabLab n'avait qu'un rouleau.

---

## Statut

- **Module cœur (C1 + C2 + C3)** : **codé et validé sur matériel**. `src/coeur.py`. Impression réelle confirmée sur plusieurs postes ; détection portable confirmée sous Debian 12 et 13.
- **Journalisation** : **codée**. `src/journal.py` — un log par poste dans `~/.ql570/ql570-<hostname>.log`.
- **Catalogue d'erreurs** : structure + entrées E-C2-* / E-C3-* (dont `E-C3-6`, dont la cause a été ramenée à une seule).
- **Programme A** : **codé et utilisé** (`src/programme_a.py`) — fenêtre proportionnelle, aperçu, exemplaires multiples, annulation, vérification de GIMP.
- **Programme B** : **codé** (`src/programme_b.py`) — agent de détection en autostart.
- **Installation** : `install.sh` / `uninstall.sh` **éprouvés** sur postes réels, symétriques.
- **Dépôt** : `github.com/lesporteslogiques/stickeuse` (public) — code, mires de test et documentation.
- **Chantiers ouverts** : documentation du wiki, cohabitation A/B, débranchement à chaud, enrichissement des lignes de journal.
- **Projet** : Stickeuse QL-570 — Vitally LUBIN / Les Portes Logiques — code **AGPL-3.0**, docs **CC BY**.
