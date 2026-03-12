# partition_utils.py - Version 1.7
# Traitement partitions musicales avec boutons YouTube
"""
v1.7 :
  - Y defaut = 2% (marge basse standard)
  - Semantique fond corrigee : 0%=opaque, 100%=transparent
  - Regeneration si parametres CSV ont change (fichier .params adjacent au PDF)
  - Signature stockee apres chaque generation reussie

v1.6 : V/H, fond en %, x/y flottants, debug CSV
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
    print("AVERTISSEMENT : pypdf ou reportlab manquant")
    print("  pip install pypdf reportlab")

version = ("partition_utils.py", "1.8")
print(f"[Import] {version[0]} - Version {version[1]} charge")

# Constantes boutons
BUTTON_WIDTH   = 140
BUTTON_HEIGHT  = 50
BUTTON_SPACING = 20
FOND_PADDING   = 8

# Defauts CSV
DEFAULT_Y_PCT            = 2.0    # % hauteur depuis le bas (marge basse standard)
DEFAULT_X_PCT            = None   # None = centre automatiquement
DEFAULT_FOND_OPACITE_PCT = 0.0    # 0% = fond blanc opaque (defaut)


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
                   x_pct=None, y_pct=None, fond_opacite_pct=0.0):
    """Cree overlay PDF avec 2 boutons.

    Args:
        page_width, page_height : dimensions page en points PDF
        player_url, video_id    : liens YouTube
        x_pct       : % largeur depuis gauche (None = centre)
        y_pct       : % hauteur depuis le bas (negatif = marge sous la page)
        fond_opacite_pct : 0=fond blanc opaque, 100=fond invisible
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    total_width = BUTTON_WIDTH * 2 + BUTTON_SPACING

    # Convertir % -> points PDF
    y_pct_val = y_pct if y_pct is not None else DEFAULT_Y_PCT
    start_y = (y_pct_val / 100.0) * page_height

    if x_pct is not None:
        start_x = (x_pct / 100.0) * page_width
    else:
        start_x = (page_width - total_width) / 2

    # Fond blanc avec opacite calculee
    # fond_opacite_pct=0   -> fond blanc plein (alpha=1 = opaque)
    # fond_opacite_pct=100 -> invisible        (alpha=0 = transparent)
    alpha = 1.0 - (fond_opacite_pct / 100.0)
    alpha = max(0.0, min(1.0, alpha))  # clamp 0..1

    if alpha > 0.01:  # dessiner le fond seulement s'il est visible
        pad = FOND_PADDING
        fond_color = Color(1, 1, 1, alpha=alpha)  # blanc avec transparence
        c.setFillColor(fond_color)
        c.setStrokeColor(fond_color)
        c.rect(
            start_x - pad,
            start_y - pad,
            total_width + 2 * pad,
            BUTTON_HEIGHT + 2 * pad,
            fill=1, stroke=0
        )

    # Bouton rouge YouTube
    draw_button(c, start_x, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#FF0000"), "YouTube")
    c.linkURL(
        f"https://youtube.com/watch?v={quote(video_id)}",
        (start_x, start_y, start_x + BUTTON_WIDTH, start_y + BUTTON_HEIGHT),
        relative=0
    )

    # Bouton vert Jouer ici
    x2 = start_x + BUTTON_WIDTH + BUTTON_SPACING
    draw_button(c, x2, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#28a745"), "Jouer ici")
    c.linkURL(
        f"{player_url}?v={quote(video_id)}",
        (x2, start_y, x2 + BUTTON_WIDTH, start_y + BUTTON_HEIGHT),
        relative=0
    )

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

    Args:
        source_pdf      : PDF source (sans boutons)
        target_pdf      : PDF destination (avec boutons)
        player_url      : URL page lecteur
        video_id        : ID video YouTube
        orientation     : "V" (portrait) | "H" (paysage) - info seulement
        fond_opacite_pct: 0=fond blanc opaque, 100=transparent (float 0-100)
        pos_x           : % largeur depuis gauche (None=centre)
        pos_y           : % hauteur depuis bas    (None=2% = marge basse)

    Returns:
        True si succes
    """
    if not HAS_PDF_LIBS:
        print("  ✗ pypdf/reportlab manquant - partition ignoree")
        return False

    try:
        reader = PdfReader(source_pdf)
        writer = PdfWriter()

        first_page = reader.pages[0]
        width  = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)

        overlay_pdf = create_overlay(
            width, height, player_url, video_id,
            x_pct=pos_x,
            y_pct=pos_y,
            fond_opacite_pct=fond_opacite_pct
        )
        first_page.merge_page(overlay_pdf.pages[0])
        writer.add_page(first_page)

        for page in reader.pages[1:]:
            writer.add_page(page)

        target_pdf.parent.mkdir(parents=True, exist_ok=True)
        with open(target_pdf, "wb") as f:
            writer.write(f)

        # Sauvegarder signature des parametres pour detecter les changements
        sig = _params_signature(video_id, orientation, fond_opacite_pct, pos_x, pos_y)
        _sauvegarder_signature(target_pdf, sig)

        return True

    except Exception as e:
        print(f"  ✗ Erreur ajout boutons : {e}")
        return False


# ============================================================================
# LECTURE __correspondance.csv
# ============================================================================

def _normaliser_cle_csv(pdf_name: str) -> str:
    """Normalise une cle pdf_name : retire prefixe __partition_, normalise."""
    nom = pdf_name.strip()
    nom = re.sub(r'^__partition[\s_]+', '', nom, flags=re.IGNORECASE)
    stem = Path(nom).stem
    ext  = Path(nom).suffix
    stem = unicodedata.normalize('NFD', stem)
    stem = ''.join(c for c in stem if unicodedata.category(c) != 'Mn')
    stem = stem.replace("'", "_").replace("\u2019", "_").replace(" ", "_")
    stem = stem.lower()
    return stem + ext.lower()


def _parse_float(val, defaut=None) -> Optional[float]:
    """Convertit valeur CSV en float ou defaut si vide/invalide."""
    v = val.strip() if val else ""
    if not v:
        return defaut
    try:
        return float(v.replace(",", "."))  # accepte virgule ou point
    except ValueError:
        return defaut


def _parse_orientation(val: str) -> str:
    """Normalise orientation : V/H insensible a la casse."""
    v = val.strip().upper()
    if v in ("H", "LANDSCAPE", "L", "PAYSAGE"):
        return "H"
    return "V"  # defaut portrait


def _parse_fond(val: str) -> float:
    """Convertit fond_transparent CSV en % d opacite (0=opaque, 100=invisible).
    Vide ou invalide -> 0 (fond blanc opaque, defaut).
    """
    v = val.strip() if val else ""
    if not v:
        return DEFAULT_FOND_OPACITE_PCT
    try:
        pct = float(v.replace(",", "."))
        return max(0.0, min(100.0, pct))
    except ValueError:
        return DEFAULT_FOND_OPACITE_PCT


def _get_col(row, *noms):
    """Lit la premiere colonne trouvee parmi les noms proposes (insensible casse)."""
    row_lower = {k.lower().strip(): v for k, v in row.items() if k}
    for nom in noms:
        val = row_lower.get(nom.lower())
        if val is not None:
            return str(val).strip()
    return ""


def charger_correspondances(csv_path: Path) -> dict:
    """Charge correspondances partition -> YouTube + parametres depuis CSV.

    Noms de colonnes supportes (insensible a la casse) :
        nom_partition__pdf  | pdf_name      -> nom du fichier partition
        youtube_url         | url           -> URL YouTube
        orientation                         -> V ou H
        transparence        | fond_transparent -> 0-100%
        position_Horizontale | x             -> % largeur
        position_verticale  | y             -> % hauteur depuis bas

    Returns:
        Dict {nom_pdf_normalise: {video_id, orientation, fond_opacite_pct, x, y}}
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
                youtube_url = _get_col(row,
                    "youtube_url", "url", "youtube")

                if not pdf_name_brut:
                    continue

                pdf_name = _normaliser_cle_csv(pdf_name_brut)

                video_id = youtube_url.split("v=")[-1].split("&")[0] if "v=" in youtube_url else youtube_url

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


def _params_signature(video_id: str, orientation: str, fond_opacite_pct: float,
                      pos_x, pos_y) -> str:
    """Calcule une signature textuelle des parametres CSV."""
    return f"{video_id}|{orientation}|{fond_opacite_pct}|{pos_x}|{pos_y}"


def _lire_signature(target_pdf: Path) -> str:
    """Lit la signature sauvegardee dans le fichier .params adjacent au PDF."""
    params_file = target_pdf.with_suffix(".params")
    if params_file.exists():
        try:
            return params_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return ""


def _sauvegarder_signature(target_pdf: Path, signature: str) -> None:
    """Sauvegarde la signature dans un fichier .params adjacent au PDF."""
    params_file = target_pdf.with_suffix(".params")
    try:
        params_file.write_text(signature, encoding="utf-8")
    except Exception:
        pass


def doit_regenerer_partition(source_pdf: Path, target_pdf: Path,
                              video_id: str = "", orientation: str = "V",
                              fond_opacite_pct: float = 0.0,
                              pos_x=None, pos_y=None) -> bool:
    """Verifie si partition doit etre regeneree.

    Regenere si :
    - target absent
    - source plus recent que target
    - parametres CSV ont change depuis la derniere generation
      (detecte via fichier .params adjacent au PDF final)
    """
    if not target_pdf.exists():
        return True

    if source_pdf.stat().st_mtime > target_pdf.stat().st_mtime:
        return True

    # Verifier si les parametres ont change
    sig_actuelle  = _params_signature(video_id, orientation, fond_opacite_pct, pos_x, pos_y)
    sig_sauvegardee = _lire_signature(target_pdf)
    if sig_actuelle != sig_sauvegardee:
        return True

    return False

# Fin partition_utils.py v1.8