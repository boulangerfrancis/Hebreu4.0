# partition_utils.py — Version 1.0
# Traitement partitions musicales avec boutons YouTube

"""
Module de traitement des partitions avec boutons YouTube.

Basé sur Place_Bouton_PDF.py avec améliorations:
- Intégration architecture modulaire
- Lecture __correspondance.csv
- Génération conditionnelle (si source plus récent)
- Gestion erreurs robuste
"""

import csv
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
from typing import Dict, Optional

try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, white
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False
    print("AVERTISSEMENT : pypdf ou reportlab manquant")
    print("  pip install pypdf reportlab")

# Constantes boutons
BUTTON_WIDTH = 140
BUTTON_HEIGHT = 50
MARGIN = 40
BUTTON_SPACING = 20

def draw_button(c, x, y, width, height, color, text):
    """Dessine un bouton avec cercle play."""
    radius = height * 0.4
    
    # Rectangle arrondi
    c.setFillColor(color)
    c.roundRect(x, y, width, height, radius/2, fill=1)

    # Cercle blanc pour triangle
    circle_x = x + radius + 5
    circle_y = y + height / 2
    c.setFillColor(white)
    c.circle(circle_x, circle_y, radius, fill=1)

    # Triangle dans cercle
    c.setFillColor(color)
    tri_half = radius * 0.6
    path = c.beginPath()
    path.moveTo(circle_x - tri_half*0.6, circle_y - tri_half)
    path.lineTo(circle_x - tri_half*0.6, circle_y + tri_half)
    path.lineTo(circle_x + tri_half, circle_y)
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    # Texte centré
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", int(height/3))
    text_x = x + 2*radius + 10
    text_y = y + (height - int(height/3)) / 2 - 1
    c.drawString(text_x, text_y, text)

def create_overlay(page_width, page_height, player_url, video_id):
    """Crée overlay PDF avec 2 boutons."""
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    total_width = BUTTON_WIDTH*2 + BUTTON_SPACING
    start_x = (page_width - total_width) / 2
    y = MARGIN

    # Bouton rouge YouTube
    draw_button(c, start_x, y, BUTTON_WIDTH, BUTTON_HEIGHT, HexColor("#FF0000"), "YouTube")
    youtube_link = f"https://youtube.com/watch?v={quote(video_id)}"
    c.linkURL(youtube_link, (start_x, y, start_x+BUTTON_WIDTH, y+BUTTON_HEIGHT), relative=0)

    # Bouton vert Jouer ici
    x2 = start_x + BUTTON_WIDTH + BUTTON_SPACING
    draw_button(c, x2, y, BUTTON_WIDTH, BUTTON_HEIGHT, HexColor("#28a745"), "Jouer ici")
    player_link = f"{player_url}?v={quote(video_id)}"
    c.linkURL(player_link, (x2, y, x2+BUTTON_WIDTH, y+BUTTON_HEIGHT), relative=0)

    c.save()
    packet.seek(0)
    return PdfReader(packet)

def ajouter_boutons_partition(source_pdf: Path, target_pdf: Path, 
                               player_url: str, video_id: str) -> bool:
    """Ajoute boutons YouTube sur première page partition.
    
    Args:
        source_pdf: PDF source (sans boutons)
        target_pdf: PDF destination (avec boutons)
        player_url: URL page lecteur (/musique/index.html)
        video_id: ID vidéo YouTube
        
    Returns:
        True si succès
    """
    if not HAS_PDF_LIBS:
        return False
    
    try:
        reader = PdfReader(source_pdf)
        writer = PdfWriter()

        # Première page avec boutons
        first_page = reader.pages[0]
        width = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)

        overlay_pdf = create_overlay(width, height, player_url, video_id)
        first_page.merge_page(overlay_pdf.pages[0])
        writer.add_page(first_page)

        # Autres pages inchangées
        for page in reader.pages[1:]:
            writer.add_page(page)

        # Sauvegarder
        target_pdf.parent.mkdir(parents=True, exist_ok=True)
        with open(target_pdf, "wb") as f:
            writer.write(f)
        
        return True
        
    except Exception as e:
        print(f"✗ Erreur ajout boutons : {e}")
        return False

def charger_correspondances(csv_path: Path) -> Dict[str, str]:
    """Charge correspondances partition → YouTube depuis CSV.
    
    Format CSV attendu:
    pdf_name,youtube_url
    partition1.pdf,https://youtube.com/watch?v=VIDEO_ID
    
    Args:
        csv_path: Chemin __correspondance.csv
        
    Returns:
        Dict {nom_pdf: video_id}
    """
    if not csv_path.exists():
        return {}
    
    correspondances = {}
    
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pdf_name = row.get("pdf_name", "")
                youtube_url = row.get("youtube_url", "")
                
                # Extraire ID vidéo
                if "v=" in youtube_url:
                    video_id = youtube_url.split("v=")[-1].split("&")[0]
                else:
                    video_id = youtube_url
                
                correspondances[pdf_name] = video_id
        
        return correspondances
        
    except Exception as e:
        print(f"✗ Erreur lecture correspondances : {e}")
        return {}

def doit_regenerer_partition(source_pdf: Path, target_pdf: Path) -> bool:
    """Vérifie si partition doit être regénérée.
    
    Regénère si:
    - Target inexistant
    - Source plus récent que target
    
    Args:
        source_pdf: PDF source (sans boutons)
        target_pdf: PDF cible (avec boutons)
        
    Returns:
        True si regénération nécessaire
    """
    if not target_pdf.exists():
        return True
    
    if source_pdf.stat().st_mtime > target_pdf.stat().st_mtime:
        return True
    
    return False

# Fin partition_utils.py v1.0
