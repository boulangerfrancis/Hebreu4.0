# cree_table_des_matieres.py — Version 6.29

version = ("cree_table_des_matieres.py", "6.29")
print(f"[Version] {version[0]} — {version[1]}")

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

from lib1.options import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH
from lib1.config import CONFIG
from lib1 import html_utils as html  # v6.29: Import html_utils pour templates

def lire(variable: dict, element: str, defaut) -> object:
    """Lit une valeur dans un dictionnaire, retourne la valeur par défaut sinon.

    Args:
        variable (dict): Dictionnaire source.
        element (str): Clé recherchée.
        defaut: Valeur retournée si la clé est absente.

    Returns:
        object: Valeur trouvée ou valeur par défaut.
    """
    return variable.get(element, defaut)

voir_structure = lire(CONFIG, "voir_structure", False)

def log(msg: str) -> None:
    """Affiche un message de debug préfixé.

    Args:
        msg (str): Message à afficher.
    """
    print(f"[TDM DEBUG] {msg}")

def appliquer_style(texte: str) -> str:
    """Applique les balises Markdown-like au texte.

    Supporte :
    - **gras**
    - __italique__
    - --souligné--
    - ~~barré~~
    - [couleur]texte[/couleur]

    Args:
        texte (str): Texte brut contenant les balises.

    Returns:
        str: Texte converti en HTML.
    """
    texte = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texte)
    texte = re.sub(r'__(.*?)__', r'<em>\1</em>', texte)
    texte = re.sub(r'--(.*?--)', r'<u>\1</u>', texte)
    texte = re.sub(r'~~(.*?)~~', r'<del>\1</del>', texte)

    couleurs = {"rouge": "red", "bleu": "blue", "vert": "green", "jaune": "gold",
                "violet": "purple", "orange": "orange", "gris": "gray", "noir": "black"}
    for nom, code in couleurs.items():
        texte = texte.replace(f"[{nom}]", f'<span style="color:{code}">')
        texte = texte.replace(f"[/{nom}]", "</span>")

    texte = re.sub(r'\[couleur:(#[0-9a-fA-F]{6}|rgba?\([^)]+\))\]', lambda m: f'<span style="color:{m.group(1)}">', texte)
    texte = texte.replace("[/couleur]", "</span>")
    return texte

def deb_html(titre: str) -> str:
    """Génère le début du document HTML.

    Args:
        titre (str): Titre de la page.

    Returns:
        str: Balises <html><head>...</head><body>.
    """
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8"/>
    <title>{titre}</title>
    <link href="{BASE_PATH}/style.css" rel="stylesheet"/>
</head>
<body>"""

def fin_html() -> str:
    """Génère la fin du document HTML.

    Returns:
        str: Balises </body></html>.
    """
    return """</body>
