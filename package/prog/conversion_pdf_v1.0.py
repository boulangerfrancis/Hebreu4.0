# conversion_pdf.py — Version 1.0
# Module wrapper pour conversion DOCX→PDF via docx_to_pdf.py

"""
Module de conversion DOCX vers PDF.

Utilise docx_to_pdf.py (PDFCreator) pour les conversions.
Compatible avec l'architecture modulaire du générateur.
"""

from pathlib import Path
import sys

# Importer le module de conversion PDFCreator
try:
    from docx_to_pdf import docx_to_pdf
    HAS_PDFCREATOR = True
except ImportError:
    HAS_PDFCREATOR = False
    print("AVERTISSEMENT : docx_to_pdf.py non trouvé ou PDFCreator non installé")

def convertir_docx_vers_pdf(docx_path: Path, pdf_path: Path, log_func) -> bool:
    """Convertit un fichier DOCX en PDF via PDFCreator.
    
    Args:
        docx_path: Chemin du fichier DOCX source
        pdf_path: Chemin du fichier PDF destination
        log_func: Fonction de log (affichage messages)
        
    Returns:
        True si conversion réussie, False sinon
    """
    if not HAS_PDFCREATOR:
        log_func("✗ PDFCreator non disponible")
        return False
    
    try:
        # Appeler fonction de conversion
        docx_to_pdf(
            str(docx_path),
            str(pdf_path),
            timeout=60  # 60 secondes max
        )
        return True
        
    except FileNotFoundError as e:
        log_func(f"✗ Fichier introuvable : {e}")
        return False
        
    except TimeoutError as e:
        log_func(f"✗ Timeout : {e}")
        return False
        
    except Exception as e:
        log_func(f"✗ Erreur conversion : {e}")
        return False

# Fin conversion_pdf.py
