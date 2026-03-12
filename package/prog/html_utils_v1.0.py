# html_utils.py — Version 1.0
# Utilitaires pour génération HTML et interprétation templates

from pathlib import Path
from datetime import datetime
import re
from typing import List

def interpreter_template(contenu: str, variables: dict) -> str:
    """Interprète les variables {{VAR}} dans un template.
    
    Args:
        contenu: Contenu du template avec {{variables}}
        variables: Dict des variables à substituer
        
    Returns:
        Contenu avec variables remplacées
        
    Example:
        >>> interpreter_template("Lien: {{BASE_PATH}}/index.html", {"BASE_PATH": "/site"})
        'Lien: /site/index.html'
    """
    for var, valeur in variables.items():
        contenu = contenu.replace(f"{{{{{var}}}}}", str(valeur))
    return contenu

def charger_template_html(fichier: Path, variables: dict, voir_structure: bool = False, 
                          position: str = "", commun: str = "") -> str:
    """Charge un fichier HTML et interprète les variables.
    
    Args:
        fichier: Chemin du fichier template
        variables: Dict des variables (BASE_PATH, etc.)
        voir_structure: Ajouter commentaires de structure
        position: Pour commentaire (début/fin)
        commun: Pour commentaire (_général ou vide)
        
    Returns:
        HTML interprété
    """
    if not fichier.exists():
        return ""
    
    try:
        with open(fichier, "r", encoding="utf-8") as f:
            contenu = f.read()
        
        # Interpréter variables
        contenu = interpreter_template(contenu, variables)
        
        # Ajouter commentaires structure si demandé
        if voir_structure and position:
            contenu = f"<div><!-- {position}{commun} -->{contenu}<!-- fin {position}{commun} --></div>"
        
        return contenu
    except Exception as e:
        print(f"Erreur lecture {fichier}: {e}")
        return ""

def appliquer_mini_markdown(texte: str) -> str:
    """Applique le mini-markdown aux textes.
    
    Syntaxe supportée:
    - **texte** : gras
    - __texte__ : italique
    - --texte-- : souligné
    - ~~texte~~ : barré
    - [rouge]texte[/rouge] : couleur
    - [couleur:#ff0000]texte[/couleur] : couleur hex
    
    Args:
        texte: Texte avec mini-markdown
        
    Returns:
        HTML formaté
    """
    # Gras, italique, souligné, barré
    texte = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texte)
    texte = re.sub(r'__(.*?)__', r'<em>\1</em>', texte)
    texte = re.sub(r'--(.*?)--', r'<u>\1</u>', texte)
    texte = re.sub(r'~~(.*?)~~', r'<del>\1</del>', texte)
    
    # Couleurs nommées
    couleurs = {
        "rouge": "red", "bleu": "blue", "vert": "green", "jaune": "gold",
        "violet": "purple", "orange": "orange", "gris": "gray", "noir": "black"
    }
    for nom, code in couleurs.items():
        texte = texte.replace(f"[{nom}]", f'<span style="color:{code}">')
        texte = texte.replace(f"[/{nom}]", "</span>")
    
    # Couleurs hex/rgba
    texte = re.sub(
        r'\[couleur:(#[0-9a-fA-F]{6}|rgba?\([^)]+\))\]',
        lambda m: f'<span style="color:{m.group(1)}">',
        texte
    )
    texte = texte.replace("[/couleur]", "</span>")
    
    return texte

def echapper_accents_html(texte: str) -> str:
    """Échappe les caractères accentués en entités HTML sauf hébreu.
    
    Préserve: Hébreu (U+0590 à U+05FF)
    Convertit: Caractères accentués en &#code;
    
    Args:
        texte: Texte source
        
    Returns:
        Texte avec accents échappés
    """
    result = []
    for char in texte:
        code = ord(char)
        # Hébreu : préserver
        if 0x0590 <= code <= 0x05FF:
            result.append(char)
        # Accents : échapper
        elif code > 127:
            result.append(f"&#{code};")
        else:
            result.append(char)
    return "".join(result)

