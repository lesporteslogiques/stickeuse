#!/usr/bin/env bash
#
# install.sh — installation de « Stickeuse QL-570 » sur un poste Debian.
#
# À LANCER EN ROOT, une seule fois par machine, par le ou la responsable.
# Comme les comptes utilisateurs ne sont pas sudoers, on devient root par
# « su - » (session de login : le PATH contient alors les dossiers « sbin »).
#
# Usage :
#     su -                       # devenir root (mot de passe root)
#     ./install.sh <login>       # <login> = le compte qui utilisera l'appli
#
# Si l'on est passé par « sudo » (machine où c'est possible), <login> peut être
# omis : on retombe alors sur $SUDO_USER.
#
# Pour défaire l'installation : uninstall.sh (symétrique).

# ── Garde-fous shell ────────────────────────────────────────────────────────
# set -e        : on s'arrête à la première commande qui échoue.
# set -u        : utiliser une variable non définie est une erreur (anti-typo).
# set -o pipefail : dans « a | b », l'échec de a (pas seulement de b) compte.
set -euo pipefail

# On ne dépend PAS du PATH de l'appelant : on ajoute nous-mêmes les dossiers
# « sbin » où vivent usermod, udevadm, runuser… Ainsi le script marche qu'on
# soit arrivé par « su - » OU par « su -c "…" » (le piège classique du PATH).
export PATH="/usr/local/sbin:/usr/sbin:/sbin:$PATH"

# ── Petits messages lisibles ────────────────────────────────────────────────
# Trois fonctions pour parler à l'humain. « erreur » arrête le script (exit 1).
info()   { printf '  [info] %s\n' "$*"; }
avert()  { printf '  [!]    %s\n' "$*" >&2; }   # >&2 : sur la sortie d'erreur
erreur() { printf '  [STOP] %s\n' "$*" >&2; exit 1; }

# ── Constantes de déploiement ───────────────────────────────────────────────
# Ce sont des chemins d'INSTALLATION (documentés, identiques sur chaque poste),
# PAS des valeurs matérielles : la règle « rien en dur » vise le port/modèle de
# l'imprimante (qui se découvrent), pas l'emplacement où l'on pose l'appli.
APP_DIR="/opt/ql570"                 # toute l'appli vit ici
VENV="$APP_DIR/venv"                 # l'environnement virtuel Python (isolé du système)
PY="$VENV/bin/python"                # l'interpréteur DE ce venv (pas celui du système)
REGLE_UDEV="/etc/udev/rules.d/99-ql570.rules"
AUTOSTART="/etc/xdg/autostart/ql570-agent.desktop"
FICHIERS_PY="coeur.py journal.py programme_a.py programme_b.py"

# Identité USB de la QL-570 (les mêmes codes que dans coeur.py). Sert à écrire
# la règle udev. Ce ne sont pas des valeurs « en dur dans l'appli » mais la
# description matérielle figée de CE modèle (04f9 = Brother, 2028 = QL-570).
ID_VENDOR="04f9"
ID_PRODUCT="2028"

# ── 0. Vérifications préalables ──────────────────────────────────────────────
# Être root : « id -u » vaut 0 pour root.
[ "$(id -u)" -eq 0 ] || erreur "À lancer en root (ex. « su - » puis ./install.sh <login>)."

# Quel utilisateur ? L'argument $1 d'abord ; sinon $SUDO_USER (rempli par sudo,
# mais VIDE après « su - ») ; sinon on ne devine pas, on demande.
TARGET_USER="${1:-${SUDO_USER:-}}"
[ -n "$TARGET_USER" ] || erreur "Préciser le compte : ./install.sh <login>"
# Le compte existe-t-il vraiment ? (« id » échoue sinon.)
id "$TARGET_USER" >/dev/null 2>&1 || erreur "Compte introuvable : $TARGET_USER"
# Son dossier personnel (6ᵉ champ de la ligne passwd) et son groupe principal.
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
TARGET_GROUP="$(id -gn "$TARGET_USER")"
info "Installation pour le compte : $TARGET_USER (home : $TARGET_HOME)"

