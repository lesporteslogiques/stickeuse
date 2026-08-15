#!/usr/bin/env bash
#
# uninstall.sh — désinstallation de « Stickeuse QL-570 ». Symétrique d'install.sh.
#
# À LANCER EN ROOT (« su - » puis ./uninstall.sh <login>). <login> sert à
# retrouver l'icône posée sur LE bureau de cet utilisateur, et ses journaux.
#
# Choix assumés (prudence) :
#   - on NE retire PAS l'utilisateur du groupe « lp » (partagé avec d'autres
#     usages d'impression : le retirer pourrait casser autre chose) ;
#   - on NE désinstalle PAS les paquets système (python3-tk, libusb…) : d'autres
#     programmes peuvent en dépendre ;
#   - les journaux (~/.ql570) ne sont effacés QUE si on le confirme.

set -euo pipefail
export PATH="/usr/local/sbin:/usr/sbin:/sbin:$PATH"

info()   { printf '  [info] %s\n' "$*"; }
avert()  { printf '  [!]    %s\n' "$*" >&2; }
erreur() { printf '  [STOP] %s\n' "$*" >&2; exit 1; }

# Mêmes chemins qu'à l'installation (à garder synchronisés avec install.sh).
APP_DIR="/opt/ql570"
REGLE_UDEV="/etc/udev/rules.d/99-ql570.rules"
AUTOSTART="/etc/xdg/autostart/ql570-agent.desktop"

[ "$(id -u)" -eq 0 ] || erreur "À lancer en root (ex. « su - » puis ./uninstall.sh <login>)."

TARGET_USER="${1:-${SUDO_USER:-}}"
[ -n "$TARGET_USER" ] || erreur "Préciser le compte : ./uninstall.sh <login>"
id "$TARGET_USER" >/dev/null 2>&1 || erreur "Compte introuvable : $TARGET_USER"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

# Tout est tolérant à l'absence (rm -f / -rf, tests d'existence) : on peut
# relancer uninstall.sh sans erreur même si une partie est déjà retirée.

# ── f⁻¹. Retirer l'autostart de l'agent ──────────────────────────────────────
if [ -f "$AUTOSTART" ]; then
    info "Suppression de l'autostart : $AUTOSTART"
    rm -f "$AUTOSTART"
fi

# ── e⁻¹. Retirer la règle udev (puis recharger) ──────────────────────────────
if [ -f "$REGLE_UDEV" ]; then
    info "Suppression de la règle udev : $REGLE_UDEV"
    rm -f "$REGLE_UDEV"
    udevadm control --reload-rules
    udevadm trigger || avert "udevadm trigger a renvoyé une erreur (sans gravité)."
fi

# ── g⁻¹. Retirer l'entrée du menu des applications ───────────────────────────
LANCEUR="/usr/share/applications/stickeuse-ql570.desktop"
if [ -f "$LANCEUR" ]; then
    info "Suppression de l'entrée de menu : $LANCEUR"
    rm -f "$LANCEUR"
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

# ── Relevé préalable : quelles mires l'installation a-t-elle posées ? ───────
# On le lit dans /opt/ql570 AVANT de l'effacer, plutôt que de réécrire ici la
# liste des noms. Une liste écrite à deux endroits finit toujours par diverger :
# on ajoute un rouleau à l'installation, on oublie la désinstallation, et un
# fichier orphelin reste chez l'utilisateur. Ici, la désinstallation ne connaît
# aucun nom — elle retire exactement ce qui a été posé, quels qu'ils soient.
MIRES_POSEES=""
if [ -d "$APP_DIR" ]; then
    for chemin in "$APP_DIR"/test-stickeuse-*.png; do
        [ -f "$chemin" ] && MIRES_POSEES="$MIRES_POSEES $(basename "$chemin")"
    done
fi

# ── c⁻¹ / b⁻¹. Retirer l'appli et son venv ───────────────────────────────────
if [ -d "$APP_DIR" ]; then
    info "Suppression de $APP_DIR (programmes + environnement virtuel)"
    rm -rf "$APP_DIR"
