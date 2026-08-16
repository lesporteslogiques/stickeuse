# Stickeuse QL-570

Application pour piloter l'imprimante d'étiquettes **Brother QL-570** depuis un poste Debian, utilisable sans compétence technique. Développée pour le FabLab **Les Portes Logiques** (Quimper).

> **Statut : opérationnelle.** Module cœur, journalisation, application d'impression et agent de détection sont codés et validés sur matériel. Les scripts `install.sh` / `uninstall.sh` ont été éprouvés lors de déploiements complets, sous Debian 12 et Debian 13.

## Ce que fait l'appli

- Détecte automatiquement l'imprimante branchée (port et modèle) — rien n'est codé en dur.
- Imprime une étiquette à partir d'une **image PNG** préparée par l'utilisateur dans GIMP.
- Gère **deux rouleaux** : DK-11208 (38 × 90 mm) et DK-11202 (62 × 100 mm), déclarés à l'accueil — la QL-570 ne sait pas dire lequel est chargé. Un rouleau peut être déclaré temporairement **indisponible** : il apparaît grisé, avec le motif, au lieu d'être masqué.
- Imprime plusieurs exemplaires d'affilée, avec possibilité d'**annuler** ceux qui restent.
- Signale, au branchement, qu'une QL-570 est disponible (agent en fond, notification de bureau).
- Fournit des **mires de test** (`src/test-stickeuse-*.png`, une par rouleau et par orientation ; chacune porte sa référence imprimée), copiées dans le dossier « Images » de l'utilisateur à l'installation : elles vérifient d'un seul tirage la densité, la finesse de trait, l'échelle et l'orientation.
- Signale à l'accueil si **GIMP** manque sur le poste (sans bloquer : l'appli imprime tout PNG conforme, d'où qu'il vienne).

L'image elle-même se fabrique dans **GIMP** (voir [`docs/prise-en-main-gimp.md`](docs/prise-en-main-gimp.md)) : l'appli ne crée pas l'image, elle l'imprime.

## Architecture (résumé)

Trois piliers, détaillés dans [`docs/algorithme-appli-QL570.md`](docs/algorithme-appli-QL570.md) :

- **Module cœur** ([`src/coeur.py`](src/coeur.py)) — le moteur (détection, accès, impression), testable en ligne de commande.
- **Transversaux** — catalogue d'erreurs et journalisation ([`src/journal.py`](src/journal.py), un log par poste).
- **Deux programmes** — l'application d'impression ([`src/programme_a.py`](src/programme_a.py), fenêtre) et l'agent de détection ([`src/programme_b.py`](src/programme_b.py), pop-up), qui partagent le cœur sans communiquer entre eux.

## Documentation

- [`docs/notes-techniques-QL570.md`](docs/notes-techniques-QL570.md) — le contexte matériel vérifié.
- [`docs/algorithme-appli-QL570.md`](docs/algorithme-appli-QL570.md) — l'organisation et les algorithmes.
- [`docs/prise-en-main-gimp.md`](docs/prise-en-main-gimp.md) — comment fabriquer l'image de l'étiquette.
- **Guide d'usage** (côté utilisateur), sur le wiki : <https://lesporteslogiques.net/wiki/materiel/logicos/guideql570>.
- Le **récit de construction** est tenu sur le wiki des Portes Logiques (le dépôt reste la source de vérité technique).

## Dépendances