# Où sont les sources à installer ? À côté de ce script : soit dans src/, soit
# directement à côté. On ne code pas un chemin en dur : on cherche.
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
if   [ -f "$SCRIPT_DIR/src/coeur.py" ]; then SRC_DIR="$SCRIPT_DIR/src"
elif [ -f "$SCRIPT_DIR/coeur.py" ];     then SRC_DIR="$SCRIPT_DIR"
else erreur "Sources .py introuvables près de $SCRIPT_DIR (ni ./src/ ni ./)."
fi
info "Sources : $SRC_DIR"

# ── a. Dépendances système (apt) ─────────────────────────────────────────────
# DEBIAN_FRONTEND=noninteractive : pas de question bloquante pendant l'install.
export DEBIAN_FRONTEND=noninteractive
info "apt : mise à jour de l'index…"
apt-get update -qq || avert "apt-get update a échoué (on tente quand même l'install)."

# ESSENTIELLES — sans elles l'appli ne tourne pas :
#   python3-tk     : l'interface graphique (Tkinter) du Programme A
#   python3-venv   : nécessaire pour CRÉER l'environnement virtuel ci-dessous
#   libusb-1.0-0   : la bibliothèque système que pyusb utilise (voie de repli)
#   xdg-user-dirs  : fournit « xdg-user-dir », qui dit où est le dossier
#                    « Images » de l'utilisateur, quelle que soit la langue du poste
info "apt : dépendances essentielles…"
apt-get install -y python3-tk python3-venv libusb-1.0-0 xdg-user-dirs \
    || erreur "Échec d'installation des dépendances essentielles (apt)."

# OPTIONNELLE — « au mieux » : seulement la pop-up de l'agent. Sans elle,
# l'appli se dégrade en douceur (l'agent écrit dans le journal au lieu d'une
# notification). On n'ARRÊTE donc PAS si elle manque.
info "apt : libnotify-bin (optionnel)…"
apt-get install -y libnotify-bin \
    || avert "libnotify-bin non installé : pas de pop-up, le reste fonctionne."

# OPTIONNELLE — GIMP : ce n'est pas une dépendance de l'appli (qui imprime un
# PNG, d'où qu'il vienne), mais l'outil avec lequel l'utilisateur FABRIQUE son
# image. On le pose ici parce que l'installation est le seul moment où quelqu'un
# a les droits root ; sans lui, l'appli le signale à l'accueil et fonctionne.
info "apt : gimp (optionnel, pour fabriquer les images)…"
apt-get install -y gimp \
    || avert "gimp non installé : l'appli imprimera, mais l'utilisateur ne pourra pas fabriquer d'image ici."

# ── b. Environnement virtuel + paquets pip ───────────────────────────────────
mkdir -p "$APP_DIR"
# Un « venv » est un Python isolé : ses paquets n'interfèrent pas avec ceux du
# système. On le crée une fois ; s'il existe déjà, on ne recommence pas.
if [ ! -d "$VENV" ]; then
    info "Création de l'environnement virtuel : $VENV"
    python3 -m venv "$VENV"
else
    info "Environnement virtuel déjà présent : $VENV"
fi

# brother_ql : pilote d'impression ; pyudev : lecture des branchements USB ;
# pyusb : voie de repli directe sur le bus (importée par coeur.py). pyusb vient
# normalement avec brother_ql, mais on l'installe explicitement pour ne pas
# dépendre de cette transitivité.
info "pip : brother_ql, pyudev, pyusb (dans le venv)…"
"$VENV/bin/pip" install --upgrade pip >/dev/null \
    || avert "Mise à jour de pip ignorée (sans gravité)."
"$VENV/bin/pip" install brother_ql pyudev pyusb \
    || erreur "Échec d'installation des paquets Python (pip)."

# ── c. Poser les 4 .py dans /opt/ql570/ ──────────────────────────────────────
info "Copie des programmes dans $APP_DIR"
for f in $FICHIERS_PY; do
    [ -f "$SRC_DIR/$f" ] || erreur "Fichier source manquant : $SRC_DIR/$f"
    install -m 0644 "$SRC_DIR/$f" "$APP_DIR/$f"   # « install » : copie + pose les droits
done

