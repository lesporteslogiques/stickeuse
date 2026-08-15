#!/usr/bin/env python3
"""Fabrique les mires de test de la Stickeuse QL-570.

Usage : python3 generer-mire.py [sortie.png] [portrait|paysage] [39x90|62x100]
Defauts : test-stickeuse.png, en portrait, au format 39x90.

Auteurice : Vitally LUBIN - FabLab Les Portes Logiques (2026) - AGPL-3.0.

Formats imposes par les rouleaux predecoupes, en pixels imprimables :
  DK-11208 (38 x 90 mm)  -> 413 x 991 portrait, 991 x 413 paysage
  DK-11202 (62 x 100 mm) -> 696 x 1109 portrait, 1109 x 696 paysage
Toujours en noir et blanc pur (mode 1), 300 ppp. L'appli accepte les deux
orientations : brother_ql pivote lui-meme une image en paysage. Les mires
paysage servent justement a VOIR dans quel sens il les pivote.

Le nom du fichier produit devrait porter la reference du rouleau et les
dimensions en pixels : la fenetre « Parcourir... » de l'appli n'affiche
que ce nom, sans colonne de description possible. Exemple :
    test-stickeuse-DK11208-413x991px-portrait.png
"""

import sys
from PIL import Image, ImageDraw, ImageFont

# Les formats connus, en pixels imprimables (portrait). Mêmes valeurs que le
# catalogue de src/coeur.py : si l'un bouge, l'autre doit suivre.
FORMATS = {
    # identifiant brother_ql : (largeur px, hauteur px, reference, dimensions reelles)
    "39x90": (413, 991, "DK-11208", "38 x 90 mm"),
    "62x100": (696, 1109, "DK-11202", "62 x 100 mm"),
}

L, H = FORMATS["39x90"][:2]   # pixels imprimables (portrait), par defaut
PPP = 300                # points par pouce
MM = PPP / 25.4          # pixels par millimetre
NOIR, BLANC = 0, 1       # en mode "1", un pixel vaut 0 (noir) ou 1 (blanc)

sortie = sys.argv[1] if len(sys.argv) > 1 else "test-stickeuse.png"
orientation = sys.argv[2] if len(sys.argv) > 2 else "portrait"
format_choisi = sys.argv[3] if len(sys.argv) > 3 else "39x90"
if format_choisi not in FORMATS:
    sys.exit("Format inconnu : " + format_choisi + ". Connus : "
             + ", ".join(FORMATS))
L, H, REFERENCE, DIMENSIONS = FORMATS[format_choisi]


def police(taille):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", taille)


