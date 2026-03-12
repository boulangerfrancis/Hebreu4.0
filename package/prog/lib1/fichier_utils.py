# fichier_utils.py — Version 1.0
# Gestion fichiers spéciaux et filtrage

"""
Module de gestion des fichiers spéciaux.

Règles:
- Fichiers commençant par "__" sont ignorés (commentaires)
- SAUF "__partition_*.docx" (sources partitions)
- "__correspondance.csv" : mapping partition → YouTube
"""

from pathlib import Path
from typing import Tuple

def est_fichier_commentaire(nom_fichier: str) -> bool:
    """Vérifie si un fichier est un commentaire (à ignorer).
    
    Règles:
    - Commence par "__" → commentaire
    - SAUF "__partition_*.docx" → source partition
    - SAUF "__correspondance.csv" → mapping YouTube
    
    Args:
        nom_fichier: Nom du fichier
        
    Returns:
        True si commentaire (à ignorer)
    """
    if not nom_fichier.startswith("__"):
        return False
    
    # Exceptions
    if nom_fichier.startswith("__partition_") and nom_fichier.endswith(".docx"):
        return False
    
    if nom_fichier == "__correspondance.csv":
        return False
    
    # Tous les autres "__*" sont des commentaires
    return True

def est_partition_source(nom_fichier: str) -> bool:
    """Vérifie si un fichier est une partition source.
    
    Args:
        nom_fichier: Nom du fichier
        
    Returns:
        True si partition source (__partition_*.docx)
    """
    return nom_fichier.startswith("__partition_") and nom_fichier.endswith(".docx")

def nom_partition_final(nom_source: str) -> Tuple[str, str]:
    """Convertit nom partition source en nom final.
    
    Args:
        nom_source: "__partition_Nom Partition.docx"
        
    Returns:
        (nom_pdf_brut, nom_pdf_normalise)
        ("Nom Partition.pdf", "nom_partition.pdf")
    """
    if not est_partition_source(nom_source):
        return (nom_source, nom_source)
    
    # Enlever "__partition_"
    nom_sans_prefix = nom_source[len("__partition_"):]
    
    # Remplacer .docx par .pdf
    nom_pdf = Path(nom_sans_prefix).stem + ".pdf"
    
    return nom_pdf

def doit_filtrer_fichier(nom_fichier: str) -> bool:
    """Détermine si un fichier doit être ignoré du scan.
    
    Utilise est_fichier_commentaire() + autres règles.
    
    Args:
        nom_fichier: Nom du fichier
        
    Returns:
        True si fichier à ignorer
    """
    # Temporaires Word
    if nom_fichier.startswith('~$'):
        return True
    
    # STRUCTURE.py
    if nom_fichier == "STRUCTURE.py":
        return True
    
    # Commentaires
    if est_fichier_commentaire(nom_fichier):
        return True
    
    return False

# Fin fichier_utils.py v1.0
