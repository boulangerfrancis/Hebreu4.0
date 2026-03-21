# pdf_utils.py — Version 1.1
# Gestion des conversions DOCX vers PDF
# v1.1: Correction logique "PDF créé aujourd'hui" pour éviter reconversion en boucle

from pathlib import Path
from datetime import datetime
from typing import Tuple

# Variable globale : heure de début de la session
SESSION_START_TIME = datetime.now()

def pdf_cree_aujourdhui(pdf_path: Path) -> bool:
    """Vérifie si un PDF a été créé aujourd'hui.
    
    Args:
        pdf_path: Chemin du PDF
        
    Returns:
        True si créé aujourd'hui
    """
    if not pdf_path.exists():
        return False
    
    pdf_mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime)
    return pdf_mtime.date() == datetime.now().date()

def doit_regenerer_pdf(docx_path: Path, pdf_path: Path, config_regeneration, 
                       regenerer_aujourdhui: bool = True) -> Tuple[bool, str]:
    """Détermine si un PDF doit être regénéré.
    
    v1.1: Si PDF créé aujourd'hui, vérifie qu'il soit créé AVANT cette session
    pour éviter de reconvertir les PDF qu'on vient de générer.
    
    Args:
        docx_path: Chemin du DOCX source
        pdf_path: Chemin du PDF destination
        config_regeneration: Valeur config (True, False, ou "JJ/MM/AAAA")
        regenerer_aujourdhui: Regénérer si PDF créé aujourd'hui
        
    Returns:
        (doit_regenerer, raison)
    """
    # 1. PDF inexistant
    if not pdf_path.exists():
        return (True, "PDF inexistant")
    
    # 2. Mode regeneration = True : tout regénérer
    if config_regeneration is True:
        return (True, "Regénération forcée (config)")
    
    # 3. Mode regeneration = date : regénérer si DOCX modifié après date
    if isinstance(config_regeneration, str):
        try:
            date_limite = datetime.strptime(config_regeneration, "%d/%m/%Y")
            docx_mtime = datetime.fromtimestamp(docx_path.stat().st_mtime)
            if docx_mtime > date_limite:
                return (True, f"DOCX modifié après {config_regeneration}")
        except ValueError:
            # Format date invalide, ignorer
            pass
    
    # 4. PDF créé aujourd'hui AVANT cette session
    # v1.1: Évite de reconvertir les PDF créés dans CETTE session
    if regenerer_aujourdhui:
        pdf_mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime)
        
        # PDF créé aujourd'hui ?
        if pdf_mtime.date() == datetime.now().date():
            # Créé AVANT le début de cette session ?
            if pdf_mtime < SESSION_START_TIME:
                return (True, "PDF créé aujourd'hui (session précédente)")
            # Sinon : créé PENDANT cette session → ne pas reconvertir
    
    # 5. DOCX plus récent que PDF
    if docx_path.stat().st_mtime > pdf_path.stat().st_mtime:
        return (True, "DOCX plus récent")
    
    return (False, "")

def traiter_conversions_dossier(dossier: Path, fichiers: list, normaliser_nom_func, 
                                convertir_func, config: dict, log_func) -> int:
    """Traite les conversions DOCX→PDF d'un dossier.
    
    Args:
        dossier: Dossier à traiter
        fichiers: Liste des fichiers du dossier
        normaliser_nom_func: Fonction de normalisation noms
        convertir_func: Fonction de conversion (depuis docx2pdf)
        config: Configuration (regeneration, regenerer_pdf_aujourd_hui)
        log_func: Fonction de log
        
    Returns:
        Nombre de conversions effectuées
    """
    nb_conversions = 0
    
    for fichier in fichiers:
        # Ignorer fichiers temporaires Word
        if fichier.name.startswith('~$'):
            continue
        
        # Fichiers .doc ou .docx uniquement
        if fichier.suffix.lower() not in ['.doc', '.docx']:
            continue
        
        # Nom du PDF cible
        nom_pdf = normaliser_nom_func(fichier.stem + ".pdf")
        pdf_path = dossier / nom_pdf
        
        # Vérifier si conversion nécessaire
        doit_convertir, raison = doit_regenerer_pdf(
            fichier,
            pdf_path,
            config.get("regeneration", False),
            config.get("regenerer_pdf_aujourd_hui", True)
        )
        
        if doit_convertir:
            log_func(f"Conversion ({raison}): {fichier.name} → {nom_pdf}")
            success = convertir_func(fichier, pdf_path, log_func)
            
            if success:
                nb_conversions += 1
            else:
                log_func(f"✗ Échec conversion: {fichier.name}")
    
    return nb_conversions

def est_fichier_copiable(fichier: Path, extensions_copiables: set) -> bool:
    """Vérifie si un fichier doit être copié vers HTML.
    
    Args:
        fichier: Fichier à tester
        extensions_copiables: Set d'extensions autorisées
        
    Returns:
        True si copiable
    """
    # STRUCTURE.py jamais copié
    if fichier.name == "STRUCTURE.py":
        return False
    
    # Fichiers temporaires Word jamais copiés
    if fichier.name.startswith('~$'):
        return False
    
    # DOCX jamais copiés (convertis en PDF)
    ext = fichier.suffix.lower().lstrip(".")
    if ext in ("doc", "docx"):
        return False
    
    # Extensions autorisées
    if ext in extensions_copiables:
        return True
    
    # Fichiers sans extension si autorisé
    if ext == "" and "" in extensions_copiables:
        return True
    
    return False

# Fin pdf_utils.py v1.1
