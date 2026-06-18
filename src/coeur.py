"""coeur.py — le moteur de Stickeuse QL-570 (sans interface).

Il sait parler à l'imprimante Brother QL-570 : la trouver, vérifier qu'on peut
lui écrire, et (plus tard) imprimer. Testable directement en ligne de commande.
Construit en trois étapes : C1 détection · C2 accès · C3 impression (à venir).

Les termes techniques (motif, nœud, backend, dataclass…) sont définis simplement
dans docs/lexique.md.
"""

import glob                            # liste les fichiers correspondant à un motif (jokers façon shell)
import os                              # outils du système ; ici os.access, pour tester un droit
import pyudev                          # lecture d'udev : la base qui décrit les périphériques
from dataclasses import dataclass      # fabrique des objets de données (constructeur automatique)


class ErreurStickeuse(Exception):
    """Erreur prévue de l'application, portant un code de catalogue (ex. "E-C2-1").

    « Lever » cette exception (raise), c'est dire « je ne peux pas continuer, et
    voici pourquoi ». Le code permettra plus tard de traduire l'incident en
    message clair et en geste à faire (voir le catalogue d'erreurs de l'algo).
    """
    def __init__(self, code, message):
        super().__init__(message)   # message lisible, comme pour toute exception
        self.code = code            # ex. "E-C2-1" : la clé vers le catalogue


# ─────────────────────────────────────────────────────────────────────────────
# C1 — Détection : trouver le port et le modèle de l'imprimante branchée
# ─────────────────────────────────────────────────────────────────────────────

def lister_noeuds_lp():
    """Liste les nœuds /dev/usb/lp* exposés par le noyau (liste, possiblement vide).

    Un « nœud » est le fichier-périphérique par lequel le noyau expose une
    imprimante USB. Son numéro (lp0, lp1…) change selon les branchements : on ne
    le code donc JAMAIS en dur, on le découvre.
    """
    # sorted → ordre stable, pour que le « premier trouvé gagne » de detecter()
    # soit reproductible, et non livré au hasard de l'ordre du système.
    return sorted(glob.glob("/dev/usb/lp*"))


def lire_identite_usb(chemin):
    """Pour un nœud donné, renvoie l'identité USB de l'imprimante, ou None.

    L'identité (fabricant, modèle) ne vit PAS sur le nœud lpX lui-même, mais sur
    son « parent » : le périphérique USB physique. On remonte donc à ce parent.
    """
    contexte = pyudev.Context()                                # point d'entrée vers udev
    noeud = pyudev.Devices.from_device_file(contexte, chemin)  # le chemin devient un objet interrogeable
    parent = noeud.find_parent("usb", "usb_device")            # on remonte au périphérique USB physique
    if parent is None:                                         # un nœud peut n'avoir aucun parent USB ;
        return None                                            # on ne suppose jamais qu'il existe.
    return {
        "idVendor": parent.attributes.asstring("idVendor"),    # 04f9 attendu = Brother
        "idProduct": parent.attributes.asstring("idProduct"),  # 2028 attendu = QL-570
        "product": parent.attributes.asstring("product"),      # "QL-570" : le nom lisible du modèle
    }


@dataclass
class Imprimante:
    """Ce que C1 a trouvé : où est l'imprimante (port) et quel est son modèle."""
    port: str       # ex. "/dev/usb/lp1"
    modele: str     # ex. "QL-570"


def detecter():
    """Renvoie la première imprimante Brother branchée (Imprimante), ou None."""
    for chemin in lister_noeuds_lp():            # on essaie chaque nœud, dans l'ordre stable
        identite = lire_identite_usb(chemin)
        if identite is not None and identite["idVendor"] == "04f9":     # 04f9 = code fabricant Brother
            return Imprimante(port=chemin, modele=identite["product"])  # premier Brother → on rend aussitôt
    return None                                  # parcouru sans Brother → aucune imprimante


# ─────────────────────────────────────────────────────────────────────────────
# C2 — Accès & robustesse : produire le trio (backend, adresse, modèle) pour C3,
#      ou lever une erreur cataloguée.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Cible:
    """Le « par quoi parler » à l'imprimante : les 3 infos que C3 passera à
    brother_ql (ses drapeaux -b, -p, -m)."""
    backend: str    # "linux_kernel" (via un nœud lpX) ou "pyusb" (direct sur le bus)
    adresse: str    # "file:///dev/usb/lp1"  ou  "usb://0x04f9:0x2028"
    modele: str     # "QL-570"


def chercher_via_pyusb():
    """Repli quand AUCUN nœud /dev/usb/lp* n'existe (pilote usblp absent) :
    on cherche l'imprimante directement sur le bus USB.

    Renvoie une Cible, None si rien trouvé, et lève E-C2-3 si on la voit mais
    qu'on ne peut pas l'ouvrir (règle udev manquante).
    """
    import usb.core   # importé seulement ici : ce repli est rare, on ne charge pyusb qu'au besoin

    # 0x04f9 / 0x2028 : les mêmes codes qu'en C1, mais écrits en hexadécimal (0x…),
    # la notation que pyusb attend.
    dev = usb.core.find(idVendor=0x04f9, idProduct=0x2028)
    if dev is None:
        return None                              # pas sur le bus non plus
    try:
        modele = dev.product or "QL-570"         # nom lu dans le descripteur USB
    except (ValueError, usb.core.USBError):
        # Lire ce nom oblige à ouvrir le périphérique : si ça échoue, c'est un
        # problème d'accès (libusb) → la règle udev est probablement absente.
        raise ErreurStickeuse(
            "E-C2-3",
            "Imprimante vue sur le bus mais non ouvrable (règle udev absente ?).",
        )
    return Cible(backend="pyusb", adresse="usb://0x04f9:0x2028", modele=modele)


def determiner_cible():
    """C2 complet : renvoie le trio (Cible) prêt pour l'impression, ou lève
    ErreurStickeuse si l'imprimante est absente ou inaccessible.
    """
    imprimante = detecter()                      # on réutilise C1
    if imprimante is not None:
        # Voie noyau : on a un nœud /dev/usb/lpX. Peut-on ÉCRIRE dessus ?
        # (en pratique : appartenir au groupe « lp »). os.W_OK = « droit d'écriture ».
        if not os.access(imprimante.port, os.W_OK):
            raise ErreurStickeuse(
                "E-C2-2",
                "Pas le droit d'écrire sur l'imprimante. "
                "Ajouter l'utilisateur au groupe « lp », puis rouvrir la session.",
            )
        return Cible(
            backend="linux_kernel",
            adresse="file://" + imprimante.port,   # /dev/usb/lp1 → file:///dev/usb/lp1
            modele=imprimante.modele,
        )

    # Pas de Brother sur un nœud. Est-ce parce qu'il n'y a AUCUN nœud lp* ?
    if not lister_noeuds_lp():                   # liste vide → peut-être le pilote usblp absent
        cible = chercher_via_pyusb()             # → on tente le bus directement
        if cible is not None:
            return cible

    # Soit des nœuds existent sans Brother, soit pyusb n'a rien trouvé :
    raise ErreurStickeuse(
        "E-C2-1",
        "Aucune imprimante Brother trouvée (ni nœud /dev/usb/lpX, ni sur le bus). "
        "Vérifier qu'elle est branchée et allumée.",
    )


if __name__ == "__main__":          # ne s'exécute QUE si on lance coeur.py directement ;
                                    # à l'import (depuis programme_a / programme_b), ce bloc est ignoré.
    try:
        print(determiner_cible())
    except ErreurStickeuse as e:
        print(f"[{e.code}] {e}")
