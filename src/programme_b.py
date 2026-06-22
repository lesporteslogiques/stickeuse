"""programme_b.py — Stickeuse QL-570, l'agent de détection (fond de session).

Programme B tourne en arrière-plan, **sans fenêtre**. Il surveille les
branchements USB et, quand une QL-570 apparaît, affiche une notification de
bureau « QL-570 détectée ». Il N'IMPRIME JAMAIS : il ne fait que détecter et
signaler. Il reconnaît l'imprimante par la **même identité USB que C1** (cœur),
et s'appuie sur le journal — son seul moyen de trace, faute de fenêtre.

État : B2 — finitions : arrêt propre au Ctrl-C, et journalisation du
débranchement (identification par CHEMIN mémorisé : voir surveiller()).

Les termes (udev, moniteur, notification, chemin sysfs…) sont définis dans
docs/lexique.md.
"""

import shutil                        # shutil.which : retrouver notify-send sur le PATH
import subprocess                    # lancer notify-send (la notification de bureau)
import pyudev                        # écoute des événements de périphériques (comme C1, côté flux)

from journal import obtenir_journal  # le journal partagé du poste

# Mêmes codes qu'en C1 : c'est ainsi qu'on reconnaît LA QL-570 et pas un autre USB.
ID_VENDOR_BROTHER = "04f9"
ID_PRODUCT_QL570 = "2028"


def notifier(titre, message, journal):
    """Affiche une notification de bureau (pop-up éphémère) via notify-send.

    Si notify-send est absent, on se rabat sur le journal : l'agent n'ayant pas
    de fenêtre, le log reste son filet de signalement."""
    programme = shutil.which("notify-send")
    if programme is None:
        journal.warning("notify-send introuvable : notification non affichée.")
        return
    subprocess.run([programme, titre, message])


def surveiller():
    """Boucle principale : écoute l'USB et signale les arrivées/départs de la QL-570.

    Identification : à l'AJOUT, on lit idVendor/idProduct (le sysfs est vivant) ;
    si c'est la QL-570, on RETIENT son chemin sysfs. Au RETRAIT, le sysfs est
    déjà démonté — impossible d'y relire l'identité — alors on reconnaît
    l'imprimante en comparant le chemin de l'événement à celui qu'on a mémorisé.

    Limite assumée : on ne trace que le départ d'une imprimante dont on a vu
    l'arrivée. Si elle était déjà branchée avant le lancement de l'agent, son
    débranchement ne sera pas journalisé (ce n'est qu'une trace de diagnostic).

    Le Ctrl-C est la façon normale d'arrêter l'agent : on l'intercepte pour
    finir proprement, sans dérouler de traceback."""
    journal = obtenir_journal()
    journal.info("Démarrage de l'agent de détection (Programme B).")

    contexte = pyudev.Context()
    moniteur = pyudev.Monitor.from_netlink(contexte)   # le flux d'événements du noyau
    moniteur.filter_by(subsystem="usb")                # on ne garde que l'USB

    chemin_ql570 = None   # mémoire : chemin sysfs de la QL-570 tant qu'elle est branchée

    try:
        # iter(moniteur.poll, None) : « attends le prochain événement », sans fin.
        for peripherique in iter(moniteur.poll, None):
            action = peripherique.action

            if action == "add" and peripherique.device_type == "usb_device":
                # À l'ajout, le sysfs est lisible (chemin éprouvé en B1).
                try:
                    vendor = peripherique.attributes.asstring("idVendor")
                    product = peripherique.attributes.asstring("idProduct")
                except (KeyError, UnicodeDecodeError):
                    continue                               # attributs absents → pas notre affaire
                if vendor == ID_VENDOR_BROTHER and product == ID_PRODUCT_QL570:
                    chemin_ql570 = peripherique.sys_path   # on retient QUI elle est
                    journal.info("QL-570 branchée → notification.")
                    notifier("Stickeuse QL-570", "QL-570 détectée — prête à imprimer.", journal)

            elif action == "remove" and peripherique.sys_path == chemin_ql570:
                # On la reconnaît à son chemin mémorisé, sans relire le sysfs démonté.
                chemin_ql570 = None
                journal.info("QL-570 débranchée.")

    except KeyboardInterrupt:
        journal.info("Arrêt de l'agent (Ctrl-C).")


if __name__ == "__main__":
    surveiller()