# Icône de l'appli (facultative). Si le PNG est fourni à côté des sources, on
# l'installe dans /opt/ql570/ et les .desktop pointeront dessus (chemin absolu).
# Sinon, dégradation douce : on retombe sur l'icône générique « printer » du
# thème. ICON_REF porte la référence à mettre dans les .desktop, ci-dessous.
ICONE_SRC="$SRC_DIR/stickeuseql570.png"
ICONE_DST="$APP_DIR/stickeuseql570.png"
if [ -f "$ICONE_SRC" ]; then
    install -m 0644 "$ICONE_SRC" "$ICONE_DST"
    ICON_REF="$ICONE_DST"
    info "Icône installée : $ICONE_DST"
else
    ICON_REF="printer"
    avert "Icône stickeuseql570.png absente des sources : repli sur l'icône générique « printer »."
fi

# ── c bis. Mires de test ─────────────────────────────────────────────────────
# Images de contrôle aux formats imposés, en noir et blanc pur, 300 ppp : une
# par rouleau ET par orientation. Elles vérifient, juste après l'installation,
# que toute la chaîne imprime correctement — densité, finesse de trait, échelle,
# alignement, orientation. Regénérables par test/generer-mire.py ; absentes des
# sources, on continue sans elles.
#
# On les pose à DEUX endroits, pour deux usages distincts :
#   - dans /opt/ql570/ : les exemplaires de référence, qui suivent l'appli ;
#   - dans le dossier « Images » de l'utilisateur : là où « Parcourir… » ouvre,
#     donc là où la personne les trouvera sans rien chercher. Le nom commence par « test- » et
# non par « mire- » : dans la fenêtre « Parcourir… », il faut que quelqu'un
# qui n'est pas du métier comprenne à quoi sert ce fichier. Le nom porte
# aussi la référence du rouleau et les dimensions en pixels : la fenêtre
# « Parcourir… » de Tk n'affiche QUE le nom du fichier — pas de colonne de
# description, pas d'infobulle, et rien ne permet d'en ajouter.
MIRES="test-stickeuse-DK11208-413x991px-portrait.png test-stickeuse-DK11208-991x413px-paysage.png test-stickeuse-DK11202-696x1109px-portrait.png test-stickeuse-DK11202-1109x696px-paysage.png"
# Y a-t-il au moins une mire à installer ? On interroge la LISTE, jamais un nom
# écrit à part : un nom en double, c'est un renommage à moitié fait qui attend.
MIRE_TROUVEE="non"
for mire in $MIRES; do
    [ -f "$SRC_DIR/$mire" ] && MIRE_TROUVEE="oui"
done

if [ "$MIRE_TROUVEE" = "oui" ]; then
    for mire in $MIRES; do
        [ -f "$SRC_DIR/$mire" ] || continue          # chaque mire est facultative
        install -m 0644 "$SRC_DIR/$mire" "$APP_DIR/$mire"
        info "Mire de test installée : $APP_DIR/$mire"
    done

    # Où est le dossier « Images » de CET utilisateur ? Il s'appelle Images,
    # Pictures, Bilder… selon la langue du poste : on demande à xdg-user-dir au
    # lieu de deviner. « runuser » exécute la commande EN TANT QUE l'utilisateur
    # (nous sommes root) : sans cela, on lirait les dossiers de root.
    DOSSIER_IMAGES="$(runuser -l "$TARGET_USER" -c 'xdg-user-dir PICTURES' 2>/dev/null || true)"
    # Repli : si xdg-user-dir est absent ou renvoie le home lui-même, on crée
    # un dossier Images plutôt que de déposer le fichier en vrac dans le home.
    if [ -z "$DOSSIER_IMAGES" ] || [ "$DOSSIER_IMAGES" = "$TARGET_HOME" ]; then
        DOSSIER_IMAGES="$TARGET_HOME/Images"
    fi
    # On ne s'approprie QUE ce qu'on crée : si le dossier existait déjà, il
    # appartient à l'utilisateur et on n'a rien à y changer.
    if [ ! -d "$DOSSIER_IMAGES" ]; then
        mkdir -p "$DOSSIER_IMAGES"
        chown "$TARGET_USER:$TARGET_GROUP" "$DOSSIER_IMAGES"
    fi
    for mire in $MIRES; do
        [ -f "$SRC_DIR/$mire" ] || continue
        install -m 0644 "$SRC_DIR/$mire" "$DOSSIER_IMAGES/$mire"
        # Le script tourne en root : sans ce chown, le fichier déposé chez
        # l'utilisateur ne lui appartiendrait pas (lisible, mais pas gérable).
        chown "$TARGET_USER:$TARGET_GROUP" "$DOSSIER_IMAGES/$mire"
        info "Mire copiée pour $TARGET_USER : $DOSSIER_IMAGES/$mire"
    done
