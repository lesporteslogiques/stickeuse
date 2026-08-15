"""programme_a.py — Stickeuse QL-570, l'application d'impression (fenêtre).

Programme A OUVRE une fenêtre et ne sert qu'à imprimer. Il s'appuie sur le cœur
(détection, validation, impression) et sur le journal — il ne réinvente rien.
Deux écrans :
  1) un accueil-checklist (garde-fou humain), pendant lequel on lance C1 + C2 ;
  2) la fenêtre principale : choisir un PNG (validé à la volée), un nombre
     d'exemplaires, puis imprimer — avec possibilité d'annuler les exemplaires
     qui restent.

Programme A complet : A1 (accueil) · A2 (mise en page) · A3 (comportement).

Les termes d'interface (widget, Tk, pack, Frame, fil d'exécution…) sont définis
dans docs/lexique.md.

Auteurice : Vitally LUBIN — FabLab Les Portes Logiques (2026) — AGPL-3.0.
"""

import os                            # os.path.basename : le nom d'un fichier sans son chemin
import shutil                        # shutil.which : retrouver une commande système (gimp, flatpak…)
import subprocess                    # lancer une commande externe et lire sa réponse
import threading                     # fils d'exécution : imprimer sans figer la fenêtre
import tkinter as tk                 # Tkinter : la boîte à outils d'interface graphique du standard Python
from tkinter import filedialog       # la fenêtre standard « choisir un fichier »
from pathlib import Path             # chemins manipulés comme des objets
from PIL import Image, ImageDraw, ImageTk   # Pillow : ouvrir, dessiner, et rendre affichable par Tkinter

import coeur                         # le moteur : determiner_cible, valider_png, imprimer, ETIQUETTE…
from journal import obtenir_journal  # le journal partagé du poste


# La checklist est coupée en deux : entre les deux moitiés s'insère la ligne du
# rouleau, dont le texte n'est pas fixe — il suit le rouleau choisi juste au-dessus.
CHECKLIST_DEBUT = [
    "L'imprimante Brother QL-570 est branchée sur le secteur.",
    "Elle est sous tension (voyant vert allumé).",
]
CHECKLIST_FIN = [
    "Il y a assez d'étiquettes pour le projet.",
]

# Icône de l'appli, cherchée À CÔTÉ de ce fichier (rien en dur) : après
# installation, programme_a.py et l'icône vivent ensemble dans /opt/ql570/.
# Même principe que dans programme_b.py. Absente → on s'en passe.
ICONE = Path(__file__).resolve().parent / "stickeuseql570.png"

# Part de la LARGEUR d'écran occupée par les fenêtres. On ne fixe pas une taille
# en pixels : elle serait minuscule sur un grand écran et débordante sur un petit.
# La HAUTEUR, elle, n'est pas imposée : elle est prise sur le contenu une fois
# les widgets posés (voir ajuster_au_contenu). Une hauteur imposée laissait un
# grand vide sous le dernier élément.
LARGEUR_ACCUEIL = 0.40
LARGEUR_PRINCIPALE = 0.50

# ── Le réglage de taille de l'interface ─────────────────────────────────────
#
# TAILLE_BASE est la taille du texte, en points (1 point = 1/72 de pouce). TOUT
# en dérive : les variantes de police (titre, état, pied de page), la taille des
# cases à cocher, de l'icône et de l'aperçu. Un seul chiffre à changer.
#
# Une tentative écartée, pour mémoire : régler le facteur d'échelle de Tk
# (« tk scaling »). Il ne change rien aux cases à cocher — sous X11, Tk dessine
# leur indicateur à une taille fixe, que ni la police ni l'échelle ne font
# bouger. D'où les images de cases fabriquées plus bas.
TAILLE_BASE = 14


def largeur_voulue(fenetre, part):
    """Renvoie la largeur de fenêtre souhaitée : une part de celle de l'écran."""
    return int(fenetre.winfo_screenwidth() * part)


def hauteur_ligne(fenetre):
    """Hauteur réelle, EN PIXELS, d'une ligne de texte de l'interface.

    Pourquoi mesurer au lieu de calculer : une taille de police est donnée en
    POINTS, et Tk les convertit en pixels selon la densité de l'écran. Sur un
    écran haute densité, 14 points font ~50 pixels ; sur un écran ordinaire,
    ~19. Tout ce qui se mesure en pixels — cases à cocher, largeur de coupe des
    messages, icône, aperçu — doit donc être déduit de CETTE mesure, sinon ces
    éléments restent petits pendant que le texte grandit. C'est exactement le
    défaut qu'on avait : des cases de 25 pixels à côté d'un texte de 50.

    « linespace » est la hauteur qu'occupe une ligne complète, interligne inclus."""
    return int(fenetre.tk.call("font", "metrics", "TkDefaultFont", "-linespace"))


