"""programme_a.py — Stickeuse QL-570, l'application d'impression (fenêtre).

Programme A OUVRE une fenêtre et ne sert qu'à imprimer. Il s'appuie sur le cœur
(détection, validation, impression) et sur le journal — il ne réinvente rien.
Deux écrans :
  1) un accueil-checklist (garde-fou humain), pendant lequel on lance C1 + C2 ;
  2) la fenêtre principale : choisir un PNG (validé à la volée), un nombre
     d'exemplaires, puis imprimer.

Programme A complet : A1 (accueil) · A2 (mise en page) · A3 (comportement).

Les termes d'interface (widget, Tk, pack, Frame…) sont définis dans docs/lexique.md.
"""

import os                            # os.path.basename : le nom d'un fichier sans son chemin
import tkinter as tk                 # Tkinter : la boîte à outils d'interface graphique du standard Python
from tkinter import messagebox       # fenêtres-message toutes faites (info, erreur, avertissement)
from tkinter import filedialog       # la fenêtre standard « choisir un fichier »
from PIL import Image, ImageTk        # Pillow : ouvrir l'image (Image) et la rendre affichable par Tkinter (ImageTk)

import coeur                         # le moteur : determiner_cible, valider_png, imprimer, ETIQUETTE…
from journal import obtenir_journal  # le journal partagé du poste


CHECKLIST = [
    "L'imprimante Brother QL-570 est branchée sur le secteur.",
    "Elle est sous tension (voyant vert allumé).",
    "Les étiquettes DK-11208 (38×90 mm) sont chargées.",
    "Il y a assez d'étiquettes pour le projet.",
]


def lancer():
    """Point d'entrée : enchaîne les deux écrans. L'accueil renvoie la cible
    (imprimante prête) ; sans cible (échec ou fenêtre fermée), on s'arrête."""
    journal = obtenir_journal()
    journal.info("Lancement Programme A")
    cible = ecran_accueil(journal)
    if cible is None:
        journal.info("Arrêt après l'accueil (échec ou fermeture).")
        return
    fenetre_principale(journal, cible)


def ecran_accueil(journal):
    """Écran « Bienvenue ! » : checklist + OK. Au clic OK (tout coché), on lance
    C1 + C2. Succès → on renvoie la Cible ; échec → fenêtre-erreur, on renvoie None."""
    resultat = {"cible": None}                 # un « casier » pour rapporter la cible hors du callback

    fenetre = tk.Tk()
    fenetre.title("Stickeuse QL-570 — Bienvenue !")

    tk.Label(fenetre, text="Avant de commencer, vérifie :",
             font=("", 12, "bold")).pack(padx=20, pady=(20, 10))

    cases = []
    for texte in CHECKLIST:
        coche = tk.BooleanVar()                # variable Tkinter : retient l'état (cochée ou non)
        tk.Checkbutton(fenetre, text=texte, variable=coche,
                       anchor="w", justify="left").pack(fill="x", padx=20)
        cases.append(coche)

    def sur_ok():
        if not all(case.get() for case in cases):
            messagebox.showwarning("Checklist", "Coche d'abord tous les points.")
            return
        try:
            cible = coeur.determiner_cible()   # C1 + C2
        except coeur.ErreurStickeuse as e:
            journal.error(f"{e.code} {e}")
            messagebox.showerror(f"Problème [{e.code}]", str(e))
            return                             # on n'ouvre pas la suite ; resultat["cible"] reste None
        journal.info(f"Accueil validé · cible : {cible}")
        resultat["cible"] = cible
        fenetre.destroy()                      # ferme l'accueil → fin de SON mainloop

    tk.Button(fenetre, text="OK", command=sur_ok, width=12).pack(pady=20)

    fenetre.mainloop()                         # bloque ici jusqu'à destroy() ou fermeture
    return resultat["cible"]


