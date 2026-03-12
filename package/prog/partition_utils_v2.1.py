# partition_utils.py — Version 2.1
# Traitement partitions musicales avec boutons YouTube
"""
v2.1 :
  - Nouvelles colonnes CSV : bord (0=bas affiche, 1=haut), sens_texte (0=normal, 1=retourne)
  - Correction y pour rotate=90 : bord=0 -> y_eff grand (bas CTM = bas page affichee)
  - Zones de clic (linkURL) transformees de CTM vers mediabox pour tous les angles
  - draw_button supporte sens_texte=1 (rotate 180 autour du centre)

v2.0 : correction rotation CTM, lecture /Rotate PDF
v1.9 : signature dans STRUCTURE.py
v1.8 : _get_col() noms colonnes CSV flexibles
"""

import csv
import re
import unicodedata
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
from typing import Dict, Optional

try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, white, Color
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False
    print("AVERTISSEMENT : pypdf ou reportlab manquant — pip install pypdf reportlab")

version = ("partition_utils.py", "2.1")
print(f"[Import] {version[0]} - Version {version[1]} charge")

# Constantes boutons
BUTTON_WIDTH   = 140
BUTTON_HEIGHT  = 50
BUTTON_SPACING = 20
FOND_PADDING   = 8

# Defauts CSV
DEFAULT_Y_PCT            = 2.0   # % hauteur depuis le bas (marge basse)
DEFAULT_X_PCT            = None  # None = centre automatiquement
DEFAULT_FOND_OPACITE_PCT = 0.0   # 0 = fond blanc opaque


# ============================================================================
# DESSIN BOUTONS
# ============================================================================

def draw_button(c, x, y, width, height, color, text, sens_texte=0):
    """Dessine un bouton arrondi avec icone play.

    sens_texte=0 : texte normal
    sens_texte=1 : bouton retourne 180 degres (texte a l'envers)
    """
    radius = height * 0.4

    if sens_texte == 1:
        # Rotation 180 autour du centre du bouton
        cx, cy = x + width / 2, y + height / 2
        c.saveState()
        c.translate(cx, cy)
        c.rotate(180)
        c.translate(-width / 2, -height / 2)
        x_draw, y_draw = 0, 0
    else:
        x_draw, y_draw = x, y

    c.setFillColor(color)
    c.roundRect(x_draw, y_draw, width, height, radius / 2, fill=1)

    circle_x = x_draw + radius + 5
    circle_y = y_draw + height / 2
    c.setFillColor(white)
    c.circle(circle_x, circle_y, radius, fill=1)
    c.setFillColor(color)
    tri_half = radius * 0.6
    path = c.beginPath()
    path.moveTo(circle_x - tri_half * 0.6, circle_y - tri_half)
    path.lineTo(circle_x - tri_half * 0.6, circle_y + tri_half)
    path.lineTo(circle_x + tri_half, circle_y)
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", int(height / 3))
    text_x = x_draw + 2 * radius + 10
    text_y = y_draw + (height - int(height / 3)) / 2 - 1
    c.drawString(text_x, text_y, text)

    if sens_texte == 1:
        c.restoreState()


def _ctm_to_mediabox(x_ctm, y_ctm, rotation, w_mb, h_mb):
    """Transforme coordonnees CTM en coordonnees mediabox.

    CTM applique selon rotation :
      90  : translate(0, w_mb) rotate(-90)   -> (x,y) => (y, w_mb-x)
      270 : translate(h_mb, 0) rotate(90)    -> (x,y) => (h_mb-y, x)
      180 : translate(w_mb, h_mb) rotate(180)-> (x,y) => (w_mb-x, h_mb-y)
      0   : identite
    """
    if rotation == 90:
        return (y_ctm, w_mb - x_ctm)
    elif rotation == 270:
        return (h_mb - y_ctm, x_ctm)
    elif rotation == 180:
        return (w_mb - x_ctm, h_mb - y_ctm)
    else:
        return (x_ctm, y_ctm)