def dessiner_portrait(d, L, H):
    """La mire portrait : les controles empiles de haut en bas.

    Les positions sont ecrites pour l'etiquette 413 x 991. Sur une etiquette
    plus haute, on decale tout le bloc du milieu vers le bas de la MOITIE de la
    hauteur en plus : le contenu se retrouve centre entre l'en-tete et le pied,
    au lieu de s'entasser en haut avec un grand vide dessous."""
    dy = max(0, (H - 991) // 2)

    def centre(y, texte, taille):
        f = police(taille)
        w = d.textbbox((0, 0), texte, font=f)[2]
        d.text(((L - w) / 2, y), texte, font=f, fill=NOIR)

    d.rectangle([0, 0, L - 1, H - 1], outline=NOIR, width=3)
    centre(24, "MIRE DE TEST", 40)
    centre(72, f"{REFERENCE} - {DIMENSIONS}", 24)
    centre(104, f"{L} x {H} px - 300 ppp", 18)
    d.line([20, 140, L - 20, 140], fill=NOIR, width=2)

    # Reglette de 30 mm : a mesurer avec une vraie regle
    y = 175 + dy
    x0 = int((L - 30 * MM) / 2)
    d.text((x0, y), "REGLETTE 30 mm (mesurer)", font=police(18), fill=NOIR)
    y += 30
    reglette(d, x0, y, 30)

    # Damier 8 px : revele un decalage de points
    y = 290 + dy
    d.text((30, y), "DAMIER 8 px (nettete)", font=police(18), fill=NOIR)
    damier(d, int((L - 24 * 8) / 2), y + 28, 24, 12)

    # Traits fins : finesse de trait, 1 a 5 px
    y = 440 + dy
    d.text((30, y), "TRAITS FINS (1 a 5 px)", font=police(18), fill=NOIR)
    traits(d, 40, y + 30, 70, 70)

    # Aplats et pave de texte : densite d'impression
    y = 580 + dy
    d.text((30, y), "APLAT NOIR (densite)", font=police(18), fill=NOIR)
    d.rectangle([30, y + 28, L - 30, y + 108], fill=NOIR)
    d.text((60, y + 52), "TEXTE INVERSE", font=police(28), fill=BLANC)

    y = 720 + dy
    d.text((30, y), "LISIBILITE", font=police(18), fill=NOIR)
    lisibilite(d, 30, y + 28, (26, 22, 18, 14, 11))

    reperes(d, L, H)

    # Orientation : confirme le sens d'impression
    d.line([20, H - 96, L - 20, H - 96], fill=NOIR, width=2)
    centre(H - 84, "BAS DE L'ETIQUETTE", 30)
    fleche_bas(d, L / 2, H - 46)


def dessiner_paysage(img, d, L, H):
    """La mire paysage : memes controles, ranges en colonnes.

    Elle sert a verifier COMMENT brother_ql pivote une image paysage : les
    reperes de bord (« BAS » et « DROITE ») disent, sur l'etiquette sortie,
    ou chaque cote de l'image a atterri."""

    def centre(y, texte, taille):
        f = police(taille)
        w = d.textbbox((0, 0), texte, font=f)[2]
        d.text(((L - w) / 2, y), texte, font=f, fill=NOIR)

    dy = max(0, (H - 413) // 2)            # meme centrage que le portrait
    d.rectangle([0, 0, L - 1, H - 1], outline=NOIR, width=3)
    centre(18, "MIRE DE TEST - PAYSAGE", 34)
    centre(60, f"{REFERENCE} - {DIMENSIONS}  ·  {L} x {H} px - 300 ppp", 18)
    d.line([20, 88, L - 20, 88], fill=NOIR, width=2)

    # ── Colonne de gauche : reglette + traits fins ──
    x = 40
    d.text((x, 110 + dy), "REGLETTE 30 mm (mesurer)", font=police(17), fill=NOIR)
    reglette(d, x, 140 + dy, 30)
    d.text((x, 215 + dy), "TRAITS FINS (1 a 5 px)", font=police(17), fill=NOIR)
    traits(d, x + 10, 245 + dy, 60, 60)

    # ── Colonne du milieu : damier ──
    # 420 et non 400 : la reglette mesure 354 px et son chiffre « 30 » deborde
    # un peu a droite. Le damier commence apres, sans le chevaucher.
    x = 420
    d.text((x, 110 + dy), "DAMIER 8 px", font=police(17), fill=NOIR)
    damier(d, x, 140 + dy, 18, 10)

    # ── Colonne de droite : aplat + lisibilite ──
    # Elle s'arrete a 70 px du bord : la bande verticale « DROITE DE L'IMAGE »
    # occupe cet espace.
    x = 600
    droite = L - 70
    d.text((x, 110 + dy), "APLAT NOIR (densite)", font=police(17), fill=NOIR)
    d.rectangle([x, 138 + dy, droite, 196 + dy], fill=NOIR)
    d.text((x + 20, 152 + dy), "TEXTE INVERSE", font=police(26), fill=BLANC)
    d.text((x, 215 + dy), "LISIBILITE", font=police(17), fill=NOIR)
    lisibilite(d, x, 243 + dy, (20, 16, 13, 11))

    reperes(d, L, H)

    # ── Reperes de bord : c'est eux qu'on lira sur l'etiquette imprimee ──
    d.line([20, H - 70, L - 20, H - 70], fill=NOIR, width=2)
    centre(H - 58, "BAS DE L'IMAGE", 26)
    fleche_bas(d, L / 2, H - 30)
    # Le bord droit, ecrit verticalement : on le dessine a plat sur une petite
    # image, on la pivote d'un quart de tour, puis on la colle. PIL ne sait pas
    # ecrire du texte en biais directement.
    bandeau = Image.new("1", (260, 32), BLANC)
    ImageDraw.Draw(bandeau).text((0, 0), "DROITE DE L'IMAGE",
                                 font=police(24), fill=NOIR)
    img.paste(bandeau.rotate(90, expand=True), (L - 44, 120 + dy))


# ── Briques communes aux deux orientations ──────────────────────────────────

def reglette(d, x0, y, millimetres):
    """Une regle graduee, a verifier avec une vraie regle."""
    d.line([x0, y, x0 + millimetres * MM, y], fill=NOIR, width=3)
    for i in range(millimetres + 1):
        x = x0 + i * MM
        h = 26 if i % 10 == 0 else (16 if i % 5 == 0 else 9)
        d.line([x, y, x, y + h], fill=NOIR, width=2 if i % 5 == 0 else 1)
    for i in range(0, millimetres + 1, 10):
        d.text((x0 + i * MM - 8, y + 30), str(i), font=police(16), fill=NOIR)


def damier(d, x, y, colonnes, lignes, cote=8):
    """Un damier de carres de 8 px : revele un decalage de points."""
    for li in range(lignes):
        for co in range(colonnes):
            if (li + co) % 2 == 0:
                d.rectangle([x + co * cote, y + li * cote,
                             x + (co + 1) * cote - 1, y + (li + 1) * cote - 1],
                            fill=NOIR)
    d.rectangle([x - 2, y - 2, x + colonnes * cote + 1, y + lignes * cote + 1],
                outline=NOIR, width=1)


def traits(d, x, y, hauteur, ecart):
    """Cinq traits verticaux, de 1 a 5 px : la finesse imprimable."""
    for ep in range(1, 6):
        d.line([x, y, x, y + hauteur], fill=NOIR, width=ep)
        d.text((x - 5, y + hauteur + 6), str(ep), font=police(16), fill=NOIR)
        x += ecart


def lisibilite(d, x, y, tailles):
    """Une echelle de tailles de texte : jusqu'ou reste-t-on lisible ?"""
    for i, t in enumerate(tailles):
        d.text((x, y + i * (t + 10)), "Abc 0123456789 - " + str(t) + " px",
               font=police(t), fill=NOIR)


def reperes(d, L, H):
    """Quatre equerres d'angle : revelent un rognage ou un decalage."""
    for cx, cy, sx, sy in ((14, 14, 1, 1), (L - 15, 14, -1, 1),
                           (14, H - 15, 1, -1), (L - 15, H - 15, -1, -1)):
        d.line([cx, cy, cx + sx * 40, cy], fill=NOIR, width=4)
        d.line([cx, cy, cx, cy + sy * 40], fill=NOIR, width=4)


def fleche_bas(d, x, y):
    """Une fleche vers le bas : le sens de lecture."""
    d.line([x, y, x, y + 22], fill=NOIR, width=4)
    d.polygon([(x - 12, y + 18), (x + 12, y + 18), (x, y + 34)], fill=NOIR)


# ── Fabrication ─────────────────────────────────────────────────────────────

if orientation == "paysage":
    L, H = H, L                      # 991 x 413 : la transposee du portrait

img = Image.new("1", (L, H), BLANC)
d = ImageDraw.Draw(img)

if orientation == "paysage":
    dessiner_paysage(img, d, L, H)
else:
    dessiner_portrait(d, L, H)

# Nom de fichier conseille : reference + dimensions en pixels + orientation.
# La fenetre « Parcourir... » de Tk n'affiche QUE le nom du fichier — ni colonne
# de description, ni infobulle, et on ne peut pas lui en ajouter. Tout ce que la
# personne doit savoir pour choisir doit donc tenir dans ce nom.
img.save(sortie, dpi=(PPP, PPP))
print("Mire ecrite :", sortie, img.size, img.mode, "-", orientation)