def images_cases(cote):
    """Fabrique les deux images d'une case à cocher : vide, puis cochée.

    Pourquoi les dessiner au lieu d'utiliser la case native de Tk : celle-ci a
    une taille fixe, minuscule, qui ne suit ni la police ni le facteur d'échelle.
    Sur une checklist qu'on doit lire d'un coup d'œil, elle devient illisible dès
    qu'on grossit le texte. Une image, elle, se dessine à la taille qu'on veut.

    On dessine en QUADRUPLE, puis on réduit : les bords obliques du ✓ sont ainsi
    lissés au lieu d'être en escalier (c'est de l'anticrénelage fait à la main).

    Renvoie deux PhotoImage. ATTENTION : l'appelant doit GARDER une référence
    vers elles, sinon le ramasse-miettes de Python les supprime et les cases
    apparaissent vides."""
    f = 4                                  # facteur de dessin, réduit ensuite
    grand = cote * f
    marge = max(2, grand // 8)

    def carre():
        """Le fond commun : un carré blanc bordé de gris."""
        img = Image.new("RGBA", (grand, grand), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([marge, marge, grand - marge, grand - marge],
                    fill="white", outline="#555", width=max(2, grand // 24))
        return img, d

    vide, _ = carre()
    cochee, d = carre()
    # Le ✓ : deux segments, de la gauche vers le bas, puis vers le haut à droite.
    epaisseur = max(3, grand // 8)
    d.line([(grand * 0.28, grand * 0.52),
            (grand * 0.45, grand * 0.70),
            (grand * 0.74, grand * 0.30)],
           fill="#2e7d32", width=epaisseur, joint="curve")

    return (ImageTk.PhotoImage(vide.resize((cote, cote), Image.LANCZOS)),
            ImageTk.PhotoImage(cochee.resize((cote, cote), Image.LANCZOS)))


def images_ronds(cote):
    """Fabrique les deux images d'un bouton rond : vide, puis choisi.

    Même raison que pour les cases à cocher : l'indicateur natif de Tk a une
    taille fixe, minuscule dès qu'on grossit le texte.

    Rond et non carré, à dessein : la forme dit la règle. Une case carrée se
    coche indépendamment des autres ; un rond signale un choix EXCLUSIF — un
    seul rouleau est chargé dans la machine à un instant donné."""
    f = 4                                  # dessiné en quadruple, puis réduit
    grand = cote * f
    marge = max(2, grand // 8)
    trait = max(2, grand // 24)

    def cercle():
        img = Image.new("RGBA", (grand, grand), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([marge, marge, grand - marge, grand - marge],
                  fill="white", outline="#555", width=trait)
        return img, d

    vide, _ = cercle()
    choisi, d = cercle()
    creux = grand // 4                     # le point central, plus petit que le cercle
    d.ellipse([creux, creux, grand - creux, grand - creux], fill="#2e7d32")

    return (ImageTk.PhotoImage(vide.resize((cote, cote), Image.LANCZOS)),
            ImageTk.PhotoImage(choisi.resize((cote, cote), Image.LANCZOS)))


def poser_choix(parent, texte, variable, valeur, images, commande=None,
                famille=None, taille=None, actif=True):
    """Pose un bouton de choix exclusif, avec NOS images rondes.

    Même principe que poser_case, mais sur un Radiobutton : tous ceux qui
    partagent la même « variable » s'excluent mutuellement, et « valeur » est ce
    que la variable prend quand on choisit celui-ci."""
    fond = parent.cget("bg")
    choix = tk.Radiobutton(
        parent, text=" " + texte, variable=variable, value=valeur, command=commande,
        image=images[0], selectimage=images[1], compound="left",
        indicatoron=False,                 # pas d'indicateur natif : nos images le remplacent
        relief="flat", offrelief="flat", overrelief="flat",
        highlightthickness=0, borderwidth=0,
        bg=fond, activebackground=fond, selectcolor=fond,
        anchor="w", justify="left",
    )
    if famille is not None:
        choix.config(font=(famille, taille))
    if not actif:
        # Grisé et non cliquable : le choix EXISTE (on sait qu'il est prévu),
        # mais on ne peut pas le faire aujourd'hui. Le masquer laisserait croire
        # à un oubli ; le laisser actif ferait échouer l'impression après coup,
        # une fois l'image déjà fabriquée.
        choix.config(state="disabled", disabledforeground="#999")
    return choix


def poser_case(parent, texte, variable, images, commande=None, gras=False,
               famille=None, taille=None):
    """Pose une case à cocher qui utilise NOS images plutôt que celle de Tk.

    indicatoron=False dit à Tk de ne pas dessiner sa propre case ; c'est alors
    l'image (image / selectimage) qui la remplace. Ce mode transforme aussi le
    widget en bouton-bascule : on remet donc les reliefs à plat et la couleur de
    sélection à celle du fond, pour retrouver l'aspect d'une simple ligne."""
    fond = parent.cget("bg")
    # texte peut être une chaîne figée, ou une variable Tkinter dont le contenu
    # change en cours de route (la ligne « rouleau chargé » suit le choix fait
    # juste au-dessus). On branche l'une ou l'autre selon ce qu'on reçoit.
    libelle = {"textvariable": texte} if isinstance(texte, tk.StringVar) \
        else {"text": " " + texte}
    case = tk.Checkbutton(
        parent, variable=variable, command=commande, **libelle,
        image=images[0], selectimage=images[1], compound="left",
        indicatoron=False,                 # pas d'indicateur natif : nos images le remplacent
        relief="flat", offrelief="flat", overrelief="flat",
        highlightthickness=0, borderwidth=0,
        bg=fond, activebackground=fond, selectcolor=fond,
        anchor="w", justify="left",
    )
    if famille is not None:                # sinon : on garde la police par défaut
        case.config(font=(famille, taille, "bold") if gras else (famille, taille))
    return case


def harmoniser_polices(fenetre):
    """Donne la même police, à la même taille, à TOUT ce que Tk dessine.

    Tk range ses polices sous des noms (TkDefaultFont, TkMenuFont…) et s'en sert
    partout, y compris dans les fenêtres qu'on n'a pas écrites : le sélecteur de
    fichiers, les messages, les menus. Les régler ici, c'est régler l'interface
    entière d'un coup — au lieu d'habiller nos widgets un par un et de laisser le
    reste dépareillé.

    Renvoie la famille de police retenue, pour construire les variantes (titre en
    gras, pied de page plus petit) dans la MÊME famille."""
    noms = ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
            "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont")
    for nom in noms:
        try:
            # On parle à Tcl directement plutôt que par tkinter.font : l'ordre
            # s'applique ainsi à CETTE fenêtre, sans ambiguïté — l'appli en ouvre
            # deux l'une après l'autre, et la première est détruite entre-temps.
            fenetre.tk.call("font", "configure", nom, "-size", TAILLE_BASE)
        except tk.TclError:
            pass          # police absente sur ce système : les autres suffisent

    famille = fenetre.tk.call("font", "actual", "TkDefaultFont", "-family")


    return famille


def agrandir_selecteur(fenetre):
    """Agrandit la fenêtre « Choisir un PNG » dès qu'elle apparaît.

    Cette fenêtre-là, on ne la construit pas : c'est Tk qui la fabrique quand on
    appelle askopenfilename. Elle s'ouvre petite, ce qui est fâcheux pour LA
    fenêtre où l'on cherche justement quelque chose. On ne peut pas la régler à
    l'avance, mais on peut la retrouver une fois ouverte et lui donner une
    taille : Tk la nomme « .__tk_filedialog ».

    Appelée un court instant APRÈS l'ouverture, via after() : au moment où l'on
    demande la fenêtre, elle n'existe pas encore. Si le nom change selon les
    versions de Tk, on cherche parmi les fenêtres ouvertes celle dont le nom
    évoque un sélecteur ; et si l'on ne trouve rien, on renonce sans bruit —
    l'appli marche, la fenêtre est seulement plus petite."""
    noms = [".__tk_filedialog"]
    try:
        # splitlist : Tcl rend ses listes sous forme de chaîne ; sans elle, on
        # parcourrait les CARACTÈRES de cette chaîne au lieu des fenêtres.
        for enfant in fenetre.tk.splitlist(fenetre.tk.call("winfo", "children", ".")):
            nom = str(enfant)
            if "filedialog" in nom or "fdialog" in nom:
                noms.append(nom)
    except tk.TclError:
        pass

    for nom in noms:
        try:
            # « winfo exists » répond "0" ou "1" — des CHAÎNES, toutes deux vraies
            # en Python. D'où la conversion en entier : sans elle, le test ne
            # détecterait jamais une fenêtre absente.
            if not int(fenetre.tk.call("winfo", "exists", nom)):
                continue
            ecran_l = fenetre.winfo_screenwidth()
            ecran_h = fenetre.winfo_screenheight()
            largeur, hauteur = int(ecran_l * 0.55), int(ecran_h * 0.65)
            x, y = (ecran_l - largeur) // 2, (ecran_h - hauteur) // 2
            fenetre.tk.call("wm", "geometry", nom, f"{largeur}x{hauteur}+{x}+{y}")
            fenetre.tk.call("wm", "resizable", nom, 1, 1)   # et libre de l'agrandir encore
            return
        except tk.TclError:
            continue          # fenêtre disparue entre-temps : rien à faire


def message(parent, titre, texte, genre="info"):
    """Affiche une fenêtre-message, et attend que la personne la ferme.

    Pourquoi ne pas utiliser messagebox, la fenêtre toute faite de Tkinter :
    sous Linux, elle fixe sa largeur de coupe (le point où le texte revient à la
    ligne) à un peu moins de 8 cm, décidés à sa création. Quand on agrandit les
    polices, le texte grossit mais la colonne reste étroite : « 2 étiquette(s)
    imprimée(s). » se retrouve coupé en trois lignes. Et comme cette largeur est
    figée, agrandir la fenêtre à la main n'y change rien.

    En l'écrivant nous-mêmes, on choisit la largeur de coupe, on garde la police
    de l'appli, et on interdit le redimensionnement — puisqu'il ne servait à rien.

    genre : "info", "avert" ou "erreur" ; ne change que la couleur du titre."""
    couleurs = {"info": "#2e7d32", "avert": "#b35c00", "erreur": "#b00020"}
    famille = parent.tk.call("font", "actual", "TkDefaultFont", "-family")
    ligne = hauteur_ligne(parent)              # en pixels réels, densité d'écran comprise

    fen = tk.Toplevel(parent)
    # La barre de fenêtre porte le nom de l'appli, pas le titre du message :
    # celui-ci est déjà écrit en gros dans la fenêtre, et le répéter deux fois
    # à trois centimètres d'écart n'apprend rien à personne.
    fen.title("Stickeuse QL-570")
    fen.transient(parent)          # fenêtre fille : elle reste au-dessus de l'appli
    fen.resizable(False, False)    # rien à gagner à l'agrandir : sa taille suit son texte

    tk.Label(fen, text=titre, font=(famille, TAILLE_BASE + 1, "bold"),
             fg=couleurs.get(genre, "#333")).pack(padx=28, pady=(20, 8), anchor="w")
    # wraplength en PIXELS. On le déduit de la hauteur MESURÉE d'une ligne :
    # ~24 lignes de large, soit une colonne confortable quelle que soit la
    # densité de l'écran. Le déduire du nombre de points donnait une colonne
    # deux fois trop étroite sur un écran fin.
    tk.Label(fen, text=texte, wraplength=ligne * 24,
             justify="left").pack(padx=28, pady=(0, 16), anchor="w")
    bouton = tk.Button(fen, text="OK", width=10, command=fen.destroy)
    bouton.pack(pady=(0, 20))

    fen.bind("<Return>", lambda evenement: fen.destroy())    # Entrée ferme aussi
    fen.bind("<Escape>", lambda evenement: fen.destroy())
    bouton.focus_set()

    # Centrer sur la fenêtre de l'appli : update_idletasks force le calcul de la
    # taille avant qu'on s'en serve, sinon elle vaudrait encore 1×1.
    fen.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - fen.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - fen.winfo_height()) // 3
    fen.geometry(f"+{max(0, x)}+{max(0, y)}")

    fen.grab_set()                 # modale : les clics vont à elle seule
    fen.wait_window()              # on ne rend la main qu'à sa fermeture


def ajuster_au_contenu(fenetre, largeur):
    """Donne à la fenêtre sa taille définitive, puis la centre. À appeler UNE
    FOIS tous les widgets posés, juste avant mainloop().

    La largeur est celle qu'on veut (une part de l'écran) ; la HAUTEUR est prise
    sur le contenu — la place que les widgets réclament, ni plus ni moins. Une
    hauteur imposée à l'avance laisse un vide sous le dernier élément si le
    contenu est court, et coupe le bouton du bas s'il est long.

    winfo_req… donne cette place réclamée ; update_idletasks force Tkinter à la
    calculer maintenant, sinon elle vaudrait encore 1×1."""
    fenetre.update_idletasks()
    largeur = max(largeur, fenetre.winfo_reqwidth())      # jamais plus étroit que le contenu
    hauteur = fenetre.winfo_reqheight()
    ecran_l, ecran_h = fenetre.winfo_screenwidth(), fenetre.winfo_screenheight()
    largeur, hauteur = min(largeur, ecran_l), min(hauteur, ecran_h)
    x = (ecran_l - largeur) // 2
    y = (ecran_h - hauteur) // 2
    fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")


def gimp_installe():
    """Dit si GIMP est disponible sur ce poste (paquet système ou Flatpak).

    GIMP n'est PAS une dépendance de l'appli : c'est l'outil avec lequel
    l'utilisateur FABRIQUE l'image de son étiquette. Sans lui, la Stickeuse
    imprime encore très bien un PNG venu d'ailleurs — d'où un simple
    avertissement, jamais un blocage.

    Deux façons d'installer GIMP sur Debian, donc deux vérifications : le paquet
    système (qui pose une commande « gimp » dans le PATH) et Flatpak (qui n'en
    pose aucune : il faut interroger sa liste d'applications)."""
    for nom in ("gimp", "gimp-3.0", "gimp-2.10"):
        if shutil.which(nom):
            return True
    flatpak = shutil.which("flatpak")
    if flatpak is not None:
        try:
            resultat = subprocess.run(
                [flatpak, "list", "--app", "--columns=application"],
                capture_output=True, text=True, timeout=5,
            )
            if "org.gimp.GIMP" in resultat.stdout:
                return True
        except (OSError, subprocess.SubprocessError):
            pass      # flatpak injoignable : on conclut simplement « pas trouvé »
    return False


def dossier_images():
    """Renvoie le dossier « Images » de l'utilisateur, quelle que soit sa langue.

    On ne code pas « ~/Images » en dur : ce dossier s'appelle Pictures, Bilder,
    Imágenes… selon la langue du poste. La commande « xdg-user-dir », standard
    sur les bureaux Linux, donne le bon chemin. Si elle manque ou échoue, on se
    rabat sur le dossier personnel — jamais d'erreur pour si peu."""
    outil = shutil.which("xdg-user-dir")
    if outil is not None:
        try:
            resultat = subprocess.run([outil, "PICTURES"],
                                      capture_output=True, text=True, timeout=5)
            chemin = Path(resultat.stdout.strip())
            if chemin.is_dir():
                return str(chemin)
        except (OSError, subprocess.SubprocessError):
            pass
    return str(Path.home())


def lancer():
    """Point d'entrée : enchaîne les deux écrans. L'accueil renvoie la cible
    (imprimante prête) ; sans cible (échec ou fenêtre fermée), on s'arrête."""
    journal = obtenir_journal()
    journal.info("Lancement Programme A")
    cible, etiquette = ecran_accueil(journal)
    if cible is None:
        journal.info("Arrêt après l'accueil (échec ou fermeture).")
        return
    fenetre_principale(journal, cible, etiquette)


def ecran_accueil(journal):
    """Écran « Bienvenue ! » : choix du rouleau + checklist + OK. Au clic OK
    (tout coché), on lance C1 + C2.

    Renvoie le couple (Cible, Etiquette) : où est l'imprimante, et quel rouleau
    la personne déclare avoir chargé. En cas d'échec ou de fermeture de la
    fenêtre, renvoie (None, None) — l'appelant n'a qu'un test à faire."""
    resultat = {"cible": None,                 # un « casier » pour rapporter la cible hors du callback
                "etiquette": None,             # …le rouleau déclaré chargé…
                "images": None}                # …et pour garder en vie les images des cases

    # className : le nom sous lequel la fenêtre se présente au bureau. C'est lui
    # que le fichier .desktop reprend dans « StartupWMClass », et c'est ainsi que
    # le dock reconnaît l'appli en cours d'exécution (icône et nom corrects) au
    # lieu de l'afficher comme une fenêtre anonyme.
    # La valeur ci-dessous est celle que Tk produit RÉELLEMENT, vérifiée avec
    # « xprop WM_CLASS » sur la fenêtre ouverte. Tk ne se contente pas de mettre
    # une majuscule à la première lettre : il passe aussi tout le reste en
    # MINUSCULES. Un « Stickeuse-QL570 » demandé ressort donc en
    # « Stickeuse-ql570 » — et le .desktop, s'il annonçait l'autre graphie, ne
    # correspondrait à rien. D'où ce nom déjà écrit sous sa forme d'arrivée :
    # quoi que fasse Tk, il ne peut plus le changer.
    fenetre = tk.Tk(className="Stickeuse-ql570")
    fenetre.title("Stickeuse QL-570 — Bienvenue !")
    largeur = largeur_voulue(fenetre, LARGEUR_ACCUEIL)
    famille = harmoniser_polices(fenetre)      # une police commune à TOUT Tk
    police_titre = (famille, TAILLE_BASE + 2, "bold")
    police_note = (famille, TAILLE_BASE - 2)
    cote_case = int(hauteur_ligne(fenetre) * 1.1)   # la case suit la hauteur RÉELLE du texte
    cases_images = images_cases(cote_case)
    ronds_images = images_ronds(cote_case)
    resultat["images"] = (cases_images, ronds_images)   # références gardées : sinon, images vides

    # ── Quel rouleau est chargé ? ──
    # La QL-570 ne sait PAS le dire : rien dans le protocole ne renseigne le
    # rouleau présent. C'est donc à l'humain de le déclarer — et c'est bien la
    # place de cette question, au milieu des autres vérifications qu'on ne peut
    # pas automatiser. Un mauvais choix ne produit aucune erreur : juste une
    # étiquette mal cadrée, et une image refusée pour ses dimensions.
    # Le rouleau proposé au départ doit être utilisable : si celui du catalogue
    # devenait indisponible, on prend le premier qui ne l'est pas.
    defaut = coeur.ETIQUETTE.identifiant
    if coeur.ETIQUETTES[defaut].indisponible:
        defaut = next((c for c, e in coeur.ETIQUETTES.items() if not e.indisponible),
                      defaut)
    rouleau = tk.StringVar(value=defaut)

    tk.Label(fenetre, text="Quel rouleau est chargé dans la machine ?",
             font=police_titre).pack(padx=20, pady=(20, 8))

    ligne_rouleau = tk.StringVar()
    coche_rouleau = tk.BooleanVar()
    dernier_rouleau = {"cle": rouleau.get()}   # ce qui était choisi juste avant

    def sur_choix_rouleau():
        """Met à jour la ligne de checklist qui décrit le rouleau, et la décoche
        si l'on a VRAIMENT changé de rouleau.

        « Vraiment » : recliquer sur le rouleau déjà choisi déclenche aussi cette
        fonction, mais ne défait rien — une confirmation donnée n'a pas à être
        annulée par un geste qui ne change rien. En revanche, passer d'un rouleau
        à l'autre après avoir confirmé son chargement, c'est précisément le
        moment où la confirmation ne vaut plus rien."""
        etiquette = coeur.ETIQUETTES[rouleau.get()]
        ligne_rouleau.set(f" Le rouleau {etiquette.libelle} est chargé "
                          f"({etiquette.largeur} × {etiquette.hauteur} px).")
        if rouleau.get() != dernier_rouleau["cle"]:
            coche_rouleau.set(False)
            dernier_rouleau["cle"] = rouleau.get()
        suivre_les_cases()

    for cle, etiquette in coeur.ETIQUETTES.items():
        poser_choix(fenetre, etiquette.libelle, rouleau, cle, ronds_images,
                    commande=sur_choix_rouleau, actif=not etiquette.indisponible,
                    famille=famille, taille=TAILLE_BASE).pack(fill="x", padx=40)
        if etiquette.indisponible:
            # La raison, juste sous le rouleau concerné : sans elle, un bouton
            # grisé ressemble à une panne de l'appli.
            tk.Label(fenetre, text=f"     indisponible — {etiquette.indisponible}",
                     fg="#b35c00", font=police_note,
                     anchor="w").pack(fill="x", padx=40)

    # ── La checklist ──
    tk.Label(fenetre, text="Avant de commencer, vérifie :",
             font=police_titre).pack(padx=20, pady=(22, 10))
    cases = [tk.BooleanVar() for _ in CHECKLIST_DEBUT] + [coche_rouleau] \
        + [tk.BooleanVar() for _ in CHECKLIST_FIN]

    tout = tk.BooleanVar()                     # l'état de la case « Tout cocher »

    def basculer_tout():
        """« Tout cocher » : on applique son état à toutes les autres cases."""
        for coche in cases:
            coche.set(tout.get())

    def suivre_les_cases():
        """L'inverse : « Tout cocher » se décoche dès qu'une case ne l'est plus,
        et se coche dès qu'elles le sont toutes. Sans ça, elle afficherait un
        état faux — et une interface qui ment est pire qu'une interface pauvre."""
        tout.set(all(coche.get() for coche in cases))

    poser_case(fenetre, "Tout cocher", tout, cases_images, commande=basculer_tout,
               gras=True, famille=famille, taille=TAILLE_BASE).pack(fill="x", padx=20, pady=(0, 6))

    # Les libellés dans l'ordre d'affichage : la ligne du rouleau est une variable
    # (son texte change), les autres sont des chaînes figées.
    libelles = CHECKLIST_DEBUT + [ligne_rouleau] + CHECKLIST_FIN
    for texte, coche in zip(libelles, cases):
        poser_case(fenetre, texte, coche, cases_images, commande=suivre_les_cases,
                   famille=famille, taille=TAILLE_BASE).pack(fill="x", padx=40)

    sur_choix_rouleau()                        # remplit la ligne du rouleau par défaut

    # GIMP absent → on le signale ICI, avant que la personne ne parte chercher
    # son image : c'est le moment utile. Message de niveau N2 (le responsable du
    # FabLab installe), sans jargon, avec la commande exacte à lui transmettre.
    if not gimp_installe():
        journal.warning("GIMP non détecté sur ce poste.")
        tk.Label(
            fenetre,
            text=("GIMP n'est pas installé sur ce poste.\n"
                  "Il sert à fabriquer l'image de l'étiquette — l'impression, elle,\n"
                  "fonctionne quand même avec un PNG venu d'ailleurs.\n"
                  "Pour l'installer, demander au responsable du FabLab :\n"
                  "apt install gimp"),
            fg="#b35c00", font=police_note, justify="left",
        ).pack(padx=20, pady=(12, 0))

    def sur_ok():
        if not all(case.get() for case in cases):
            message(fenetre, "Checklist", "Coche d'abord tous les points.", "avert")
            return
        try:
            cible = coeur.determiner_cible()   # C1 + C2
        except coeur.ErreurStickeuse as e:
            journal.error(f"{e.code} {e}")
            message(fenetre, f"Problème [{e.code}]", str(e), "erreur")
            return                             # on n'ouvre pas la suite ; resultat["cible"] reste None
        etiquette = coeur.ETIQUETTES[rouleau.get()]
        journal.info(f"Accueil validé · cible : {cible} · rouleau : {etiquette.libelle}")
        resultat["cible"] = cible
        resultat["etiquette"] = etiquette
        fenetre.destroy()                      # ferme l'accueil → fin de SON mainloop

    tk.Button(fenetre, text="OK", command=sur_ok, width=12).pack(pady=20)

    ajuster_au_contenu(fenetre, largeur)       # la hauteur suit le contenu, sans vide inutile
    # Une checklist n'a rien à gagner à s'étirer : sa taille est celle de son
    # contenu, et l'agrandir n'ajouterait que du vide. On l'interdit donc.
    fenetre.resizable(False, False)
    fenetre.mainloop()                         # bloque ici jusqu'à destroy() ou fermeture
    return resultat["cible"], resultat["etiquette"]


def fenetre_principale(journal, cible, etiquette):
    """La fenêtre d'impression : choisir un PNG (validé), un nombre, imprimer."""
    fenetre = tk.Tk(className="Stickeuse-ql570")   # second écran = sa propre fenêtre racine
    fenetre.title("Stickeuse QL-570")
    largeur = largeur_voulue(fenetre, LARGEUR_PRINCIPALE)
    famille = harmoniser_polices(fenetre)
    police_titre = (famille, TAILLE_BASE + 7, "bold")
    police_etat = (famille, TAILLE_BASE + 1)
    police_pied = (famille, TAILLE_BASE - 3)

    etat = {"chemin": None,                    # le PNG validé prêt à imprimer (None tant qu'aucun)
            "apercu": None,                    # la PhotoImage de l'aperçu : on la GARDE ici pour que
                                               # le ramasse-miettes ne la supprime pas (sinon aperçu blanc)
            "icone": None,                     # idem pour l'icône de l'en-tête
            "annulation": None,                # l'« interrupteur » d'annulation de l'impression en cours
            "rendez_vous": None}               # le redessin d'aperçu programmé (anti-rebond)

    # ── En-tête : icône + titre + état de l'imprimante ──
    if ICONE.exists():                         # dégradation douce : sans le fichier, pas d'icône
        image_icone = Image.open(ICONE)
        cote_icone = hauteur_ligne(fenetre) * 3
        if image_icone.width < cote_icone:
            # L'icône source est petite (48×48). Pour l'agrandir sans la rendre
            # floue, on multiplie par un facteur ENTIER en mode NEAREST : chaque
            # pixel devient un carré net de N×N. Un agrandissement lissé, lui,
            # baverait — et sur un logo à angles droits, ça se voit tout de suite.
            facteur = max(1, cote_icone // image_icone.width)
            image_icone = image_icone.resize(
                (image_icone.width * facteur, image_icone.height * facteur),
                Image.NEAREST)
        else:
            image_icone.thumbnail((cote_icone, cote_icone), Image.LANCZOS)
        etat["icone"] = ImageTk.PhotoImage(image_icone)   # référence gardée dans etat
        tk.Label(fenetre, image=etat["icone"]).pack(pady=(14, 0))
    tk.Label(fenetre, text="Stickeuse QL-570",
             font=police_titre).pack(pady=(8, 2))
    tk.Label(fenetre, text=f"{cible.modele} prête", fg="#2e7d32",
             font=police_etat).pack(pady=(0, 2))
    # On rappelle le rouleau déclaré : c'est lui qui décide des dimensions
    # acceptées, et l'oublier est l'erreur la plus probable de toute l'appli.
    tk.Label(fenetre, text=f"Rouleau {etiquette.libelle}  ·  "
                           f"{etiquette.largeur} × {etiquette.hauteur} px",
             fg="#555", font=police_pied).pack(pady=(0, 12))

    # ── Section « Fichier à imprimer » ──
    nom_fichier = tk.StringVar(value="Aucun fichier sélectionné")  # variable texte reliée au Label
    cadre_fichier = tk.Frame(fenetre)
    cadre_fichier.pack(fill="x", padx=20, pady=6)
    tk.Label(cadre_fichier, text="Fichier à imprimer :").pack(anchor="w")
    ligne = tk.Frame(cadre_fichier)
    ligne.pack(fill="x", pady=4)
    bouton_parcourir = tk.Button(ligne, text="Parcourir…")
    bouton_parcourir.pack(side="left")         # sa command est câblée plus bas
    tk.Label(ligne, textvariable=nom_fichier, fg="#555").pack(side="left", padx=10)

    # ── Zone d'aperçu (sous « Parcourir », au-dessus d'« Imprimer ») ──
    # Un cadre de taille FIXE, qui réserve la place de la vignette dès le
    # lancement. Sans cette réservation, la fenêtre — dont la hauteur est prise
    # sur le contenu — serait calculée sans l'aperçu, et la vignette se
    # retrouverait coupée dès qu'on choisit un fichier.
    # pack_propagate(False) est ce qui empêche le cadre de se redimensionner sur
    # son contenu : sans cet ordre, un cadre vide retomberait à une taille nulle.
    cote_apercu = hauteur_ligne(fenetre) * 14
    cadre_apercu = tk.Frame(fenetre, width=cote_apercu, height=cote_apercu)
    # expand=True + fill="both" : ce cadre est le SEUL à réclamer la place
    # supplémentaire quand on agrandit la fenêtre. Les autres sections gardent
    # leur taille ; c'est l'étiquette qu'on veut voir en grand, pas les libellés.
    cadre_apercu.pack(pady=8, expand=True, fill="both")
    cadre_apercu.pack_propagate(False)
    apercu = tk.Label(cadre_apercu)            # pas d'image au départ
    apercu.pack(expand=True)

    # ── Section « Nombre d'exemplaires » ──
    cadre_nb = tk.Frame(fenetre)
    cadre_nb.pack(fill="x", padx=20, pady=6)
    tk.Label(cadre_nb, text="Nombre d'exemplaires :").pack(side="left")
    exemplaires = tk.Spinbox(cadre_nb, from_=1, to=99, width=4)    # sélecteur numérique, défaut 1
    exemplaires.pack(side="left", padx=8)
    tk.Label(cadre_nb, text="étiquette(s)").pack(side="left")

    # ── Boutons « Imprimer » et « Annuler » (côte à côte) ──
    cadre_boutons = tk.Frame(fenetre)
    cadre_boutons.pack(pady=16)
    bouton_imprimer = tk.Button(cadre_boutons, text="Imprimer", bg="#2e7d32", fg="white",
                                state="disabled", width=16)
    bouton_imprimer.pack(side="left", padx=6)
    # « Annuler » n'est actif QUE pendant une impression : hors de là, il n'y a
    # rien à annuler, et un bouton cliquable sans effet est un mensonge d'interface.
    bouton_annuler = tk.Button(cadre_boutons, text="Annuler", width=12,
                               state="disabled")
    bouton_annuler.pack(side="left", padx=6)

    # ── Ligne d'état : où en est l'impression ──
    statut = tk.StringVar(value="")
    tk.Label(fenetre, textvariable=statut, fg="#555").pack(pady=(0, 4))

    # ── Pied de page ──
    tk.Label(fenetre,
             text="© 2026 Vitally LUBIN · FabLab Les Portes Logiques · AGPL-3.0",
             fg="#888", font=police_pied).pack(side="bottom", pady=(8, 12))

    # ── Comportements (A3) : on relie les boutons à du code, une fois la mise
    #    en page construite. C'est .config(command=…) qui fait ce branchement. ──

    def dessiner_apercu(chemin_png):
        """Redessine la vignette à la taille ACTUELLE du cadre d'aperçu.

        On repart chaque fois du fichier d'origine plutôt que d'agrandir la
        vignette précédente : une image déjà réduite puis regrossie devient
        floue, alors que l'original garde tous ses détails."""
        largeur_cadre = max(cadre_apercu.winfo_width(), 1)
        hauteur_cadre = max(cadre_apercu.winfo_height(), 1)
        try:
            image = Image.open(chemin_png)
            # On calcule le rapport d'agrandissement dans les deux sens et on
            # garde le PLUS PETIT : c'est lui qui fait tenir l'image entière
            # dans le cadre, sans la déformer ni la déborder.
            #
            # thumbnail() ne conviendrait pas seule : elle ne sait que RÉDUIRE.
            # Une fois la fenêtre plus large que l'image (991 px), il n'y aurait
            # plus rien à réduire et la vignette resterait petite au milieu du
            # vide — précisément ce qu'on veut éviter en agrandissant la fenêtre.
            rapport = min(largeur_cadre / image.width, hauteur_cadre / image.height)
            image = image.resize(
                (max(1, int(image.width * rapport)),
                 max(1, int(image.height * rapport))),
                Image.LANCZOS)
        except OSError:
            # Le fichier a été effacé, déplacé ou débranché depuis qu'on l'a
            # choisi : on efface la vignette au lieu de laisser une erreur
            # remonter d'un redessin que personne n'a demandé.
            apercu.config(image="")
            etat["apercu"] = None
            return
        photo = ImageTk.PhotoImage(image)      # version affichable par Tkinter
        apercu.config(image=photo)
        etat["apercu"] = photo                 # ← on GARDE la référence (sinon ramasse-miettes → aperçu blanc)

    def sur_redimensionnement(evenement):
        """Le cadre d'aperçu a changé de taille → on refait la vignette.

        L'événement <Configure> arrive à CHAQUE pixel de déplacement pendant
        qu'on tire un coin de la fenêtre : redessiner à chaque fois saccaderait.
        On attend donc 150 ms de calme avant de redessiner, et toute nouvelle
        secousse annule le rendez-vous précédent — c'est un « anti-rebond »."""
        if etat["chemin"] is None:
            return
        if etat["rendez_vous"] is not None:
            fenetre.after_cancel(etat["rendez_vous"])
        def redessiner():
            etat["rendez_vous"] = None         # le rendez-vous est honoré : on l'oublie
            if etat["chemin"] is not None:     # le fichier a pu être désélectionné entre-temps
                dessiner_apercu(etat["chemin"])

        etat["rendez_vous"] = fenetre.after(150, redessiner)

    cadre_apercu.bind("<Configure>", sur_redimensionnement)

    def parcourir():
        """Choisir un fichier → le VALIDER (C3-A) → activer ou non « Imprimer »."""

        def vider_apercu():
            """Efface la vignette (fichier refusé, ou aucun fichier)."""
            apercu.config(image="")            # plus d'image dans le Label
            etat["apercu"] = None              # on lâche la référence gardée

        def montrer_apercu(chemin_png):
            """Affiche une vignette du PNG validé, proportions préservées."""
            dessiner_apercu(chemin_png)

        # La fenêtre n'existe pas encore : on programme son agrandissement pour
        # dans un instant. askopenfilename bloque, mais Tk continue de traiter ses
        # rendez-vous pendant ce temps — c'est ce qui rend l'astuce possible.
        fenetre.after(80, lambda: agrandir_selecteur(fenetre))
        chemin = filedialog.askopenfilename(
            title="Choisir un PNG",
            # On ouvre dans le dossier « Images » : c'est là que GIMP exporte, et
            # là que l'installation dépose la mire de test. La personne trouve
            # ses fichiers du premier coup, au lieu d'atterrir dans son dossier
            # personnel au milieu de tout le reste.
            initialdir=dossier_images(),
            # UNE seule entrée, donc aucun moyen de basculer sur « tous les
            # fichiers » : la fenêtre ne montre que des PNG. Ce n'est pas une
            # sécurité (valider_png vérifie le contenu de toute façon), c'est du
            # confort — on ne propose pas ce qui sera refusé ensuite.
            # Les deux motifs sont là parce que le filtre distingue majuscules et
            # minuscules : sans « *.PNG », un fichier venu de Windows ou d'un
            # appareil photo resterait invisible.
            filetypes=[("Images PNG", "*.png *.PNG")],
        )
        if not chemin:                         # annulé : on ne touche à rien
            return
        nom_fichier.set(os.path.basename(chemin))
        try:
            avertissement = coeur.valider_png(chemin, etiquette)
        except coeur.ErreurStickeuse as e:     # refus DUR (E-C3-1 / E-C3-2)
            journal.warning(f"{e.code} {e}")
            etat["chemin"] = None
            vider_apercu()                     # fichier non imprimable → pas d'aperçu
            bouton_imprimer.config(state="disabled")   # on (re)désactive : fichier non imprimable
            message(fenetre, f"Fichier refusé [{e.code}]", str(e), "erreur")
            return
        # Fichier accepté (avec ou sans avertissement souple) → on peut imprimer.
        etat["chemin"] = chemin
        montrer_apercu(chemin)                 # aperçu seulement APRÈS validation réussie
        bouton_imprimer.config(state="normal")
        if avertissement is not None:          # E-C3-3 : trop de gris, mais non bloquant
            journal.warning(f"{avertissement.code} {avertissement}")
            message(fenetre, f"Avertissement [{avertissement.code}]",
                    f"{avertissement}\nTu peux imprimer quand même.", "avert")
        else:
            journal.info(f"Fichier validé : {chemin}")

    def imprimer_action():
        """Clic « Imprimer » → C3 répété selon le nombre d'exemplaires.

        L'impression part dans un FIL D'EXÉCUTION séparé. Sans cela, la boucle
        occuperait Tkinter du premier au dernier exemplaire : la fenêtre serait
        gelée, et le bouton « Annuler » — précisément celui dont on a besoin —
        impossible à cliquer."""
        chemin = etat["chemin"]
        if chemin is None:                     # garde-fou (le bouton ne devrait pas être actif)
            return
        try:
            nombre = int(exemplaires.get())
        except ValueError:
            nombre = 1                         # saisie bizarre → on retombe sur 1

        # L'« interrupteur » d'annulation : un objet que les deux fils partagent.
        # Le bouton Annuler le lève (.set()) ; le fil d'impression le consulte
        # (.is_set()) avant chaque exemplaire. C'est le moyen prévu pour dire
        # « stop » d'un fil à l'autre, sans variable partagée bricolée.
        annulation = threading.Event()
        etat["annulation"] = annulation

        # Pendant l'impression : on verrouille ce qui n'a plus de sens, on ouvre
        # ce qui en a un.
        bouton_imprimer.config(state="disabled")
        bouton_parcourir.config(state="disabled")
        bouton_annuler.config(state="normal")

        def signaler(fonction, *arguments):
            """Fait exécuter `fonction` par le fil de l'interface.

            Si la fenêtre a été fermée entre-temps, Tkinter proteste (TclError) :
            on ignore alors le message, il n'a plus de destinataire. Sans ce
            filet, fermer la fenêtre pendant une impression ferait mourir le fil
            sur une erreur, en silence et de travers."""
            try:
                fenetre.after(0, fonction, *arguments)
            except tk.TclError:
                pass

        def travail():
            """Ce que fait le fil d'impression. Attention : ce code ne tourne PAS
            dans le fil de l'interface. Il ne doit donc JAMAIS toucher aux widgets
            directement (Tkinter n'est pas prévu pour) ; il passe ses messages par
            signaler(), qui les fait exécuter par le fil de l'interface."""
            faites = 0
            for numero in range(1, nombre + 1):
                if annulation.is_set():        # demande d'arrêt → on ne lance pas le suivant
                    break
                signaler(statut.set, f"Impression {numero} / {nombre}…")
                try:
                    coeur.imprimer(cible, etiquette, chemin)   # une étiquette par appel
                except coeur.ErreurStickeuse as e:
                    signaler(terminer, faites, nombre, e)
                    return
                faites += 1
            signaler(terminer, faites, nombre, None)

        # daemon=True : si la fenêtre est fermée en cours d'impression, ce fil ne
        # retient pas le programme en vie.
        threading.Thread(target=travail, daemon=True).start()

    def terminer(faites, demandees, erreur):
        """Fin d'impression (réussie, annulée ou en erreur) : remettre l'interface
        d'aplomb, journaliser, annoncer. Exécuté dans le fil de l'interface."""
        etat["annulation"] = None
        bouton_imprimer.config(state="normal")
        bouton_parcourir.config(state="normal")
        bouton_annuler.config(state="disabled")
        statut.set("")
        chemin = etat["chemin"]

        if erreur is not None:
            journal.error(f"{erreur.code} {erreur} (après {faites}/{demandees})")
            message(fenetre, f"Échec [{erreur.code}]",
                    f"{erreur}\n\n{faites} étiquette(s) imprimée(s) sur {demandees}.", "erreur")
            return

        if faites < demandees:                 # sortie de boucle avant la fin → annulation
            journal.info(f"Impression annulée : {faites}/{demandees} · {chemin}")
            message(fenetre, "Annulé",
                    f"Impression annulée.\n{faites} étiquette(s) imprimée(s) "
                    f"sur {demandees} demandée(s).", "avert")
            return

        journal.info(f"Imprimé {faites}× : {chemin}")
        message(fenetre, "Imprimé", f"{faites} étiquette(s) imprimée(s).")

    def annuler_action():
        """Clic « Annuler » → on lève l'interrupteur ; le fil d'impression le
        verra avant l'exemplaire suivant.

        Ce qu'on annule, ce sont les exemplaires QUI RESTENT : l'étiquette déjà
        envoyée, elle, sortira — une fois les données parties, la machine les
        imprime et l'appli n'a plus la main dessus. Le message le dit, plutôt que
        de laisser croire à un arrêt immédiat."""
        annulation = etat["annulation"]
        if annulation is None:                 # rien en cours (garde-fou)
            return
        annulation.set()
        bouton_annuler.config(state="disabled")   # une demande suffit
        statut.set("Annulation demandée — l'étiquette en cours se termine…")

    bouton_parcourir.config(command=parcourir)
    bouton_imprimer.config(command=imprimer_action)
    bouton_annuler.config(command=annuler_action)

    ajuster_au_contenu(fenetre, largeur)       # la hauteur suit le contenu, sans vide inutile
    fenetre.mainloop()


if __name__ == "__main__":
    lancer()
