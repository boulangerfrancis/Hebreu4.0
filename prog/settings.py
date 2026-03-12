# settings.py — Version 1.0
# Fusion de config.py (v3.0) + options.py (v1.1)
# Un seul fichier de configuration pour tout le projet

version = ("settings.py", "1.0")
print(f"[Import] {version[0]} - Version {version[1]} chargé")

# ============================================================================
# CHEMINS DU PROJET
# ============================================================================

DOSSIER_RACINE = r"C:\SiteGITHUB\Hebreu4.0"
DOSSIER_DOCUMENTS = f"{DOSSIER_RACINE}\\documents"
DOSSIER_HTML = f"{DOSSIER_RACINE}\\html"

# Base path pour les liens HTML
# "" pour test local (serveur sur /html)
# "/Hebreu4.0/html" pour GitHub Pages
BASE_PATH = "/Hebreu4.0/html"
# BASE_PATH = ""  # ← Décommenter pour test local

# ============================================================================
# CONFIGURATION GÉNÉRALE
# ============================================================================

CONFIG = {
    # ----------------------------------------
    # TITRES ET LABELS
    # ----------------------------------------
    "titre_site": "Hébreu biblique",

    # ----------------------------------------
    # AFFICHAGE DOSSIERS/FICHIERS
    # Format : [préfixe_dossier, suffixe_dossier, préfixe_fichier, suffixe_fichier]
    # ----------------------------------------
    "ajout_affichage": ["📁 ", "", "📘 ", ""],

    # ----------------------------------------
    # STRUCTURE ET NAVIGATION
    # ----------------------------------------
    "dossier_tdm": "TDM",
    "voir_structure": False,        # Ajoute commentaires HTML structure
    "lien_souligné_index": False,

    # ----------------------------------------
    # EXTENSIONS ACCEPTÉES (scan documents)
    # ----------------------------------------
    "extensions_acceptees": ["pdf", "doc", "docx", "html", "htm", "txt",
                              "jpg", "jpeg", "png", "gif"],

    # ----------------------------------------
    # DOSSIERS À IGNORER
    # ----------------------------------------
    "ignorer": ["nppBackup", ".git", ".github", "__pycache__",
                "package", "test", "backup_v23", "backup_v24"],

    # ----------------------------------------
    # CONVERSION PDF
    # Options :
    #   False       → comportement normal (PDF absent ou DOCX plus récent)
    #   True        → regénérer TOUS les PDF (si DOCX source présent)
    #   "JJ/MM/AAAA"→ regénérer si DOCX modifié après cette date
    # ----------------------------------------
    "regeneration": False,

    # Regénérer PDF dont le DOCX source a été modifié AUJOURD'HUI
    # (utile pour retravailler un fichier dans la journée)
    "regenerer_pdf_aujourd_hui": False,

    # ----------------------------------------
    # PARTITIONS MUSICALES
    # URL de la page lecteur (bouton "Jouer ici" dans les PDF)
    # ----------------------------------------
    "player_url": "/Hebreu4.0/html/musique/index.html",

    # ----------------------------------------
    # CONTENU GLOBAL HAUT/BAS PAGE
    # ----------------------------------------
    "haut_page": [],
    "bas_page": [],
}

# ============================================================================
# COMPATIBILITÉ : les anciens imports depuis lib1.options et lib1.config
# continuent de fonctionner si on ajoute dans lib1/__init__.py :
#   from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG
# ============================================================================

# Fin settings.py v1.0