fi

# ── c bis⁻¹. Retirer les copies des mires chez l'utilisateur ─────────────────
# /opt/ql570 est parti en entier (ci-dessus), mais les copies déposées dans le
# dossier « Images » vivent chez l'utilisateur : on les retire NOMMÉMENT, et
# elles seules, d'après le relevé fait plus haut. On ne touche évidemment pas au
# dossier, qui contient les images de la personne.
DOSSIER_IMAGES="$(runuser -l "$TARGET_USER" -c 'xdg-user-dir PICTURES' 2>/dev/null || true)"
if [ -z "$DOSSIER_IMAGES" ] || [ "$DOSSIER_IMAGES" = "$TARGET_HOME" ]; then
    DOSSIER_IMAGES="$TARGET_HOME/Images"
fi
for mire in $MIRES_POSEES; do
    if [ -f "$DOSSIER_IMAGES/$mire" ]; then
        info "Suppression de la mire de test : $DOSSIER_IMAGES/$mire"
        rm -f "$DOSSIER_IMAGES/$mire"
    fi
done

# ── h⁻¹. Retirer l'application des favoris (dock), s'il y a lieu ─────────────
# Les versions 2026-08 les plus anciennes épinglaient l'appli au dock ; ce n'est
# plus le cas (le dock l'affiche pendant qu'elle tourne, c'est suffisant). On
# nettoie ce reliquat chez les postes concernés, sans toucher aux autres favoris
# de la personne. On NE touche PAS au rangement de la grille : c'est son
# arrangement personnel, et il ne nous appartient pas.
LANCEUR_ID="stickeuse-ql570.desktop"
UID_CIBLE="$(id -u "$TARGET_USER")"
PRISE_BUS="/run/user/$UID_CIBLE/bus"
if [ -S "$PRISE_BUS" ]; then
    FAVORIS="$(runuser -u "$TARGET_USER" -- env DBUS_SESSION_BUS_ADDRESS="unix:path=$PRISE_BUS" \
        gsettings get org.gnome.shell favorite-apps 2>/dev/null || true)"
    case "$FAVORIS" in
        *"$LANCEUR_ID"*)
            # On retire notre entrée et la virgule qui l'accompagne, quelle que
            # soit sa place dans la liste (début, milieu ou fin).
            NOUVEAUX="$(printf '%s' "$FAVORIS" \
                | sed -e "s/'$LANCEUR_ID', //g" -e "s/, '$LANCEUR_ID'//g" -e "s/'$LANCEUR_ID'//g")"
            runuser -u "$TARGET_USER" -- env DBUS_SESSION_BUS_ADDRESS="unix:path=$PRISE_BUS" \
                gsettings set org.gnome.shell favorite-apps "$NOUVEAUX" 2>/dev/null \
                && info "Application retirée du dock de $TARGET_USER." \
                || avert "Retrait du dock impossible : clic droit sur l'icône → « Retirer des favoris »."
            ;;
        "")
            avert "Favoris de $TARGET_USER illisibles : dock non vérifié." ;;
        *)
            info "Application absente du dock : rien à retirer." ;;
    esac
else
    avert "Session de $TARGET_USER non ouverte : dock non vérifié."
fi

# ── d : NON défait (groupe lp partagé) ───────────────────────────────────────
avert "Le compte $TARGET_USER reste dans le groupe « lp » (partagé) — non retiré, volontairement."

# ── Journaux : sur confirmation seulement ────────────────────────────────────
LOGS="$TARGET_HOME/.ql570"
if [ -d "$LOGS" ]; then
    # « read » peut échouer s'il n'y a pas de terminal (script non interactif) :
    # on protège par « || rep=N » pour ne pas tomber sous set -e, et on conserve.
    rep="N"
    read -r -p "  Supprimer aussi les journaux $LOGS ? [o/N] " rep || rep="N"
    case "$rep" in
        [oO]*) rm -rf "$LOGS"; info "Journaux supprimés." ;;
        *)     info "Journaux conservés : $LOGS" ;;
    esac
fi

echo
info "Désinstallation terminée."
