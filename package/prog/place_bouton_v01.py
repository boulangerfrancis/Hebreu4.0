# place_bouton_v01.py — Version 1.0
# v1.0 : creation
#   Ajoute un bouton YouTube cliquable sur la premiere page d'un PDF.
#   Le lien est ajoute via pypdf.annotations.Link (merge_page ne preserve pas linkURL).
#
# USAGE :
#   python place_bouton.py dossier_src fichier_src dossier_dst fichier_dst
#                          youtube_url
#                          [transparence] [pos_x] [pos_y]
#                          [rotation] [orientation_texte]
#                          [largeur] [hauteur]
#
# VALEURS PAR DEFAUT :
#   transparence     = 100  (opaque)
#   pos_x            = 0    (bord gauche)
#   pos_y            = 0    (bord bas)
#   rotation         = E    (vers la droite)
#   orientation_texte= 2    (horizontal + rotation E)
#   largeur          = 160  pts
#   hauteur          = 35   pts
#
# ROTATION (direction vers laquelle pointe le bouton) :
#   N ou 1 = haut      E ou 2 = droite    S ou 3 = bas    O ou 4 = gauche
#
# ORIENTATION TEXTE :
#   Texte horizontal (lettres normales) puis rotation :
#     1=N  2=E  3=S  4=O
#   Texte vertical (lettres empilees haut->bas) puis rotation :
#     5=N  6=E  7=S  8=O
#
# EXEMPLES :
#   python place_bouton.py . source.pdf . cible.pdf https://youtube.com/watch?v=XXX
#   python place_bouton.py . source.pdf . cible.pdf https://youtube.com/watch?v=XXX 100 0 807 E 2

import sys
import os
import math
from pathlib import Path
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from pypdf import PdfWriter, PdfReader
from pypdf.annotations import Link

version = ("place_bouton.py", "1.0")
print(f"[Import] {version[0]} - Version {version[1]} charge")

# ─────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────
COULEUR_BOUTON   = "#CC0000"
LABEL            = "YouTube"
DEF_TRANSPARENCE = 100
DEF_POS_X        = 0.0
DEF_POS_Y        = 0.0
DEF_ROTATION     = "E"
DEF_ORIENT       = "2"
DEF_LARGEUR      = 160
DEF_HAUTEUR      = 35

ROTATION_MAP = {
    "N": 90, "1": 90,
    "E":  0, "2":  0,
    "S":270, "3":270,
    "O":180, "4":180,
}


# ─────────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────────
def parse_rotation(val):
    """Convertit N/E/S/O ou 1/2/3/4 en angle degrees."""
    v = str(val).strip().upper()
    if v not in ROTATION_MAP:
        raise ValueError("rotation invalide %r : utiliser N E S O ou 1 2 3 4" % val)
    return ROTATION_MAP[v]


def parse_orient(val):
    """
    Retourne (vertical: bool, angle: int).
    1-4 : texte horizontal + rotation N/E/S/O
    5-8 : texte vertical   + rotation N/E/S/O
    """
    v = int(val)
    if not 1 <= v <= 8:
        raise ValueError("orientation_texte invalide %r : utiliser 1-8" % val)
    vertical = (v >= 5)
    idx      = (v - 1) % 4
    angle    = [90, 0, 270, 180][idx]
    return vertical, angle


# ─────────────────────────────────────────────────────────────────────
# DESSIN BOUTON
# ─────────────────────────────────────────────────────────────────────
def dessiner_bouton(c, x, y, L, H, angle_rot, texte_vertical, alpha_pct):
    """
    Dessine le bouton sur le canvas c.
    (x, y)         : point fixe = coin bas-gauche avant rotation
    L, H           : largeur, hauteur en pts
    angle_rot      : 0=droite 90=haut 180=gauche 270=bas
    texte_vertical : False=horizontal  True=lettres empilees haut->bas
    alpha_pct      : 0=invisible 100=opaque

    Retourne le rectangle englobant (x_min, y_min, x_max, y_max)
    en coordonnees page, pour l'annotation Link.
    """
    alpha  = alpha_pct / 100.0
    icon_w = H
    text_w = L - icon_w
    rayon  = H * 0.28
    fs_h   = int(H * 0.38)
    fs_v   = int(H * 0.32)

    c.saveState()
    c.translate(x, y)
    c.rotate(angle_rot)

    # Fond arrondi
    c.setFillColor(HexColor(COULEUR_BOUTON)); c.setFillAlpha(alpha)
    c.setStrokeAlpha(0.0)
    c.roundRect(0, 0, L, H, rayon, fill=1, stroke=0)

    # Cercle icone play
    r     = H * 0.30
    cx_ic = icon_w / 2
    cy_ic = H / 2
    c.setFillColor(white); c.setFillAlpha(alpha)
    c.circle(cx_ic, cy_ic, r, fill=1, stroke=0)

    # Triangle play
    t = r * 0.55
    c.setFillColor(HexColor(COULEUR_BOUTON)); c.setFillAlpha(alpha)
    p = c.beginPath()
    p.moveTo(cx_ic - t*0.6, cy_ic - t)
    p.lineTo(cx_ic - t*0.6, cy_ic + t)
    p.lineTo(cx_ic + t,     cy_ic)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Texte
    c.setFillColor(white); c.setFillAlpha(alpha)
    if not texte_vertical:
        c.setFont("Helvetica-Bold", fs_h)
        tw = c.stringWidth(LABEL, "Helvetica-Bold", fs_h)
        c.drawString(icon_w + (text_w - tw) / 2, (H - fs_h) / 2 + 1, LABEL)
    else:
        nb         = len(LABEL)
        interligne = fs_v * 1.05
        total_h    = nb * interligne
        tx         = icon_w + (text_w - fs_v) / 2
        ty_start   = H - (H - total_h) / 2 - fs_v
        c.setFont("Helvetica-Bold", fs_v)
        for i, lettre in enumerate(LABEL):
            c.drawString(tx, ty_start - i * interligne, lettre)

    c.restoreState()

    # Calcul rectangle englobant (coordonnees page)
    rad   = math.radians(angle_rot)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    coins = [
        (x,                     y),
        (x + L*cos_a,           y + L*sin_a),
        (x + L*cos_a - H*sin_a, y + L*sin_a + H*cos_a),
        (x           - H*sin_a, y            + H*cos_a),
    ]
    return (min(p[0] for p in coins), min(p[1] for p in coins),
            max(p[0] for p in coins), max(p[1] for p in coins))


