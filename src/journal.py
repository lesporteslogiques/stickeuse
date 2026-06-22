"""journal.py — la journalisation de Stickeuse QL-570 (transversal).

Un « journal » (log) est un fichier où le programme écrit, ligne par ligne et
horodaté, ce qu'il fait et les incidents qu'il rencontre. Il sert APRÈS coup :
quand quelque chose a mal tourné sur un poste, on relit le journal pour
comprendre — sans avoir à reproduire le problème devant la personne.

Un journal PAR POSTE : ~/.ql570/ql570-<hostname>.log. Mettre le nom de machine
(hostname) dans le fichier évite que deux postes écrivent dans le même journal
au cas où le dossier personnel serait partagé sur le réseau.

Séparation des rôles : ce module dit OÙ va le journal (obtenir_journal, appelé
une fois au lancement d'un programme) ; ensuite, n'importe quel module écrit
dedans sans se soucier du fichier.
"""

import logging                  # le module de journalisation de la bibliothèque standard
import socket                   # socket.gethostname() : le nom de la machine
from pathlib import Path        # chemins manipulés comme des objets, plus lisibles que des chaînes


def chemin_journal():
    """Renvoie le chemin du fichier-journal de CE poste, en créant le dossier
    ~/.ql570/ s'il n'existe pas encore."""
    dossier = Path.home() / ".ql570"          # ~/.ql570  (Path.home() = le dossier personnel)
    dossier.mkdir(exist_ok=True)              # le crée si absent ; ne proteste pas s'il existe déjà
    hostname = socket.gethostname()           # ex. "op42", "op52"
    return dossier / f"ql570-{hostname}.log"  # ex. ~/.ql570/ql570-op42.log


def obtenir_journal():
    """Renvoie le journal de l'appli, configuré (une seule fois) pour écrire
    dans le fichier du poste.

    On passe par un logger NOMMÉ ("ql570") : tous les modules qui demandent ce
    nom reçoivent le MÊME objet-journal. C'est ainsi que cœur, Programme A et
    Programme B partageront un seul journal sans se le passer la main."""
    journal = logging.getLogger("ql570")      # toujours le même objet pour ce nom

    # S'il est déjà configuré (il a un "handler"), on ne recommence pas : sinon
    # chaque appel ajouterait un canal d'écriture de plus, et chaque ligne
    # finirait écrite en double, triple… Un "handler" = la destination d'écriture.
    if not journal.handlers:
        journal.setLevel(logging.INFO)        # on garde INFO et au-dessus (INFO, WARNING, ERROR)
        handler = logging.FileHandler(chemin_journal(), encoding="utf-8")  # écrit dans le fichier (en ajout)
        forme = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",   # horodatage [NIVEAU] message
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(forme)
        journal.addHandler(handler)

    return journal