def _link_rect(x_ctm, y_ctm, w_btn, h_btn, rotation, w_mb, h_mb):
    """Rectangle linkURL en coords mediabox depuis coords CTM.

    Transforme les 4 coins et retourne le rectangle englobant.
    Indispensable car linkURL ignore le CTM courant de reportlab.
    """
    coins = [
        (x_ctm,         y_ctm),
        (x_ctm + w_btn, y_ctm),
        (x_ctm,         y_ctm + h_btn),
        (x_ctm + w_btn, y_ctm + h_btn),
    ]
    mb = [_ctm_to_mediabox(cx, cy, rotation, w_mb, h_mb) for cx, cy in coins]
    xs = [p[0] for p in mb]
    ys = [p[1] for p in mb]
    return (min(xs), min(ys), max(xs), max(ys))


def create_overlay(page_width, page_height, player_url, video_id,
                   x_pct=None, y_pct=None, fond_opacite_pct=0.0,
                   rotation=0, bord=0, sens_texte=0):
    """Cree overlay PDF avec 2 boutons positionnes correctement.

    Args:
        page_width, page_height : dimensions mediabox (/Rotate non pris en compte)
        rotation      : angle /Rotate du PDF (0, 90, 180, 270)
        bord          : 0=bas de la page affichee, 1=haut
        sens_texte    : 0=texte normal, 1=retourne 180 degres
        x_pct         : % largeur effective depuis gauche (None=centre)
        y_pct         : % depuis le bord choisi (None=DEFAULT_Y_PCT)
        fond_opacite_pct : 0=fond blanc opaque, 100=invisible
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    total_width = BUTTON_WIDTH * 2 + BUTTON_SPACING

    # Dimensions effectives (page vue a l ecran)
    if rotation in (90, 270):
        eff_w, eff_h = page_height, page_width
    else:
        eff_w, eff_h = page_width, page_height

    y_pct_val = y_pct if y_pct is not None else DEFAULT_Y_PCT

    # x : % de la largeur effective
    eff_x = ((x_pct / 100.0) * eff_w) if x_pct is not None             else (eff_w - total_width) / 2

    # y selon bord :
    #   bord=0 (bas affiche)  : depuis le bas  -> y_eff grand
    #   bord=1 (haut affiche) : depuis le haut -> y_eff petit
    if bord == 0:
        eff_y = eff_h * (1.0 - y_pct_val / 100.0) - BUTTON_HEIGHT
    else:
        eff_y = eff_h * (y_pct_val / 100.0)

    # Appliquer CTM selon rotation
    if rotation == 90:
        c.saveState()
        c.translate(0, page_width)
        c.rotate(-90)
    elif rotation == 270:
        c.saveState()
        c.translate(page_height, 0)
        c.rotate(90)
    elif rotation == 180:
        c.saveState()
        c.translate(page_width, page_height)
        c.rotate(180)

    start_x, start_y = eff_x, eff_y

    # Fond
    alpha = max(0.0, min(1.0, 1.0 - fond_opacite_pct / 100.0))
    if alpha > 0.01:
        pad = FOND_PADDING
        c.setFillColor(Color(1, 1, 1, alpha=alpha))
        c.setStrokeColor(Color(1, 1, 1, alpha=alpha))
        c.rect(start_x - pad, start_y - pad,
               total_width + 2 * pad, BUTTON_HEIGHT + 2 * pad,
               fill=1, stroke=0)

    # Boutons
    draw_button(c, start_x, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#FF0000"), "YouTube", sens_texte)
    x2 = start_x + BUTTON_WIDTH + BUTTON_SPACING
    draw_button(c, x2, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#28a745"), "Jouer ici", sens_texte)

    if rotation != 0:
        c.restoreState()

    # Zones de clic en coords MEDIABOX (linkURL ignore le CTM)
    rect1 = _link_rect(start_x, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                       rotation, page_width, page_height)
    rect2 = _link_rect(x2, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                       rotation, page_width, page_height)
    c.linkURL(f"https://youtube.com/watch?v={quote(video_id)}", rect1, relative=0)
    c.linkURL(f"{player_url}?v={quote(video_id)}", rect2, relative=0)

    c.save()
    packet.seek(0)
    return PdfReader(packet)


# ============================================================================
# AJOUT BOUTONS SUR PDF
# ============================================================================

def ajouter_boutons_partition(source_pdf: Path, target_pdf: Path,
                               player_url: str, video_id: str,
                               orientation: str = "V",
                               fond_opacite_pct: float = 0.0,
                               pos_x: float = None,
                               pos_y: float = None,
                               bord: int = 0,
                               sens_texte: int = 0) -> bool:
    """Ajoute boutons YouTube sur premiere page partition.

    Lit /Rotate du PDF : Word en paysage produit un PDF portrait + Rotate=90.
    create_overlay applique une transformation CTM pour que x%/y% soient
    corrects par rapport a la page telle qu'affichee.
    """
    if not HAS_PDF_LIBS:
        print("  ✗ pypdf/reportlab manquant")
        return False
    try:
        reader = PdfReader(source_pdf)
        writer = PdfWriter()
        first_page = reader.pages[0]

        width  = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)

        # Lire la rotation (Word paysage = portrait + Rotate:90)
        try:
            rotation = int(first_page.get("/Rotate", 0) or 0)
        except Exception:
            rotation = 0

        print(f"  [PDF] {source_pdf.name} : "
              f"{width:.0f}x{height:.0f}pts rotate={rotation}")

        overlay_pdf = create_overlay(
            width, height, player_url, video_id,
            x_pct=pos_x, y_pct=pos_y,
            fond_opacite_pct=fond_opacite_pct,
            rotation=rotation,
            bord=bord,
            sens_texte=sens_texte,
        )
        first_page.merge_page(overlay_pdf.pages[0])
        writer.add_page(first_page)
        for page in reader.pages[1:]:
            writer.add_page(page)
        target_pdf.parent.mkdir(parents=True, exist_ok=True)
        with open(target_pdf, "wb") as f:
            writer.write(f)
        return True
    except Exception as e:
        print(f"  ✗ Erreur ajout boutons : {e}")
        return False


# ============================================================================
# LECTURE __correspondance.csv
# ============================================================================

def _get_col(row: dict, *noms) -> str:
    """Lit la premiere colonne trouvee (insensible a la casse)."""
    row_lower = {k.lower().strip(): v for k, v in row.items() if k}
    for nom in noms:
        val = row_lower.get(nom.lower())
        if val is not None:
            return str(val).strip()
    return ""


def _normaliser_cle_csv(pdf_name: str) -> str:
    """Retire prefixe __partition_ et normalise : minusc., sans accents, espaces->_."""
    nom  = pdf_name.strip()
    nom  = re.sub(r'^__partition[\s_]+', '', nom, flags=re.IGNORECASE)
    stem = Path(nom).stem
    ext  = Path(nom).suffix
    stem = unicodedata.normalize('NFD', stem)
    stem = ''.join(c for c in stem if unicodedata.category(c) != 'Mn')
    stem = stem.replace("'", "_").replace("\u2019", "_").replace(" ", "_").lower()
    return stem + ext.lower()


def _parse_float(val, defaut=None) -> Optional[float]:
    v = val.strip() if val else ""
    if not v:
        return defaut
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return defaut


def _parse_int(val, defaut=0) -> int:
    """Parse un entier depuis une chaine CSV (0 si vide)."""
    v = val.strip() if val else ""
    if not v:
        return defaut
    try:
        return int(float(v))
    except ValueError:
        return defaut


def _parse_orientation(val: str) -> str:
    v = val.strip().upper()
    return "H" if v in ("H", "LANDSCAPE", "L", "PAYSAGE") else "V"


def _parse_fond(val: str) -> float:
    v = val.strip() if val else ""
    if not v:
        return DEFAULT_FOND_OPACITE_PCT
    try:
        return max(0.0, min(100.0, float(v.replace(",", "."))))
    except ValueError:
        return DEFAULT_FOND_OPACITE_PCT


def charger_correspondances(csv_path: Path) -> Dict[str, dict]:
    """Charge correspondances depuis CSV avec noms de colonnes flexibles.

    Noms de colonnes supportes (insensible a la casse) :
        nom_partition__pdf  | pdf_name      -> nom fichier
        youtube_url         | url           -> URL YouTube
        orientation                         -> V ou H
        transparence        | fond_transparent -> 0-100%
        position_Horizontale | x             -> % largeur
        position_verticale  | y             -> % hauteur depuis bas

    Returns:
        Dict {nom_normalise: {video_id, orientation, fond_opacite_pct, x, y}}
    """
    if not csv_path.exists():
        return {}

    correspondances = {}
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pdf_name_brut = _get_col(row,
                    "nom_partition__pdf", "pdf_name", "nom_partition_pdf", "nom_pdf")
                youtube_url = _get_col(row, "youtube_url", "url", "youtube")

                if not pdf_name_brut:
                    continue

                pdf_name         = _normaliser_cle_csv(pdf_name_brut)
                video_id         = youtube_url.split("v=")[-1].split("&")[0] \
                                   if "v=" in youtube_url else youtube_url
                orientation      = _parse_orientation(_get_col(row, "orientation"))
                fond_opacite_pct = _parse_fond(_get_col(row,
                    "transparence", "fond_transparent", "fond", "transparency"))
                pos_x = _parse_float(_get_col(row,
                    "position_horizontale", "position_Horizontale", "x", "pos_x"))
                pos_y = _parse_float(_get_col(row,
                    "position_verticale", "position_Verticale", "y", "pos_y"))

                bord       = _parse_int(_get_col(row,
                    "bord", "bord_bouton"), 0)
                sens_texte = _parse_int(_get_col(row,
                    "sens_texte", "sens"), 0)

                params = {
                    "video_id"        : video_id,
                    "orientation"     : orientation,
                    "fond_opacite_pct": fond_opacite_pct,
                    "x"               : pos_x,
                    "y"               : pos_y,
                    "bord"            : bord,
                    "sens_texte"      : sens_texte,
                }

                x_str = f"{pos_x}%" if pos_x is not None else "centre"
                y_str = f"{pos_y}%" if pos_y is not None else f"{DEFAULT_Y_PCT}% (defaut)"
                bord_str = "haut" if bord == 1 else "bas"
                print(f"  [CSV] {pdf_name_brut!r}")
                print(f"        -> cle    : {pdf_name!r}")
                print(f"        -> video  : {video_id!r}")
                print(f"        -> orient : {'H (Paysage)' if orientation=='H' else 'V (Portrait)'}")
                print(f"        -> fond   : {fond_opacite_pct}% transparent")
                print(f"        -> bord   : {bord_str} ({bord})")
                print(f"        -> sens   : {'retourne' if sens_texte else 'normal'} ({sens_texte})")
                print(f"        -> x      : {x_str}")
                print(f"        -> y      : {y_str}")

                correspondances[pdf_name] = params

        return correspondances
    except Exception as e:
        print(f"  ✗ Erreur lecture correspondances : {e}")
        return {}


# ============================================================================
# SIGNATURE PARAMETRES (pour detecter les changements)
# ============================================================================

def params_signature(video_id: str, orientation: str, fond_opacite_pct: float,
                     pos_x, pos_y, bord: int = 0, sens_texte: int = 0) -> str:
    """Chaine compacte representant les parametres d'une partition.
    Stockee dans STRUCTURE.py -> cle 'params_signature' de chaque partition.
    Inclut bord et sens_texte depuis v2.1.
    """
    return f"{video_id}|{orientation}|{fond_opacite_pct}|{pos_x}|{pos_y}|{bord}|{sens_texte}"


def doit_regenerer_partition(source_pdf: Path, target_pdf: Path,
                              sig_actuelle: str = "") -> bool:
    """Verifie si partition doit etre regeneree.

    Regenere si :
    - target absent
    - source plus recent que target
    - sig_actuelle (params_signature) differente de celle stockee dans STRUCTURE.py

    La signature est passee directement (plus de fichier .params).
    La comparaison signature est faite par musique.py avant cet appel.

    Args:
        source_pdf    : PDF source (sans boutons)
        target_pdf    : PDF destination (avec boutons)
        sig_actuelle  : signature courante (depuis CSV / STRUCTURE)
    """
    if not target_pdf.exists():
        return True
    return source_pdf.stat().st_mtime > target_pdf.stat().st_mtime

# Fin partition_utils.py v2.1