# ─────────────────────────────────────────────────────────────────────
# PLACEMENT SUR LE PDF
# ─────────────────────────────────────────────────────────────────────
def placer_bouton(fichier_src, fichier_dst,
                  youtube_url,
                  transparence=DEF_TRANSPARENCE,
                  pos_x=DEF_POS_X, pos_y=DEF_POS_Y,
                  angle_rot=0, texte_vertical=False,
                  largeur=DEF_LARGEUR, hauteur=DEF_HAUTEUR):
    """
    Lit fichier_src, ajoute le bouton YouTube, ecrit fichier_dst.
    Le lien est ajoute via pypdf.annotations.Link car merge_page
    ne preserve pas les annotations reportlab (linkURL).
    """
    reader = PdfReader(str(fichier_src))
    page   = reader.pages[0]
    pw     = float(page.mediabox.width)
    ph     = float(page.mediabox.height)

    print("  Page         : %.0f x %.0f pts" % (pw, ph))
    print("  Position     : x=%.1f  y=%.1f" % (pos_x, pos_y))
    print("  Rotation     : %d deg" % angle_rot)
    print("  Texte        : %s" % ("vertical" if texte_vertical else "horizontal"))
    print("  Bouton       : %d x %d pts" % (largeur, hauteur))
    print("  Transparence : %d%%" % transparence)

    # Overlay graphique
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(pw, ph))
    rect_lien = dessiner_bouton(c, pos_x, pos_y, largeur, hauteur,
                                angle_rot, texte_vertical, transparence)
    c.save()
    packet.seek(0)

    # Fusion graphique + pages suivantes
    overlay = PdfReader(packet).pages[0]
    page.merge_page(overlay)

    writer = PdfWriter()
    writer.add_page(page)
    for i in range(1, len(reader.pages)):
        writer.add_page(reader.pages[i])

    # Annotation lien (separee du dessin car merge_page ne preserve pas linkURL)
    annotation = Link(rect=rect_lien, url=youtube_url)
    writer.add_annotation(page_number=0, annotation=annotation)

    print("  Lien         : (%.0f, %.0f, %.0f, %.0f)" % rect_lien)

    os.makedirs(Path(fichier_dst).parent, exist_ok=True)
    with open(str(fichier_dst), "wb") as f:
        writer.write(f)
    print("  => %s" % fichier_dst)


# ─────────────────────────────────────────────────────────────────────
# POINT D'ENTREE LIGNE DE COMMANDE
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    args = sys.argv[1:]
    if len(args) < 5:
        print(__doc__)
        sys.exit(1)

    def arg(i, defaut):
        return args[i] if i < len(args) else defaut

    def _int(v, d):
        try:    return int(v)
        except: return d

    def _float(v, d):
        try:    return float(v)
        except: return d

    dossier_src  = arg(0, ".")
    fichier_src  = arg(1, None)
    dossier_dst  = arg(2, ".")
    fichier_dst  = arg(3, None)
    youtube_url  = arg(4, None)
    transparence = _int(  arg(5, DEF_TRANSPARENCE), DEF_TRANSPARENCE)
    pos_x        = _float(arg(6, DEF_POS_X),        DEF_POS_X)
    pos_y        = _float(arg(7, DEF_POS_Y),        DEF_POS_Y)
    rotation     = arg(8, DEF_ROTATION)
    orient       = arg(9, DEF_ORIENT)
    largeur      = _int(  arg(10, DEF_LARGEUR),     DEF_LARGEUR)
    hauteur      = _int(  arg(11, DEF_HAUTEUR),     DEF_HAUTEUR)

    if None in (fichier_src, fichier_dst, youtube_url):
        print("ERREUR : arguments manquants")
        sys.exit(1)

    src = Path(dossier_src) / fichier_src
    dst = Path(dossier_dst) / fichier_dst

    if not src.exists():
        print("ERREUR : fichier source introuvable : %s" % src)
        sys.exit(1)

    try:
        angle_rot      = parse_rotation(rotation)
        vertical, _    = parse_orient(orient)
    except ValueError as e:
        print("ERREUR : %s" % e)
        sys.exit(1)

    print("place_bouton.py")
    print("  Source       : %s" % src)
    print("  Cible        : %s" % dst)
    print("  URL          : %s" % youtube_url)

    placer_bouton(src, dst, youtube_url,
                  transparence, pos_x, pos_y,
                  angle_rot, vertical,
                  largeur, hauteur)
    print("OK")