def generer_debut_html(titre: str, base_path: str) -> str:
    """Génère le début d'un fichier HTML.
    
    Args:
        titre: Titre de la page
        base_path: Chemin de base pour les ressources
        
    Returns:
        HTML de début
    """
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8"/>
    <title>{echapper_accents_html(titre)}</title>
    <link href="{base_path}/style.css" rel="stylesheet"/>
</head>
<body>"""

def generer_fin_html(version: str = "23.1") -> str:
    """Génère la fin d'un fichier HTML avec timestamp.
    
    Args:
        version: Version du générateur
        
    Returns:
        HTML de fin
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""<!-- Généré le {timestamp} par genere_site.py v{version} -->
</body>
</html>"""

def generer_navigation(chemin_relatif: List[str], base_path: str, 
                       fonction_nom_nav, voir_structure: bool = False) -> str:
    """Génère la barre de navigation avec fil d'Ariane.
    
    Args:
        chemin_relatif: Liste des dossiers parents
        base_path: Chemin de base
        fonction_nom_nav: Fonction pour obtenir nom_navigation
        voir_structure: Ajouter commentaires
        
    Returns:
        HTML de navigation
    """
    nav = f'<nav class="navigation"><div class="gauche"><a href="{base_path}/index.html" class="monbouton">Accueil</a>'
    
    for i in range(len(chemin_relatif) - 1):
        nom_nav = fonction_nom_nav(i, chemin_relatif)
        lien = base_path + "/" + "/".join(chemin_relatif[:i+1])
        nav += f' → <a href="{lien}/index.html" class="monbouton">{appliquer_mini_markdown(nom_nav)}</a>'
    
    nav += f'</div><div class="droite"><a href="{base_path}/TDM/index.html" class="monbouton">Sommaire</a></div></nav>'
    
    if voir_structure:
        nav = f"<div><!-- début navigation -->{nav}<!-- fin navigation --></div>"
    
    return nav

def generer_titre_table(titre: str) -> str:
    """Génère le HTML du titre au-dessus de la table.
    
    Args:
        titre: Titre (avec mini-markdown possible)
        
    Returns:
        HTML du titre
    """
    titre_html = appliquer_mini_markdown(titre)
    titre_html = echapper_accents_html(titre_html)
    return f'<div class="titre-table">{titre_html}</div>'

def generer_table_index(liste_fils: List[dict], ajout_affichage: list, 
                       lien_souligné: bool = False) -> str:
    """Génère le HTML de la table d'index.
    
    Args:
        liste_fils: Liste des éléments à afficher
        ajout_affichage: Préfixes/suffixes [dossier_pre, dossier_suf, fichier_pre, fichier_suf]
        lien_souligné: Souligner les liens
        
    Returns:
        HTML de la table
    """
    style_a = '' if lien_souligné else 'text-decoration: none;'
    lignes = []
    
    for fils in liste_fils:
        if not fils.get("affiché_index", True):
            continue
        
        nom_affiché = fils.get("nom_affiché", fils.get("nom_document", ""))
        nom_html = appliquer_mini_markdown(nom_affiché)
        nom_html = echapper_accents_html(nom_html)
        
        if fils.get("genre") == "dossier":
            if fils.get("ajout_affichage", True):
                nom_html = f"{ajout_affichage[0]}{nom_html}{ajout_affichage[1]}"
            lignes.append(f'<a class="dossier-item" style="{style_a}" href="{fils["nom_html"]}/index.html">{nom_html}</a><br>')
        else:
            if fils.get("ajout_affichage", True):
                nom_html = f"{ajout_affichage[2]}{nom_html}{ajout_affichage[3]}"
            lignes.append(f'<a class="dossier-item" style="{style_a}" href="{fils["nom_html"]}">{nom_html}</a><br>')
    
    contenu = "".join(lignes)
    return f'<div class="table-container"><table class="dossiers"><tbody><tr><td>{contenu}</td></tr></tbody></table></div>'

# Fin html_utils.py v1.0