</html>"""

def plage_html_avec_fallback(dossier: Path, fichier: str, position: str, commun: str) -> str:
    """Lit un fichier HTML avec fallback à la racine et interprétation templates.
    
    v6.29: Utilise html_utils.charger_template_html() pour interpréter {{BASE_PATH}}.

    Args:
        dossier (Path): Dossier local à vérifier.
        fichier (str): Nom du fichier à lire.
        position (str): "début" ou "fin" (pour commentaires debug).
        commun (str): Suffixe pour commentaires debug.

    Returns:
        str: Contenu du fichier avec templates résolus ou chaîne vide.
    """
    local = dossier / fichier
    
    if local.exists():
        modele = local
    else:
        if fichier in ("entete_general.html", "pied_general.html"):
            racine = Path(DOSSIER_DOCUMENTS)
            modele = racine / fichier
            if not modele.exists():
                return ""
        else:
            return ""
    
    # v6.29: Utiliser charger_template_html pour interpréter {{BASE_PATH}}
    contenu = html.charger_template_html(
        modele,
        {"BASE_PATH": BASE_PATH},
        voir_structure,
        position,
        commun
    )
    
    return contenu

def _generer_navigation(chemin_relatif: list[str]) -> str:
    """Génère la barre de navigation pour la page TDM.

    Sur la page TDM on n'affiche pas le bouton « Sommaire » (on y est déjà)
    et le bouton Accueil pointe vers la racine du site.

    Returns:
        str: HTML de la barre de navigation.
    """
    nav = f'<nav class="navigation"><div class="gauche"><a href="{BASE_PATH}/index.html" class="monbouton">Accueil</a>'
    nav += f'</div><div class="droite"></div></nav>'  # Droite vide : pas de bouton Sommaire
    if voir_structure:
        nav = f"<div><!-- début navigation -->{nav}<!-- fin navigation --></div>"
    return nav

def charger_structure(dossier: Path) -> dict:
    """Charge le fichier STRUCTURE.py d'un dossier s'il existe.

    Args:
        dossier (Path): Chemin du dossier contenant éventuellement STRUCTURE.py.

    Returns:
        dict: Contenu de STRUCTURE (dossiers et fichiers) ou dictionnaire vide.
    """
    chemin = dossier / "STRUCTURE.py"
    if chemin.exists():
        try:
            from importlib.machinery import SourceFileLoader
            module = SourceFileLoader("STRUCTURE", str(chemin)).load_module()
            return module.STRUCTURE
        except Exception as e:
            log(f"Erreur lecture STRUCTURE.py dans {dossier} : {e}")
    return {"dossiers": [], "fichiers": []}

def est_visible_tdm(item: dict) -> bool:
    """Vérifie si un élément doit apparaître dans la TDM.

    Args:
        item (dict): Élément de structure (dossier ou fichier).

    Returns:
        bool: True si affiché_TDM est True ou absent.
    """
    return item.get("affiché_TDM", True)

def generer_ligne_dossier(item: dict, lien: str, sous_arbo: str) -> str:
    """Génère le HTML pour un dossier dans l'arbre TDM.

    Args:
        item (dict): Élément dossier.
        lien (str): URL complète du dossier.
        sous_arbo (str): HTML des enfants (peut être vide).

    Returns:
        str: Ligne HTML <li>...</li>.
    """
    nom_affiché = appliquer_style(item.get("nom_affiché", item["nom_document"]))
    if sous_arbo:
        return f'<li><details><summary><a href="{lien}" class="folder-link">{nom_affiché}</a></summary><ul>{sous_arbo}</ul></details></li>\n'
    return f'<li><a href="{lien}" class="folder-link">{nom_affiché}</a></li>\n'

def generer_ligne_fichier(item: dict, lien: str) -> str:
    """Génère le HTML pour un fichier dans l'arbre TDM.

    Args:
        item (dict): Élément fichier.
        lien (str): URL complète du fichier.

    Returns:
        str: Ligne HTML <li>...</li>.
    """
    nom_affiché = appliquer_style(item.get("nom_affiché", item["nom_document"]))
    return f'<li><a href="{lien}">{nom_affiché}</a></li>\n'

def construire_arbo_recursif(dossier_sources: Path, prefixe_html: str = "") -> str:
    """Construit récursivement l'arbre HTML de la TDM.

    Args:
        dossier_sources (Path): Dossier sources à analyser.
        prefixe_html (str): Préfixe URL pour les liens (ex: "/dossier_parent").

    Returns:
        str: HTML de l'arbre (<li>...</li>).
    """
    struc = charger_structure(dossier_sources)
    html_arbre = ""

    # Tri des dossiers et fichiers
    struc["dossiers"].sort(key=lambda x: x.get("position", 9999))
    struc["fichiers"].sort(key=lambda x: x.get("position", 9999))

    for item in struc["dossiers"]:
        if est_visible_tdm(item):
            nom_html = item["nom_html"]
            lien = f"{BASE_PATH}{prefixe_html}/{nom_html}/index.html"
            sous_arbo = construire_arbo_recursif(dossier_sources / item["nom_document"], f"{prefixe_html}/{nom_html}")
            html_arbre += generer_ligne_dossier(item, lien, sous_arbo)

    for item in struc["fichiers"]:
        if est_visible_tdm(item):
            nom_html = item["nom_html"]
            lien = f"{BASE_PATH}{prefixe_html}/{nom_html}"
            html_arbre += generer_ligne_fichier(item, lien)

    return html_arbre

def charger_configuration_tdm() -> dict:
    """Charge la configuration spécifique à la page TDM depuis documents/TDM/STRUCTURE.py.

    Returns:
        dict: Configuration (entete, pied, navigation, etc.) ou dict vide.
    """
    tdm_sources = Path(DOSSIER_DOCUMENTS) / "TDM"
    return charger_structure(tdm_sources)

def ajouter_entete(html_parts: list, config_tdm: dict, tdm_sources: Path) -> None:
    """Ajoute entête général, entête local ou titre par défaut.

    Args:
        html_parts (list): Liste des parties HTML à compléter.
        config_tdm (dict): Configuration TDM.
        tdm_sources (Path): Chemin vers documents/TDM.
    """
    if config_tdm.get("entete_general", False):
        html_parts.append(plage_html_avec_fallback(tdm_sources, "entete_general.html", "début", "_général"))

    if config_tdm.get("entete", False):
        html_parts.append(plage_html_avec_fallback(tdm_sources, "entete.html", "début", ""))
    else:
        html_parts.append("<h1>Table des matières</h1>")

def ajouter_navigation(html_parts: list, config_tdm: dict) -> None:
    """Ajoute la barre de navigation si activée dans la config TDM.

    Args:
        html_parts (list): Liste des parties HTML.
        config_tdm (dict): Configuration TDM.
    """
    if config_tdm.get("navigation", False):
        html_parts.append(_generer_navigation([]))

def ajouter_arbre_tdm(html_parts: list, arbre_html: str) -> None:
    """Ajoute l'arbre TDM dans le conteneur centré.

    Args:
        html_parts (list): Liste des parties HTML.
        arbre_html (str): HTML de l'arbre généré.
    """
    html_parts.append('<div class="table-container"><table class="dossiers"><tbody><tr><td>')
    html_parts.append(f'<ul class="tree">{arbre_html}</ul>')
    html_parts.append('</td></tr></tbody></table></div>')

def ajouter_pied(html_parts: list, config_tdm: dict, tdm_sources: Path) -> None:
    """Ajoute pied local et pied général si configurés.

    Args:
        html_parts (list): Liste des parties HTML.
        config_tdm (dict): Configuration TDM.
        tdm_sources (Path): Chemin vers documents/TDM.
    """
    if config_tdm.get("pied", False):
        html_parts.append(plage_html_avec_fallback(tdm_sources, "pied.html", "fin", ""))

    if config_tdm.get("pied_general", False):
        html_parts.append(plage_html_avec_fallback(tdm_sources, "pied_general.html", "fin", "_général"))

def generer_tdm() -> None:
    """Fonction principale : génère TDM/index.html avec structure modulaire."""
    log("=== DÉBUT GÉNÉRATION TDM ===")
    racine_sources = Path(DOSSIER_DOCUMENTS)
    if not racine_sources.exists():
        log("ERREUR : dossier sources n'existe pas !")
        return

    config_tdm = charger_configuration_tdm()
    arbre_html = construire_arbo_recursif(racine_sources)

    html_parts = []
    html_parts.append(deb_html("Table des matières"))

    tdm_sources = racine_sources / "TDM"

    ajouter_entete(html_parts, config_tdm, tdm_sources)
    ajouter_navigation(html_parts, config_tdm)
    ajouter_arbre_tdm(html_parts, arbre_html)
    ajouter_pied(html_parts, config_tdm, tdm_sources)

    html_parts.append(fin_html())

    html_brut = "".join(html_parts)
    html_prettify = BeautifulSoup(html_brut, 'html.parser').prettify()

    tdm_path = Path(DOSSIER_HTML) / "TDM"
    tdm_path.mkdir(parents=True, exist_ok=True)
    (tdm_path / "index.html").write_text(html_prettify, encoding="utf-8")
    log("TDM/index.html généré avec succès")
    log("=== FIN GÉNÉRATION TDM ===")

if __name__ == "__main__":
    generer_tdm()

# fin du "cree_table_des_matieres.py" version "6.29"
