"""programme_a.py — Stickeuse QL-570, l'application d'impression (fenêtre).

Programme A OUVRE une fenêtre et ne sert qu'à imprimer. Il s'appuie sur le cœur
(détection, validation, impression) et sur le journal — il ne réinvente rien.
Deux écrans, comme dans l'algo :
  1) un accueil-checklist (garde-fou humain pour ce que l'imprimante ne sait pas
     dire : rouleau chargé, sous tension…), pendant lequel on lance C1 + C2 ;
  2) la fenêtre principale (choisir un PNG, nombre d'exemplaires, imprimer).

Ici : la brique A1 — l'écran d'accueil. La fenêtre principale viendra ensuite.

Les termes d'interface (widget, Tk, pack…) sont définis simplement dans
docs/lexique.md.
"""

import tkinter as tk                 # Tkinter : la boîte à outils d'interface graphique du standard Python
from tkinter import messagebox       # fenêtres-message toutes faites (info, erreur, avertissement)

import coeur                         # le moteur : determiner_cible, ErreurStickeuse, ETIQUETTE…
from journal import obtenir_journal  # le journal partagé du poste


# Les points de la checklist : ce que la QL-570 ne sait PAS détecter, donc
# qu'un humain confirme avant de commencer (la couche de prévention N1).
CHECKLIST = [
    "L'imprimante Brother QL-570 est branchée sur le secteur.",
    "Elle est sous tension (voyant vert allumé).",
    "Les étiquettes DK-11208 (38×90 mm) sont chargées.",
    "Il y a assez d'étiquettes pour le projet.",
]


def lancer():
    """Point d'entrée du Programme A : construit l'écran d'accueil et l'affiche.

    Tkinter fonctionne ainsi : on crée une fenêtre, on y pose des « widgets »
    (étiquettes, cases, boutons), puis on lance la « boucle d'événements »
    (mainloop) qui attend et traite les clics jusqu'à la fermeture.
    """
    journal = obtenir_journal()
    journal.info("Lancement Programme A (accueil)")

    fenetre = tk.Tk()                                   # la fenêtre racine
    fenetre.title("Stickeuse QL-570 — Bienvenue !")

    # tk.Label = un texte fixe. .pack() place le widget dans la fenêtre
    # (empilement vertical par défaut), avec un peu de marge (padx/pady).
    tk.Label(fenetre, text="Avant de commencer, vérifie :",
             font=("", 12, "bold")).pack(padx=20, pady=(20, 10))

    # Une case à cocher par point. Chaque case est reliée à une « variable
    # Tkinter » booléenne qui retient son état (cochée ou non) ; on garde la
    # liste de ces variables pour vérifier, au clic OK, que tout est coché.
    cases = []
    for texte in CHECKLIST:
        coche = tk.BooleanVar()
        tk.Checkbutton(fenetre, text=texte, variable=coche,
                       anchor="w", justify="left").pack(fill="x", padx=20)
        cases.append(coche)

    def sur_ok():
        """Appelée au clic sur OK (c'est la « command » du bouton)."""
        # 1) La checklist humaine doit être complète.
        if not all(case.get() for case in cases):
            messagebox.showwarning("Checklist", "Coche d'abord tous les points.")
            return

        # 2) Elle l'est → on lance le cœur : C1 (détection) + C2 (accès).
        try:
            cible = coeur.determiner_cible()
        except coeur.ErreurStickeuse as e:
            # Échec catalogué (E-C2-*) → on journalise et on montre l'erreur,
            # SANS ouvrir la fenêtre principale (exactement ce que dit l'algo).
            journal.error(f"{e.code} {e}")
            messagebox.showerror(f"Problème [{e.code}]", str(e))
            return

        journal.info(f"Accueil validé · cible : {cible}")
        # 3) Provisoire (brique A1) : on confirme. La fenêtre principale
        #    (brique A2) prendra la place de ce message.
        messagebox.showinfo(
            "Imprimante prête",
            f"{cible.modele} détectée ({cible.backend}).\n"
            "La fenêtre d'impression arrivera à la brique suivante.",
        )

    tk.Button(fenetre, text="OK", command=sur_ok, width=12).pack(pady=20)

    fenetre.mainloop()   # rend la main à Tkinter : la fenêtre vit jusqu'à sa fermeture


if __name__ == "__main__":
    lancer()
