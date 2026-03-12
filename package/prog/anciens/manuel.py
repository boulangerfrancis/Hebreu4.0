# extraire_manuel.py — Version 1.0

version = ("extraire_manuel.py", "1.0")
print(f"[Version] {version[0]} — {version[1]}")

manuel_md = """
§# Manuel d'Utilisation : Génération de Site Web Statique avec Python
§
§## Introduction
§
§Ce manuel décrit comment utiliser les scripts Python `genere_site.py` et `cree_table_des_matieres.py` pour générer un site web statique à partir d'un dossier de documents. Ces scripts convertissent des fichiers (comme des PDF, HTML, DOCX) en un site navigable avec une table des matières dynamique.
§
§- **genere_site.py** : Génère les pages index.html pour chaque dossier et copie les fichiers vers le dossier HTML.
§- **cree_table_des_matieres.py** : Génère la page TDM/index.html (table des matières).
§
§Les scripts sont lancés via `lance.cmd`, un fichier batch Windows qui exécute les deux scripts séquentiellement.
§
§Le système est conçu pour :
§- Créer automatiquement une structure de site.
§- Personnaliser l'affichage (noms, visibilité, positions) via des fichiers de configuration.
§- Supporter des mises en forme simples (gras, italique, couleur, souligné).
§
§Pour les non-informaticiens : Suivez les étapes basiques pour un usage simple.
§Pour les informaticiens : Sections avancées pour personnalisation et debug.
§
§## Prérequis
§
§### Pour tous les utilisateurs
§- **Système d'exploitation** : Windows (à cause de la conversion DOCX via Microsoft Word et de lance.cmd).
§- **Python 3.8+** : Téléchargez et installez depuis [python.org](https://www.python.org). Cochez "Add Python to PATH" lors de l'installation.
§- **Microsoft Word** (optionnel mais recommandé) : Pour convertir .doc/.docx en .pdf. Si absent, les fichiers DOCX ne seront pas convertis.
§- **Dossiers principaux** :
§  - `/documents` : Contient vos fichiers et sous-dossiers (source).
§  - `/html` : Dossier généré (site web final, ouvrez index.html dans un navigateur).
§
§### Installation des dépendances (pour non-informaticiens)
§1. Ouvrez une invite de commande (cmd.exe).
§2. Exécutez : `pip install beautifulsoup4 psutil` (win32com est optionnel pour Word).
§
§Pour informaticiens : Les dépendances sont BeautifulSoup (formatage HTML), psutil (gestion processus Word), win32com (interface Word).
§
§## Installation et Structure des Fichiers
§
§1. Créez un dossier principal, ex : `C:\MonSite`.
§2. Placez les fichiers suivants dans `C:\MonSite\prog` :
§   - `genere_site.py`
§   - `cree_table_des_matieres.py`
§   - `lance.cmd` (contenu : `@echo off` suivi de `python genere_site.py` puis `python cree_table_des_matieres.py` puis `pause`)
§   - Dossier `/lib1` : Contient `config.py`, `options.py`, `style.css`.
§
§3. Créez `/documents` dans `C:\MonSite` : Mettez-y vos fichiers et sous-dossiers.
§   - Exemple : `/documents/mon_dossier/mon_fichier.pdf`.
§   - Pour personnaliser : Ajoutez `STRUCTURE.py` dans chaque dossier (généré automatiquement, modifiable manuellement).
§
§4. Le dossier `/html` sera créé automatiquement.
§
§Pour changer les noms de dossiers :
§- Modifiez `DOSSIER_DOCUMENTS` et `DOSSIER_HTML` dans `/lib1/options.py`.
§- Relancez `lance.cmd`.
§
§Exemple de structure :
§```
§C:\MonSite
§├── prog
§│   ├── genere_site.py
§│   ├── cree_table_des_matieres.py
§│   ├── lance.cmd
§│   └── lib1
§│       ├── config.py
§│       ├── options.py
§│       └── style.css
§├── documents
§│   ├── entete_general.html (optionnel)
§│   ├── mon_dossier
§│   │   ├── STRUCTURE.py
§│   │   └── mon_fichier.pdf
§│   └── TDM
§└── html (généré)
§    ├── index.html
§    └── TDM
§        └── index.html
§```
§
§## Utilisation Basique (pour non-informaticiens)
§
§1. **Préparez vos documents** : Placez fichiers et dossiers dans `/documents`.
§2. **Lancez la génération** : Double-cliquez sur `lance.cmd`.
§3. **Ouvrez le site** : Ouvrez `/html/index.html` dans un navigateur.
§
§Exemple :
§- Ajoutez `/documents/introduction.pdf`.
§- Lancez `lance.cmd`.
§- Lien vers "introduction.pdf" apparaît dans l'index.
§
§Pour masquer un fichier :
§- Ouvrez le `STRUCTURE.py` du dossier.
§- Changez `"affiché_index": True` en `False`.
§- Relancez `lance.cmd`.
§
§Pour changer un nom :
§- Dans `STRUCTURE.py`, modifiez `"nom_affiché": "Nouveau **Nom** [rouge]Important[/rouge]"`.
§- Relancez.
§
§## Configuration
§
§### config.py (global)
§- `"voir_structure": True` : Ajoute commentaires debug dans HTML.
§
§### options.py
§- `extensions_acceptees` : Ajoutez "jpg" pour inclure images.
§- `dossier_tdm = "Sommaire"` : Change le nom du dossier TDM.
§
§### STRUCTURE.py (par dossier)
§- Clés principales :
§  - `nom_affiché` : Texte affiché avec formatage (**gras**, __italique__, --souligné--, [rouge]couleur[/rouge]).
§  - `nom_navigation` : Texte dans les bulles de navigation.
§  - `nom_TDM` : Texte dans la table des matières.
§  - `position` : Ordre d'affichage.
§  - `affiché_index` / `affiché_TDM` : True/False pour visibilité.
§
§Exemple :
§```
§STRUCTURE = {
§    "dossiers": [
§        {"nom_document": "mon_dossier", "nom_affiché": "Mon **Dossier**", "nom_navigation": "Navigation --Perso--", "position": 1}
§    ],
§    "fichiers": [
§        {"nom_document": "fichier.pdf", "nom_affiché": "Fichier [vert]Important[/vert]", "affiché_index": False}
§    ]
§}
§```
§
§## Utilisation Avancée (informaticiens)
§
§- Lancement manuel : `python genere_site.py` puis `python cree_table_des_matieres.py`.
§- Debug : Logs dans `generation.log`.
§- Personnalisation : Modifiez `appliquer_style` pour nouveaux formats.
§- Navigation : Utilise `nom_navigation` des parents.
§
§**Fin du manuel.**
"""

def extraire_manuel() -> None:
    """Extrait la chaîne manuel_md et crée le fichier manuel.md."""
    lignes = [ligne[1:] + "\n" for ligne in manuel_md.split("\n") if ligne.startswith("§")]
    with open("manuel.md", "w", encoding="utf-8") as f:
        f.writelines(lignes)
    print("manuel.md créé avec succès !")

if __name__ == "__main__":
    extraire_manuel()

# fin du "extraire_manuel.py" version "1.0"