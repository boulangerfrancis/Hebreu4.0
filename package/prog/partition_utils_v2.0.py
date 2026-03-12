# partition_utils.py — Version 2.0
# Traitement partitions musicales avec boutons YouTube
"""
v2.0 :
  - Correction rotation PDF : si page.rotation in (90,270), swap width/height
    pour positionner correctement les boutons sur pages paysage Word
  - create_overlay utilise les dimensions reelles apres rotation

v1.9 : signature dans STRUCTURE.py, plus de fichiers .params
v1.8 : _get_col() — lecture CSV insensible aux noms de colonnes
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

version = ("partition_utils.py", "2.0")
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

def draw_button(c, x, y, width, height, color, text):
    """Dessine un bouton arrondi avec icone play."""
    radius = height * 0.4
    c.setFillColor(color)
    c.roundRect(x, y, width, height, radius / 2, fill=1)
    circle_x = x + radius + 5
    circle_y = y + height / 2
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
    text_x = x + 2 * radius + 10
    text_y = y + (height - int(height / 3)) / 2 - 1
    c.drawString(text_x, text_y, text)


def create_overlay(page_width, page_height, player_url, video_id,
                   x_pct=None, y_pct=None, fond_opacite_pct=0.0,
                   rotation=0):
    """Cree overlay PDF avec 2 boutons.

    page_width/page_height : dimensions du mediabox (non rote).
    rotation : angle de rotation de la page (0, 90, 180, 270).
    x_pct / y_pct : % de la page telle qu'affichee (apres rotation).
    fond_opacite_pct : 0=fond blanc opaque, 100=invisible.

    Pour une page avec rotation=90 (Word paysage) :
    - x% est calcule sur la largeur effective (= height_raw)
    - y% est calcule sur la hauteur effective (= width_raw)
    - l'overlay est dessine dans le repere non-rote avec transformation CTM
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    total_width = BUTTON_WIDTH * 2 + BUTTON_SPACING

    # Dimensions effectives (apres rotation)
    if rotation in (90, 270):
        eff_w, eff_h = page_height, page_width
    else:
        eff_w, eff_h = page_width, page_height

    y_pct_val = y_pct if y_pct is not None else DEFAULT_Y_PCT
    x_pct_val = x_pct  # None = centre

    # Position dans l'espace effectif
    eff_y = (y_pct_val / 100.0) * eff_h
    eff_x = ((x_pct_val / 100.0) * eff_w) if x_pct_val is not None \
            else (eff_w - total_width) / 2

    # Transformer les coordonnees effectives en coordonnees mediabox (non-rote)
    if rotation == 90:
        # Rotation 90 CW : (ex, ey) -> (ey, W - ex) dans mediabox
        draw_x = eff_y
        draw_y = page_width - eff_x - BUTTON_HEIGHT
        # Pour rotation 90, les boutons sont dessines "couchés"
        # Il faut appliquer une rotation CTM sur le canvas
        c.saveState()
        c.translate(0, page_width)
        c.rotate(-90)
        # Maintenant on est dans l'espace effectif (eff_w x eff_h)
        start_x = eff_x
        start_y = eff_y
    elif rotation == 270:
        c.saveState()
        c.translate(page_height, 0)
        c.rotate(90)
        start_x = eff_x
        start_y = eff_y
    elif rotation == 180:
        c.saveState()
        c.translate(page_width, page_height)
        c.rotate(180)
        start_x = eff_x
        start_y = eff_y
    else:
        start_x = eff_x
        start_y = eff_y

    # Fond blanc avec opacite
    alpha = max(0.0, min(1.0, 1.0 - fond_opacite_pct / 100.0))
    if alpha > 0.01:
        pad = FOND_PADDING
        c.setFillColor(Color(1, 1, 1, alpha=alpha))
        c.setStrokeColor(Color(1, 1, 1, alpha=alpha))
        c.rect(start_x - pad, start_y - pad,
               total_width + 2 * pad, BUTTON_HEIGHT + 2 * pad,
               fill=1, stroke=0)

    # Bouton rouge YouTube
    draw_button(c, start_x, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#FF0000"), "YouTube")
    c.linkURL(f"https://youtube.com/watch?v={quote(video_id)}",
              (start_x, start_y, start_x + BUTTON_WIDTH, start_y + BUTTON_HEIGHT),
              relative=0)

    # Bouton vert Jouer ici
    x2 = start_x + BUTTON_WIDTH + BUTTON_SPACING
    draw_button(c, x2, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#28a745"), "Jouer ici")
    c.linkURL(f"{player_url}?v={quote(video_id)}",
              (x2, start_y, x2 + BUTTON_WIDTH, start_y + BUTTON_HEIGHT),
              relative=0)

    if rotation != 0:
        c.restoreState()

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
                               pos_y: float = None) -> bool:
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
            rotation=rotation
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

                params = {
                    "video_id"        : video_id,
                    "orientation"     : orientation,
                    "fond_opacite_pct": fond_opacite_pct,
                    "x"               : pos_x,
                    "y"               : pos_y,
                }

                x_str = f"{pos_x}%" if pos_x is not None else "centre"
                y_str = f"{pos_y}%" if pos_y is not None else f"{DEFAULT_Y_PCT}% (defaut)"
                print(f"  [CSV] {pdf_name_brut!r}")
                print(f"        -> cle    : {pdf_name!r}")
                print(f"        -> video  : {video_id!r}")
                print(f"        -> orient : {'H (Paysage)' if orientation=='H' else 'V (Portrait)'}")
                print(f"        -> fond   : {fond_opacite_pct}% transparent")
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
                     pos_x, pos_y) -> str:
    """Chaine compacte representant les parametres d'une partition.
    Stockee dans STRUCTURE.py -> cle 'params_signature' de chaque partition.
    """
    return f"{video_id}|{orientation}|{fond_opacite_pct}|{pos_x}|{pos_y}"


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

# Fin partition_utils.py v2.0