else
    avert "Aucune mire de test dans les sources : installation sans image de contrôle."
fi

# ── d. Droit d'accès à l'imprimante : groupe « lp » ──────────────────────────
# Ajouter l'utilisateur au groupe « lp » lui donne le droit d'écrire sur le nœud
# /dev/usb/lpX (voie principale). -a = AJOUTER sans retirer des autres groupes ;
# commande sans effet s'il est déjà membre.
info "Ajout de $TARGET_USER au groupe « lp »"
usermod -aG lp "$TARGET_USER"

# ── e. Règle udev (voie de repli pyusb) ──────────────────────────────────────
# Le nœud /dev/usb/lpX est déjà au groupe lp par défaut (règle Debian d'usblp) :
# la voie principale est donc déjà couverte par l'étape d. Cette règle-ci sert à
# la VOIE DE REPLI (pyusb/libusb), qui parle au périphérique USB brut : on lui
# met le groupe lp + droits lecture/écriture, pour le même compte, sans root.
info "Pose de la règle udev : $REGLE_UDEV"
cat > "$REGLE_UDEV" <<EOF
# Stickeuse QL-570 — accès au périphérique USB brut pour la voie de repli pyusb.
# Donne au groupe « lp » le droit d'ouvrir l'imprimante via libusb (sans root).
SUBSYSTEM=="usb", ATTR{idVendor}=="$ID_VENDOR", ATTR{idProduct}=="$ID_PRODUCT", MODE="0660", GROUP="lp"
EOF
# Recharger les règles, puis les appliquer aux périphériques déjà branchés.
udevadm control --reload-rules
udevadm trigger || avert "udevadm trigger a renvoyé une erreur (sans gravité ici)."

# ── f. Autostart de l'agent (Programme B) ────────────────────────────────────
# Un fichier .desktop dans /etc/xdg/autostart/ est lancé à l'ouverture de CHAQUE
# session graphique. L'Exec pointe le python DU VENV (pas celui du système) pour
# disposer de pyudev.
info "Pose de l'autostart de l'agent : $AUTOSTART"
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=Agent Stickeuse QL-570
Comment=Signale le branchement de l'imprimante QL-570
Exec=$PY $APP_DIR/programme_b.py
Icon=$ICON_REF
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

# ── g. Entrée dans le menu des applications (Programme A) ────────────────────
# /usr/share/applications/ est le dossier système que lit le menu « Afficher les
# applications ». Un .desktop posé là apparaît pour TOUS les comptes du poste,
# sans manipulation côté utilisateur (pas de « autoriser le lancement » comme sur
# le Bureau). C'est l'emplacement standard et le plus robuste pour un lanceur.
#
# Trois choix dans le contenu ci-dessous :
#   - PAS de « Categories= » : sur GNOME, une catégorie (Utility, System…) fait
#     ranger l'application dans un SOUS-DOSSIER de la grille (« Utilitaires »…),
#     où personne ne pense à aller la chercher — elle n'apparaissait plus qu'à
#     la recherche. Sans catégorie, elle reste à la racine, visible.
#   - « Keywords » enrichit la recherche : taper « étiquette » ou « brother »
#     suffit à la trouver.
#   - « StartupWMClass » fait le lien entre la FENÊTRE ouverte et cette entrée
#     de menu : sans lui, le dock afficherait l'appli en cours comme une fenêtre
#     anonyme, avec une icône générique. Sa valeur doit être exactement celle du
#     tk.Tk(className=…) de programme_a.py. Attention à la graphie : Tk met une
#     majuscule à la première lettre ET passe le reste en minuscules, d'où
#     « Stickeuse-ql570 » et non « Stickeuse-QL570 ». Valeur vérifiée sur une
#     fenêtre ouverte avec « xprop WM_CLASS ».
LANCEUR="/usr/share/applications/stickeuse-ql570.desktop"

