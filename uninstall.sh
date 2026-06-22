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

# ── g⁻¹. Retirer l'icône du bureau de l'utilisateur ──────────────────────────
# Même découverte du Bureau qu'à l'installation, pour viser le bon fichier.
DESKTOP_DIR="$(runuser -u "$TARGET_USER" -- xdg-user-dir DESKTOP 2>/dev/null || true)"
if [ -z "$DESKTOP_DIR" ] || [ "$DESKTOP_DIR" = "$TARGET_HOME" ]; then
    DESKTOP_DIR="$TARGET_HOME/Desktop"
fi
ICONE="$DESKTOP_DIR/stickeuse-ql570.desktop"
if [ -f "$ICONE" ]; then
    info "Suppression de l'icône du bureau : $ICONE"
    rm -f "$ICONE"
fi

# ── c⁻¹ / b⁻¹. Retirer l'appli et son venv ───────────────────────────────────
if [ -d "$APP_DIR" ]; then
    info "Suppression de $APP_DIR (programmes + environnement virtuel)"
    rm -rf "$APP_DIR"
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