Tout est posé par `install.sh` (voir [Installation](#installation)) : rien à installer à la main. Pour mémoire :

- **apt (système), essentielles** : `python3-tk` (interface Tkinter), `python3-venv` (pour créer l'environnement virtuel), `libusb-1.0-0` (voie de repli pyusb), `xdg-user-dirs` (pour localiser le Bureau).
- **apt (système), optionnelles** : `libnotify-bin` — uniquement la notification de l'agent ; sans elle, l'appli se dégrade en douceur (l'agent écrit dans le journal). `gimp` — pour *fabriquer* les images d'étiquettes sur le poste ; sans lui, l'appli imprime toujours, et le signale à l'accueil.
- **pip (dans l'environnement virtuel)** : `brother_ql`, `pyudev`, `pyusb`.
- **Accès au périphérique** : appartenance au groupe `lp` + règle udev (posées à l'installation).

## Installation

> À faire **une fois par machine**. Il faut pouvoir administrer la machine :
> soit votre compte est autorisé à utiliser `sudo`, soit vous connaissez le
> mot de passe de **root** (le compte administrateur de Linux). Debian 12 ou
> 13, connexion internet requise. L'imprimante n'a pas besoin d'être
> branchée.

> **Comment lire cette procédure**
> Les blocs sur fond gris sont des commandes à taper — ou à copier-coller
> depuis cette page — dans le terminal, **une ligne à la fois**, en
> validant chacune par la touche `Entrée`. Pour coller dans un terminal,
> le raccourci est `Ctrl` + `Maj` + `V` (et non `Ctrl` + `V`).
> Chaque fois qu'un mot de passe est demandé, **rien ne s'affiche pendant
> que vous le tapez** — ni points, ni étoiles. C'est normal : tapez-le
> jusqu'au bout et validez par `Entrée`.

**1. Ouvrez un terminal**

Menu Applications → Terminal, ou les touches `Ctrl` + `Alt` + `T`.
Une fenêtre s'ouvre, avec une ligne de texte et un curseur qui clignote :
c'est là que tout se tape.

**2. Relevez le nom de votre compte**

Tapez (ou copiez-collez) la commande ci-dessous, puis appuyez sur
`Entrée` :

```bash
whoami
```

La commande affiche un mot : le nom du compte sur lequel vous êtes
connecté·e (par exemple `vitally`). Notez-le, il resservira.
Dans la suite, il est écrit `<login>` : partout où vous voyez `<login>`,
tapez ce mot à la place (sans les chevrons).

> Cette procédure suppose que vous installez l'appli **pour vous-même**.
> Si vous l'installez pour quelqu'un d'autre sur son ordinateur, c'est
> **son** nom de compte qu'il faut utiliser, pas le vôtre.

**3. Récupérez l'application**

Tapez (ou copiez-collez) la commande ci-dessous, puis appuyez sur
`Entrée` :

```bash
cd ~
```

`cd` veut dire *change directory* (« change de dossier ») et `~` désigne
votre dossier personnel : cette ligne vous y ramène, quel que soit
l'endroit où vous vous trouviez. Tapez ensuite (ou copiez-collez) la
commande ci-dessous — elle tient sur une seule ligne — et appuyez sur
`Entrée` :

```bash
git clone https://github.com/lesporteslogiques/stickeuse.git
```

Cette commande télécharge l'application. Un dossier `stickeuse` apparaît
dans votre dossier personnel, à l'emplacement `/home/<login>/stickeuse` —
que le terminal note aussi, en raccourci, `~/stickeuse`.

> L'adresse peut aussi se copier depuis la page du dépôt : bouton vert
> **`< > Code`** → onglet **HTTPS** → icône 📋.

⚠️ **Ne supprimez jamais ce dossier** : `uninstall.sh`, qui sert à
désinstaller l'appli, s'y trouve et n'est recopié nulle part ailleurs.

**4. Repérez par quelle voie vous pouvez administrer la machine**

Tapez (ou copiez-collez) la commande ci-dessous, puis appuyez sur
`Entrée` :

```bash
sudo -v
```

Cette commande ne fait rien d'autre que vérifier vos droits. Trois
réponses possibles :

- **Votre mot de passe de session est demandé et accepté** (ou rien n'est
  demandé du tout), et aucun message d'erreur n'apparaît → suivez la
  **voie A** à l'étape 5.
- **`<login> n'est pas dans le fichier sudoers`** : votre compte n'a pas
  le droit d'administrer la machine par `sudo`. C'est le cas des postes du
  FabLab. Tapez (ou copiez-collez) alors la commande ci-dessous,
  suivie d'`Entrée` :

  ```bash
  su -
  ```

  Le mot de passe demandé est celui de **root**, pas le vôtre. S'il est
  accepté, la ligne devant le curseur change et se termine par `#` : vous
  êtes administrateur. Tapez alors, toujours suivi d'`Entrée` :

  ```bash
  exit
  ```

  pour revenir à votre compte, et suivez la **voie B** à l'étape 5.
- **`su : échec d'authentification`** alors que vous êtes sûr·e du mot de
  passe, ou aucun mot de passe root connu : le compte root est verrouillé
  (cas d'une Debian installée sans mot de passe root). **L'installation
  n'est pas possible sur cette machine** : adressez-vous à la personne qui
  l'administre.

**5. Lancez l'installation**

*Voie A* — tapez (ou copiez-collez) ces deux lignes l'une après l'autre,
en appuyant sur `Entrée` après chacune :

```bash
cd ~/stickeuse
sudo ./install.sh
```

*Voie B* — tapez (ou copiez-collez) ces quatre lignes l'une après l'autre,
en appuyant sur `Entrée` après chacune, et en remplaçant `<login>` par le
nom relevé à l'étape 2 :

```bash
su -
cd /home/<login>/stickeuse
./install.sh <login>
exit
```

Dans les deux cas, comptez une à deux minutes. L'installation est terminée
quand le curseur clignotant réapparaît, prêt à recevoir une nouvelle
commande.

> **Pourquoi la voie B est-elle plus compliquée ?** Le tiret après `su`
> ouvre une session complète d'administrateur, dont le `PATH` (la liste des
> dossiers où le système cherche les commandes) contient les dossiers
> `sbin`, où vivent `usermod` et `udevadm` dont l'installeur a besoin.
> Ensuite, `sudo` transmet automatiquement votre nom de compte au script,
> alors que `su` ne le fait pas : d'où `<login>` écrit à la main. Enfin,
> root n'habite pas dans votre dossier personnel, ce qui oblige à écrire le
> chemin en entier. Le `exit` de la dernière ligne referme la session
> d'administrateur : on ne reste jamais root plus longtemps que nécessaire.

**6. Fermez la session, puis rouvrez-la**

Indispensable : sans cela, le droit d'accès à l'imprimante n'est pas actif
et l'agent de détection ne démarre pas.

Trois façons de faire, au choix :

- **par le menu de session** — cliquez sur votre nom ou sur l'icône
  d'alimentation (en haut à droite sous GNOME) → **Se déconnecter**. C'est
  la voie la plus sûre : vos applications vous proposent d'enregistrer
  avant de fermer ;
- **en redémarrant l'ordinateur**, par le même menu ; ou en tapant (ou
  copiant-collant) la commande ci-dessous dans le terminal, suivie
  d'`Entrée` :

  ```bash
  systemctl reboot
  ```

- **en forçant la déconnexion depuis le terminal**, si le menu est
  inaccessible. Tapez (ou copiez-collez) la commande ci-dessous, puis
  appuyez sur `Entrée` :

  ```bash
  loginctl terminate-user $(whoami)
  ```

  Attention : cette commande ferme tout immédiatement, sans rien
  enregistrer et sans demander confirmation. Fermez vos documents avant.

Dans les trois cas, l'écran de connexion réapparaît : **reconnectez-vous
avec le compte relevé à l'étape 2**. C'est cette reconnexion, et elle
seule, qui rend l'installation effective.

**7. Rouvrez un terminal et vérifiez**

La déconnexion a fermé le terminal : ouvrez-en un nouveau (`Ctrl` + `Alt`
+ `T`). Tapez (ou copiez-collez) la commande ci-dessous, puis appuyez sur
`Entrée` :

```bash
groups
```

La commande affiche la liste des groupes auxquels votre compte appartient.
**Le mot `lp` doit y figurer** — c'est lui qui donne le droit d'imprimer.
S'il est absent, la reconnexion de l'étape 6 n'a pas eu lieu.

Vérifiez ensuite, dans cet ordre :

- **Stickeuse QL-570** apparaît dans le menu des applications ;
- les **mires de test** (les images `test-stickeuse-*.png`) sont dans votre
  dossier « Images » ;
- au branchement de la QL-570, une notification s'affiche à l'écran ;
- l'impression d'une mire sort correctement.

### Ce que pose `install.sh`

- l'appli et son icône dans **`/opt/ql570/`** (même emplacement partout) ;
- les dépendances dans un environnement virtuel ;
- l'ajout du compte au groupe `lp` et la règle udev (`/etc/udev/rules.d/`) ;
- l'agent en autostart (`/etc/xdg/autostart/`) — **pour tous les comptes
  du poste** ;
- l'entrée de menu du programme d'impression ;
- les mires de test dans `/opt/ql570/` et dans le dossier « Images ».

### Si ça coince

- **`git : commande introuvable`** (étape 3) : le programme de
  téléchargement n'est pas installé sur la machine. Installez-le avec
  `sudo apt install git` (voie A), ou `apt install git` après `su -`
  (voie B), puis reprenez à l'étape 3.
- **`bash: ./install.sh: Permission denied`** (étape 5) : le fichier a
  perdu son droit d'exécution. Tapez (ou copiez-collez) ces deux lignes
  l'une après l'autre, en appuyant sur `Entrée` après chacune :

  ```bash
  cd ~/stickeuse
  chmod +x install.sh uninstall.sh
  ```

  puis reprenez l'étape 5.
- **Rien ne se colle** avec `Ctrl` + `V` : dans un terminal, c'est
  `Ctrl` + `Maj` + `V`.
- **`lp` n'apparaît pas** dans le résultat de `groups` (étape 7) : la
  déconnexion/reconnexion de l'étape 6 n'a pas eu lieu, ou vous vous êtes
  reconnecté·e sur un autre compte que celui relevé à l'étape 2.
- **Pas de notification au branchement de l'imprimante** : le paquet
  `libnotify-bin` est peut-être absent. L'appli fonctionne quand même ;
  l'agent note alors les branchements dans son journal, dans le dossier
  `~/.ql570/`.
- **Erreur d'accès à l'imprimante au moment d'imprimer** : l'étape 6 n'a
  pas été faite.

## Désinstallation

Ouvrez un terminal. Les commandes ci-dessous supposent que le dossier
téléchargé lors de l'installation est toujours à sa place
(`~/stickeuse` par défaut).

*Voie A*, si votre compte peut utiliser `sudo` — tapez (ou copiez-collez)
ces deux lignes l'une après l'autre, en appuyant sur `Entrée` après
chacune :

```bash
cd ~/stickeuse
sudo ./uninstall.sh
```

*Voie B*, avec le mot de passe root — tapez (ou copiez-collez) ces quatre
lignes l'une après l'autre, en appuyant sur `Entrée` après chacune, et en
remplaçant `<login>` par le nom du compte qui utilisait l'appli :

```bash
su -
cd /home/<login>/stickeuse
./uninstall.sh <login>
exit
```

Restent volontairement en place : le compte dans le groupe `lp` (partagé
avec d'autres usages), les paquets système (utilisés ailleurs), les
journaux (effacés seulement sur confirmation).

## Licences

- **Code** : GNU Affero General Public License v3 (AGPL-3.0) — voir [`LICENSE`](LICENSE).
- **Documentation du dépôt** : Creative Commons Attribution (CC BY).
- **Wiki** : Creative Commons Attribution - Partage dans les mêmes conditions (CC BY-SA 4.0), licence par défaut du wiki Les Portes Logiques.

## Auteurice

Conçue et développée par **Vitally LUBIN** en 2026.

## Liens

- Wiki Les Portes Logiques : <https://lesporteslogiques.net/wiki/materiel/imprimante_thermique_brother_ql-570>
- Dépôt : <https://github.com/lesporteslogiques/stickeuse>