# Une version précédente avait-elle déclaré une catégorie ? On le regarde AVANT
# d'écraser le fichier : c'est le seul cas qui obligera à toucher au rangement
# de la grille (étape h). Sur une machine neuve, ou déjà à jour, la réponse est
# non — et on ne touchera à rien.
ANCIENNE_CATEGORIE="non"
if [ -f "$LANCEUR" ] && grep -q "^Categories=" "$LANCEUR"; then
    ANCIENNE_CATEGORIE="oui"
fi

info "Pose de l'entrée de menu : $LANCEUR"
cat > "$LANCEUR" <<EOF
[Desktop Entry]
Type=Application
Name=Stickeuse QL-570
Comment=Imprimer une étiquette sur la Brother QL-570
Exec=$PY $APP_DIR/programme_a.py
Icon=$ICON_REF
Terminal=false
Keywords=etiquette;label;imprimante;brother;stickeuse;QL570;
StartupWMClass=Stickeuse-ql570
EOF
chmod 0644 "$LANCEUR"   # lisible par tous ; un .desktop de menu n'a pas besoin d'être exécutable
# Rafraîchir la base des applications pour que l'entrée apparaisse sans attendre.
# update-desktop-database peut être absent selon le poste → « au mieux ».
update-desktop-database /usr/share/applications 2>/dev/null \
    || avert "update-desktop-database indisponible : l'entrée apparaîtra au prochain rafraîchissement du menu (ou à la réouverture de session)."

# ── h. Cas de migration : sortir l'appli d'un ancien dossier de la grille ────
# Poser le .desktop SUFFIT à faire apparaître l'application dans le lanceur :
# GNOME ajoute les nouvelles applications à sa grille tout seul, sans rien
# déranger. On ne touche donc normalement à RIEN ici.
#
# Une seule exception, repérée plus haut : si une version précédente déclarait
# une catégorie (Utility…), GNOME a mémorisé un rangement plaçant l'appli dans
# le dossier « Utilitaires ». Retirer la catégorie ne l'en fait pas sortir : ce
# souvenir survit à la mise à jour, et l'application reste introuvable.
#
# Dans CE cas seulement, on efface la mémoire de rangement
# (« gsettings reset app-picker-layout ») : GNOME recalcule sa grille et
# l'application revient à la racine. Le prix à payer — un rangement personnel
# remis à plat — n'est donc demandé qu'une fois, à la migration, et jamais lors
# d'une réinstallation ordinaire.
#
# Ce réglage est PERSONNEL : on l'écrit en tant que l'utilisateur, en passant
# par le « bus » de sa session (/run/user/<uid>/bus), qui n'existe que s'il est
# connecté. Sinon on ne force rien : étape « au mieux », jamais bloquante.
UID_CIBLE="$(id -u "$TARGET_USER")"
PRISE_BUS="/run/user/$UID_CIBLE/bus"
if [ "$ANCIENNE_CATEGORIE" = "non" ]; then
    info "Grille d'applications : rangement laissé intact."
elif [ -S "$PRISE_BUS" ]; then
    if runuser -u "$TARGET_USER" -- env DBUS_SESSION_BUS_ADDRESS="unix:path=$PRISE_BUS" \
        gsettings reset org.gnome.shell app-picker-layout 2>/dev/null; then
        info "Migration d'une ancienne version : rangement de la grille réinitialisé."
    else
        avert "Grille d'applications non réinitialisée (bureau non GNOME ?)."
        avert "  Sans effet sur le fonctionnement : l'appli reste trouvable par la recherche."
    fi
else
    avert "Session de $TARGET_USER non ouverte : grille d'applications non réinitialisée."
    avert "  Elle le sera au besoin en relançant ce script une fois connecté·e."
fi

# ── Fin ──────────────────────────────────────────────────────────────────────
echo
info "Installation terminée."
echo
avert "IMPORTANT : $TARGET_USER doit FERMER puis ROUVRIR sa session pour que :"
avert "  - l'appartenance au groupe « lp » prenne effet (droit d'imprimer) ;"
avert "  - l'agent de détection (Programme B) démarre automatiquement."
