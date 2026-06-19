"""coeur.py — le moteur de Stickeuse QL-570 (sans interface).

Il sait parler à l'imprimante Brother QL-570 : la trouver, vérifier qu'on peut
lui écrire, et (bientôt) imprimer. Testable directement en ligne de commande.
Construit en trois étapes : C1 détection · C2 accès · C3 validation + impression
(l'envoi à l'imprimante reste à écrire).

Les termes techniques (motif, nœud, backend, dataclass…) sont définis simplement
dans docs/lexique.md.
"""

import glob                            # liste les fichiers correspondant à un motif (jokers façon shell)
import os                              # outils du système ; ici os.access, pour tester un droit
import pyudev                          # lecture d'udev : la base qui décrit les périphériques
from dataclasses import dataclass      # fabrique des objets de données (constructeur automatique)
from PIL import Image                  # Pillow : ouvrir et inspecter des images (déjà installé via brother_ql)
import shutil                          # shutil.which : retrouver un exécutable dans le PATH
import subprocess                      # lancer une commande externe (brother_ql) en sous-processus


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


# ─────────────────────────────────────────────────────────────────────────────
# C3 — Impression + validation d'un PNG existant
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Etiquette:
    """Décrit le rouleau d'étiquettes chargé. C'est l'UNIQUE constante de
    configuration de l'appli : pour gérer un autre rouleau, on ne touche qu'ici.
    « frozen=True » la rend immuable — une vraie constante, qu'on ne risque pas
    de modifier par accident en cours de route."""
    identifiant: str   # identifiant brother_ql, ex. "39x90" (≠ des mm réels : piège de nommage)
    largeur: int       # largeur imprimable en pixels (portrait)
    hauteur: int       # hauteur imprimable en pixels (portrait)


# Le rouleau de cet exemplaire : DK-11208 (38×90 mm, prédécoupé).
ETIQUETTE = Etiquette(identifiant="39x90", largeur=413, hauteur=991)

# Au-delà de cette proportion de pixels gris (ni noirs ni blancs), on AVERTIT
# que l'image est sans doute floue ou tramée. Repère mesuré : du texte net
# tourne autour de 2 % ; une photo, bien plus. Seuil indicatif, à ajuster.
SEUIL_GRIS = 0.10


def valider_png(chemin, etiquette):
    """Vérifie qu'un fichier est imprimable sur l'étiquette donnée.

    Lève ErreurStickeuse si c'est BLOQUANT (pas un PNG → E-C3-1 ; mauvaises
    dimensions → E-C3-2). Renvoie un avertissement NON bloquant (E-C3-3, trop
    de gris) — ou None si tout est nickel."""

    # --- 7a : est-ce un PNG réellement lisible ? ---
    # On se fie au CONTENU, pas à l'extension : un « .png » peut cacher autre
    # chose, ou être corrompu. open() + load() force le décodage, donc un
    # fichier absent ou abîmé déclenche une OSError ici, qu'on rattrape.
    try:
        image = Image.open(chemin)
        image.load()
    except OSError:
        raise ErreurStickeuse("E-C3-1", f"Fichier introuvable ou illisible : {chemin}")
    if image.format != "PNG":
        raise ErreurStickeuse("E-C3-1", f"Le fichier n'est pas un PNG (format lu : {image.format}).")

    # --- 7b : dimensions EXACTEMENT attendues ? (le seul refus dur de format) ---
    # Portrait pile, OU sa transposée (paysage) que brother_ql pivotera.
    attendu = (etiquette.largeur, etiquette.hauteur)
    transpose = (etiquette.hauteur, etiquette.largeur)
    if image.size not in (attendu, transpose):
        raise ErreurStickeuse(
            "E-C3-2",
            f"Dimensions {image.size} px ; attendu {attendu} ou {transpose}.",
        )

    # --- 7c : l'image est-elle bien nette ? (vérification SOUPLE) ---
    gris = image.convert("L")              # ramène l'image en niveaux de gris
    hist = gris.histogram()                # 256 cases : nb de pixels par niveau (0 = noir, 255 = blanc)
    total = gris.width * gris.height
    proportion_gris = sum(hist[20:235]) / total   # pixels ni quasi-noirs ni quasi-blancs
    if proportion_gris > SEUIL_GRIS:
        # On RENVOIE l'erreur sans la LEVER : c'est un avertissement, pas un
        # blocage. L'appelant l'affichera et imprimera quand même.
        return ErreurStickeuse("E-C3-3", f"Image peut-être floue : {proportion_gris:.0%} de pixels gris.")

    return None   # tout est bon, aucun avertissement

def imprimer(cible, etiquette, chemin):
    """C3-B : envoie un PNG DÉJÀ VALIDÉ à l'imprimante, via la commande brother_ql.

    Reconstruit l'équivalent de la commande de référence, mais avec les valeurs
    DÉTECTÉES (rien en dur), puis la lance. Lève ErreurStickeuse si l'envoi
    échoue ; ne renvoie rien s'il réussit."""

    # Où est l'exécutable brother_ql ? (comme le ferait le shell en fouillant le
    # PATH). Absent → problème d'installation, impression impossible.
    programme = shutil.which("brother_ql")
    if programme is None:
        raise ErreurStickeuse(
            "E-C3-6",
            "Commande « brother_ql » introuvable. Vérifier son installation "
            "et que son dossier (p. ex. ~/.local/bin) est dans le PATH.",
        )

    # La commande en LISTE (pas une chaîne) : subprocess gère lui-même les
    # espaces et caractères spéciaux, sans passer par le shell. Plus sûr.
    commande = [
        programme,
        "-b", cible.backend,          # backend détecté
        "-m", cible.modele,           # modèle détecté
        "-p", cible.adresse,          # adresse détectée
        "print",
        "-l", etiquette.identifiant,  # identifiant d'étiquette (constante de config)
        chemin,                       # le PNG validé
    ]

    resultat = subprocess.run(commande, capture_output=True, text=True)
    if resultat.returncode != 0:
        sortie = (resultat.stderr + resultat.stdout).strip()
        if "permission" in sortie.lower() or "denied" in sortie.lower():
            raise ErreurStickeuse("E-C3-5", "Accès refusé à l'impression (groupe « lp » / règle udev). " + sortie)
        raise ErreurStickeuse("E-C3-4", "L'impression a échoué : " + sortie)
    # returncode == 0 → succès, rien à renvoyer.


if __name__ == "__main__":
    import sys
    try:
        cible = determiner_cible()                       # C1 + C2
        if len(sys.argv) < 2:
            print("Imprimante prête :", cible)
            print("Pour imprimer : python3 coeur.py <chemin_du_png>")
        else:
            chemin = sys.argv[1]
            avertissement = valider_png(chemin, ETIQUETTE)   # C3-A
            if avertissement is not None:
                print(f"[avertissement {avertissement.code}] {avertissement}")
            imprimer(cible, ETIQUETTE, chemin)               # C3-B
            print("Étiquette imprimée.")                     # C3-C
    except ErreurStickeuse as e:
        print(f"[{e.code}] {e}")