def fenetre_principale(journal, cible):
    """La fenêtre d'impression : choisir un PNG (validé), un nombre, imprimer."""
    fenetre = tk.Tk()                          # second écran = sa propre fenêtre racine
    fenetre.title("Stickeuse QL-570")
    etat = {"chemin": None,                    # le PNG validé prêt à imprimer (None tant qu'aucun)
            "apercu": None}                    # la PhotoImage de l'aperçu : on la GARDE ici pour que
                                               # le ramasse-miettes ne la supprime pas (sinon aperçu blanc)

    # ── En-tête (l'icône imprimante, un fichier image, viendra plus tard) ──
    tk.Label(fenetre, text="Stickeuse QL-570", font=("", 16, "bold")).pack(pady=(16, 2))
    tk.Label(fenetre, text=f"{cible.modele} prête", fg="#2e7d32").pack(pady=(0, 12))

    # ── Section « Fichier à imprimer » ──
    nom_fichier = tk.StringVar(value="Aucun fichier sélectionné")  # variable texte reliée au Label
    cadre_fichier = tk.Frame(fenetre)
    cadre_fichier.pack(fill="x", padx=20, pady=6)
    tk.Label(cadre_fichier, text="Fichier à imprimer :").pack(anchor="w")
    ligne = tk.Frame(cadre_fichier)
    ligne.pack(fill="x", pady=4)
    bouton_parcourir = tk.Button(ligne, text="Parcourir…")         # sa command est câblée plus bas
    bouton_parcourir.pack(side="left")
    tk.Label(ligne, textvariable=nom_fichier, fg="#555").pack(side="left", padx=10)

    # ── Zone d'aperçu (sous « Parcourir », au-dessus d'« Imprimer ») ──
    # Un Label vide qui accueillera la vignette du PNG validé. Tant qu'aucun
    # fichier valide n'est choisi, il reste vide ; parcourir() le remplit ou le vide.
    apercu = tk.Label(fenetre)                 # pas d'image au départ
    apercu.pack(pady=8)

    # ── Section « Nombre d'exemplaires » ──
    cadre_nb = tk.Frame(fenetre)
    cadre_nb.pack(fill="x", padx=20, pady=6)
    tk.Label(cadre_nb, text="Nombre d'exemplaires :").pack(side="left")
    exemplaires = tk.Spinbox(cadre_nb, from_=1, to=99, width=4)    # sélecteur numérique, défaut 1
    exemplaires.pack(side="left", padx=8)
    tk.Label(cadre_nb, text="étiquette(s)").pack(side="left")

    # ── Bouton « Imprimer » (vert, désactivé tant qu'aucun fichier valide) ──
    bouton_imprimer = tk.Button(fenetre, text="Imprimer", bg="#2e7d32", fg="white",
                                state="disabled", width=16)
    bouton_imprimer.pack(pady=16)

    # ── Pied de page ──
    tk.Label(fenetre,
             text="© 2026 Vitally LUBIN · FabLab Les Portes Logiques · AGPL-3.0",
             fg="#888", font=("", 8)).pack(pady=(8, 12))

    # ── Comportements (A3) : on relie les boutons à du code, une fois la mise
    #    en page construite. C'est .config(command=…) qui fait ce branchement. ──

    def parcourir():
        """Choisir un fichier → le VALIDER (C3-A) → activer ou non « Imprimer »."""

        def vider_apercu():
            """Efface la vignette (fichier refusé, ou aucun fichier)."""
            apercu.config(image="")            # plus d'image dans le Label
            etat["apercu"] = None              # on lâche la référence gardée

        def montrer_apercu(chemin_png):
            """Affiche une vignette du PNG validé, proportions préservées."""
            image = Image.open(chemin_png)
            image.thumbnail((200, 200))        # réduit SANS déformer (au plus 200 px de côté)
            photo = ImageTk.PhotoImage(image)  # version affichable par Tkinter
            apercu.config(image=photo)
            etat["apercu"] = photo             # ← on GARDE la référence (sinon ramasse-miettes → aperçu blanc)

        chemin = filedialog.askopenfilename(
            title="Choisir un PNG",
            filetypes=[("Images PNG", "*.png"), ("Tous les fichiers", "*")],
        )
        if not chemin:                         # annulé : on ne touche à rien
            return
        nom_fichier.set(os.path.basename(chemin))
        try:
            avertissement = coeur.valider_png(chemin, coeur.ETIQUETTE)
        except coeur.ErreurStickeuse as e:     # refus DUR (E-C3-1 / E-C3-2)
            journal.warning(f"{e.code} {e}")
            etat["chemin"] = None
            vider_apercu()                     # fichier non imprimable → pas d'aperçu
            bouton_imprimer.config(state="disabled")   # on (re)désactive : fichier non imprimable
            messagebox.showerror(f"Fichier refusé [{e.code}]", str(e))
            return
        # Fichier accepté (avec ou sans avertissement souple) → on peut imprimer.
        etat["chemin"] = chemin
        montrer_apercu(chemin)                 # aperçu seulement APRÈS validation réussie
        bouton_imprimer.config(state="normal")
        if avertissement is not None:          # E-C3-3 : trop de gris, mais non bloquant
            journal.warning(f"{avertissement.code} {avertissement}")
            messagebox.showwarning(f"Avertissement [{avertissement.code}]",
                                   f"{avertissement}\nTu peux imprimer quand même.")
        else:
            journal.info(f"Fichier validé : {chemin}")

    def imprimer_action():
        """Clic « Imprimer » → C3 répété selon le nombre d'exemplaires."""
        chemin = etat["chemin"]
        if chemin is None:                     # garde-fou (le bouton ne devrait pas être actif)
            return
        try:
            nombre = int(exemplaires.get())
        except ValueError:
            nombre = 1                         # saisie bizarre → on retombe sur 1
        try:
            for _ in range(nombre):
                coeur.imprimer(cible, coeur.ETIQUETTE, chemin)   # une étiquette par appel
        except coeur.ErreurStickeuse as e:
            journal.error(f"{e.code} {e}")
            messagebox.showerror(f"Échec [{e.code}]", str(e))
            return
        journal.info(f"Imprimé {nombre}× : {chemin}")
        messagebox.showinfo("Imprimé", f"{nombre} étiquette(s) imprimée(s).")

    bouton_parcourir.config(command=parcourir)
    bouton_imprimer.config(command=imprimer_action)

    fenetre.mainloop()


if __name__ == "__main__":
    lancer()
