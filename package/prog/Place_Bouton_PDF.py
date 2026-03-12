"""
Place_Bouton_PDF.py
Ajoute un bouton YouTube cliquable sur la premiere page d'un PDF.

USAGE :
  python Place_Bouton_PDF.py dossier_src fichier_src dossier_dst fichier_dst
                             youtube_url
                             [transparence] [pos_x] [pos_y]
                             [rotation] [orientation_texte]
                             [largeur] [hauteur]

VALEURS PAR DEFAUT :
  transparence     = 100  (opaque)
  pos_x            = 0    (bord gauche)
  pos_y            = 0    (bord bas)
  rotation         = E    (vers la droite)
  orientation_texte= 2    (horizontal + rotation E)
  largeur          = 160  pts
  hauteur          = 35   pts

ROTATION (direction vers laquelle pointe le bouton) :
  N ou 1 = haut      E ou 2 = droite    S ou 3 = bas    O ou 4 = gauche

ORIENTATION TEXTE :
  Texte horizontal (lettres normales) puis rotation :
    1=N  2=E  3=S  4=O
  Texte vertical (lettres empilees haut->bas) puis rotation :
    5=N  6=E  7=S  8=O

EXEMPLES :
  python Place_Bouton_PDF.py . source.pdf . cible.pdf https://youtube.com/watch?v=XXX
  python Place_Bouton_PDF.py . source.pdf . cible.pdf https://youtube.com/watch?v=XXX 100 400 20 O 4
  python Place_Bouton_PDF.py . source.pdf . cible.pdf https://youtube.com/watch?v=XXX 80 400 20 O 4 180 40
"""

import sys, os, math
from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from pypdf import PdfWriter, PdfReader

# ─────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────
COULEUR_BOUTON = "#CC0000"
DEF_TRANSPARENCE = 100
DEF_POS_X        = 0
DEF_POS_Y        = 0
DEF_ROTATION     = "E"
DEF_ORIENT       = "2"
DEF_LARGEUR      = 160
DEF_HAUTEUR      = 35
LABEL            = "YouTube"

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
    idx      = (v - 1) % 4          # 0=N 1=E 2=S 3=O
    angle    = [90, 0, 270, 180][idx]
    return vertical, angle


# ─────────────────────────────────────────────────────────────────────
# DESSIN BOUTON
# ─────────────────────────────────────────────────────────────────────
def dessiner_bouton(c, x, y, L, H, youtube_url, alpha_pct,
                    angle_rot, texte_vertical):
    """
    Dessine le bouton sur le canvas c en (x, y) point fixe.
    L, H         : largeur, hauteur en pts
    alpha_pct    : 0=invisible 100=opaque
    angle_rot    : 0=droite 90=haut 180=gauche 270=bas
    texte_vertical : False=horizontal  True=lettres empilees
    """
    alpha   = alpha_pct / 100.0
    icon_w  = H                      # carre icone = cote H
    text_w  = L - icon_w
    rayon   = H * 0.28
    fs_h    = int(H * 0.38)          # taille police texte horizontal
    fs_v    = int(H * 0.32)          # taille police texte vertical

    c.saveState()
    c.translate(x, y)
    c.rotate(angle_rot)

    # ── Fond arrondi ─────────────────────────────────────
    c.setFillColor(HexColor(COULEUR_BOUTON))
    c.setFillAlpha(alpha)
    c.setStrokeAlpha(0.0)
    c.roundRect(0, 0, L, H, rayon, fill=1, stroke=0)

    # ── Cercle icone play ─────────────────────────────────
    r      = H * 0.30
    cx_ic  = icon_w / 2
    cy_ic  = H / 2
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

    # ── Texte ─────────────────────────────────────────────
    c.setFillColor(white); c.setFillAlpha(alpha)

    if not texte_vertical:
        # Texte horizontal : une seule ligne centree dans text_w
        c.setFont("Helvetica-Bold", fs_h)
        tw = c.stringWidth(LABEL, "Helvetica-Bold", fs_h)
        tx = icon_w + (text_w - tw) / 2
        ty = (H - fs_h) / 2 + 1
        c.drawString(tx, ty, LABEL)

    else:
        # Texte vertical : lettres empilees haut -> bas
        # On calcule la hauteur totale occupee par les lettres
        # pour centrer verticalement dans le bouton
        nb      = len(LABEL)
        interligne = fs_v * 1.05
        total_h    = nb * interligne
        # x centre dans la zone texte
        tx = icon_w + (text_w - fs_v) / 2
        # y de depart : on part du haut
        ty_start = H - (H - total_h) / 2 - fs_v

        c.setFont("Helvetica-Bold", fs_v)
        for i, lettre in enumerate(LABEL):
            ty = ty_start - i * interligne
            c.drawString(tx, ty, lettre)

    c.restoreState()

    # ── Zone cliquable ────────────────────────────────────
    # linkURL utilise les coordonnees de la MEDIABOX (pas le CTM courant)
    # On calcule le rectangle englobant du bouton transforme
    rad   = math.radians(angle_rot)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    # 4 coins du bouton dans le repere page
    coins = [
        (x,                           y),
        (x + L*cos_a,                 y + L*sin_a),
        (x + L*cos_a - H*sin_a,       y + L*sin_a + H*cos_a),
        (x           - H*sin_a,       y            + H*cos_a),
    ]
    x_min = min(p[0] for p in coins)
    y_min = min(p[1] for p in coins)
    x_max = max(p[0] for p in coins)
    y_max = max(p[1] for p in coins)
    c.linkURL(youtube_url, (x_min, y_min, x_max, y_max), relative=0)


