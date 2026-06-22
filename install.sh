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
#   xdg-user-dirs  : fournit « xdg-user-dir », qui dit où est le Bureau (locale)
info "apt : dépendances essentielles…"
apt-get install -y python3-tk python3-venv libusb-1.0-0 xdg-user-dirs \
    || erreur "Échec d'installation des dépendances essentielles (apt)."

# OPTIONNELLE — « au mieux » : seulement la pop-up de l'agent. Sans elle,
# l'appli se dégrade en douceur (l'agent écrit dans le journal au lieu d'une
# notification). On n'ARRÊTE donc PAS si elle manque.
info "apt : libnotify-bin (optionnel)…"
apt-get install -y libnotify-bin \
    || avert "libnotify-bin non installé : pas de pop-up, le reste fonctionne."

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
Icon=printer
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

# ── g. Icône sur le bureau (Programme A) ─────────────────────────────────────
# On DÉCOUVRE le dossier « Bureau » via xdg-user-dir (il gère la locale : Bureau
# en français, Desktop en anglais…). On ne code pas le nom en dur. runuser
# exécute la commande EN TANT QUE l'utilisateur (sans mot de passe, car on est
# root), pour lire SA configuration.
DESKTOP_DIR="$(runuser -u "$TARGET_USER" -- xdg-user-dir DESKTOP 2>/dev/null || true)"
if [ -z "$DESKTOP_DIR" ] || [ "$DESKTOP_DIR" = "$TARGET_HOME" ]; then
    # xdg-user-dir absent, ou Bureau non encore configuré (compte jamais ouvert
    # en session graphique) → repli raisonnable + avertissement.
    DESKTOP_DIR="$TARGET_HOME/Desktop"
    avert "Dossier Bureau non détecté : repli sur $DESKTOP_DIR."
fi
ICONE="$DESKTOP_DIR/stickeuse-ql570.desktop"
info "Pose de l'icône sur le bureau : $ICONE"
mkdir -p "$DESKTOP_DIR"
cat > "$ICONE" <<EOF
[Desktop Entry]
Type=Application
Name=Stickeuse QL-570
Comment=Imprimer une étiquette sur la Brother QL-570
Exec=$PY $APP_DIR/programme_a.py
Icon=printer
Terminal=false
EOF
# L'icône doit APPARTENIR à l'utilisateur et être exécutable.
chown "$TARGET_USER:$TARGET_GROUP" "$ICONE"
chmod 0755 "$ICONE"
# Sur GNOME, une icône de bureau doit EN PLUS être marquée « de confiance ».
# gio peut être absent selon le bureau → « au mieux », on n'échoue pas.
runuser -u "$TARGET_USER" -- gio set "$ICONE" metadata::trusted true 2>/dev/null \
    || avert "Icône non marquée « de confiance » : selon le bureau, un clic droit « Autoriser le lancement » peut être nécessaire au 1ᵉʳ usage."

# ── Fin ──────────────────────────────────────────────────────────────────────
echo
info "Installation terminée."
echo
avert "IMPORTANT : $TARGET_USER doit FERMER puis ROUVRIR sa session pour que :"
avert "  - l'appartenance au groupe « lp » prenne effet (droit d'imprimer) ;"
avert "  - l'agent de détection (Programme B) démarre automatiquement."
