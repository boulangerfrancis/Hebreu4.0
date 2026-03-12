# config.py — Version 3.0
# Configuration globale du générateur de site

CONFIG = {
    # ========================================
    # TITRES ET LABELS
    # ========================================
    "titre_site": "Hébreu biblique",
    
    # ========================================
    # AFFICHAGE DOSSIERS/FICHIERS
    # ========================================
    # Format : [préfixe_dossier, suffixe_dossier, préfixe_fichier, suffixe_fichier]
    "ajout_affichage": ["📁 ", "", "📘 ", ""],
    
    # ========================================
    # STRUCTURE ET NAVIGATION
    # ========================================
    "dossier_tdm": "TDM",
    "voir_structure": False,  # Ajoute commentaires HTML structure
    "lien_souligné_index": False,
    
    # ========================================
    # EXTENSIONS ACCEPTÉES
    # ========================================
    "extensions_acceptees": ["pdf", "doc", "docx", "html", "htm", "txt", "jpg", "jpeg", "png", "gif"],
    
    # ========================================
    # DOSSIERS À IGNORER
    # ========================================
    "ignorer": ["nppBackup", ".git", ".github", "__pycache__","package","test","backup_v23"],
    
    # ========================================
    # CONVERSION PDF (v23.1)
    # ========================================
    # Options :
    # - True : Regénérer TOUS les PDF
    # - "JJ/MM/AAAA" : Regénérer si DOCX modifié après cette date
    # - False : Comportement normal (PDF absent ou DOCX plus récent)
    "regeneration": False,
    
    # Regénérer PDF créés aujourd'hui (erreurs possibles)
    "regenerer_pdf_aujourd_hui": False,
    
    # ========================================
    # CONTENU GLOBAL HAUT/BAS PAGE
    # ========================================
    "haut_page": [],
    
    "bas_page": [],
}

# Fin config.py v3.0