# ─────────────────────────────────────────────────────────────────────
# PLACEMENT SUR LE PDF
# ─────────────────────────────────────────────────────────────────────
def placer_bouton(fichier_src, fichier_dst,
                  youtube_url,
                  transparence=DEF_TRANSPARENCE,
                  pos_x=DEF_POS_X, pos_y=DEF_POS_Y,
                  angle_rot=0, texte_vertical=False,
                  largeur=DEF_LARGEUR, hauteur=DEF_HAUTEUR):

    reader = PdfReader(str(fichier_src))
    page   = reader.pages[0]
    pw     = float(page.mediabox.width)
    ph     = float(page.mediabox.height)

    print("  Page source  : %.0f x %.0f pts" % (pw, ph))
    print("  Position     : x=%.1f  y=%.1f" % (pos_x, pos_y))
    print("  Rotation     : %d deg" % angle_rot)
    print("  Texte        : %s" % ("vertical" if texte_vertical else "horizontal"))
    print("  Bouton       : %d x %d pts" % (largeur, hauteur))
    print("  Transparence : %d%%" % transparence)

    # Overlay
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(pw, ph))
    dessiner_bouton(c, pos_x, pos_y, largeur, hauteur,
                    youtube_url, transparence,
                    angle_rot, texte_vertical)
    c.save()
    packet.seek(0)

    # Fusion
    overlay = PdfReader(packet).pages[0]
    page.merge_page(overlay)

    writer = PdfWriter()
    writer.add_page(page)
    for i in range(1, len(reader.pages)):
        writer.add_page(reader.pages[i])

    os.makedirs(fichier_dst.parent, exist_ok=True)
    with open(str(fichier_dst), "wb") as f:
        writer.write(f)
    print("  => %s" % fichier_dst)


# ─────────────────────────────────────────────────────────────────────
# POINT D'ENTREE
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    args = sys.argv[1:]

    if len(args) < 5:
        print(__doc__)
        sys.exit(1)

    def arg(i, defaut):
        return args[i] if i < len(args) else defaut

    dossier_src  = arg(0, ".")
    fichier_src  = arg(1, None)
    dossier_dst  = arg(2, ".")
    fichier_dst  = arg(3, None)
    youtube_url  = arg(4, None)
    transparence = int(arg(5, DEF_TRANSPARENCE))
    pos_x        = float(arg(6, DEF_POS_X))
    pos_y        = float(arg(7, DEF_POS_Y))
    rotation     = arg(8, DEF_ROTATION)
    orient       = arg(9, DEF_ORIENT)
    largeur      = int(arg(10, DEF_LARGEUR))
    hauteur      = int(arg(11, DEF_HAUTEUR))

    if None in (fichier_src, fichier_dst, youtube_url):
        print("ERREUR : manque dossier_src fichier_src dossier_dst fichier_dst youtube_url")
        sys.exit(1)

    src = Path(dossier_src) / fichier_src
    dst = Path(dossier_dst) / fichier_dst

    if not src.exists():
        print("ERREUR : fichier source introuvable : %s" % src)
        sys.exit(1)

    try:
        angle_rot      = parse_rotation(rotation)
        vertical, _    = parse_orient(orient)
        # l'angle de rotation du texte est le meme que celui du bouton
        # l'orientation texte (1-8) determine juste vertical ou non
    except ValueError as e:
        print("ERREUR : %s" % e)
        sys.exit(1)

    print("Place_Bouton_PDF.py")
    print("  Source  : %s" % src)
    print("  Cible   : %s" % dst)
    print("  URL     : %s" % youtube_url)

    placer_bouton(src, dst, youtube_url,
                  transparence, pos_x, pos_y,
                  angle_rot, vertical,
                  largeur, hauteur)

    print("OK")
