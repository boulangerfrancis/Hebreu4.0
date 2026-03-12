# options.py — Version 1.1

version = ("options.py", "1.1")
print(f"[Import] {version[0]} - Version {version[1]} chargé")

# Chemins relatifs ou absolus selon ton environnement
DOSSIER_RACINE = r"C:\SiteGITHUB\Hebreu4.0"
DOSSIER_DOCUMENTS = f"{DOSSIER_RACINE}\\documents"
DOSSIER_HTML = f"{DOSSIER_RACINE}\\html"

# Base path pour les liens (GitHub Pages vs local)
# "" pour test local (serveur sur /html)
# "/hebreu4.0" pour GitHub Pages (repo à la racine du user site)
BASE_PATH = "/Hebreu4.0/html"  # ← Modifier ici : "" pour local, "/Hebreu4.0/html" pour GitHub
#BASE_PATH = ""  # ← Modifier ici : "" pour local, "/Hebreu4.0" pour GitHub

# fin du "options.py" version "1.1"