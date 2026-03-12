# structure_utils.py — Version 2.0
# Gestion STRUCTURE.py avec support templates {{variable}}

from pathlib import Path
import json
import re
from typing import Dict, Any, List

def resoudre_templates_runtime(item: dict, variables: dict) -> dict:
    """Résout les templates {{variable}} à l'exécution.
    
    Supporte templates imbriqués:
    - nom_affiché = "{{nom_document_sans_ext}}"
    - nom_TDM = "{{nom_affiché}}" → Résolu récursivement
    
    Syntaxe supportée:
    - {{nom_document}} : Nom complet avec extension
    - {{nom_document_sans_ext}} : Nom sans extension
    - {{titre_dossier}} : Titre du dossier
    - {{nom_affiché}} : Valeur de nom_affiché (récursif)
    - {{nom_TDM}} : Valeur de nom_TDM (récursif)
    - {{nom_navigation}} : Valeur de nom_navigation (récursif)
    
    Args:
        item: Élément avec possibles templates
        variables: Dict des variables disponibles
        
    Returns:
        Élément avec templates résolus (copie)
    """
    resolved = item.copy()
    
    # Variables de base
    nom_document = variables.get("nom_document", "")
    nom_sans_ext = Path(nom_document).stem if nom_document else ""
    titre_dossier = variables.get("titre_dossier", "")
    
    vars_disponibles = {
        "nom_document": nom_document,
        "nom_document_sans_ext": nom_sans_ext,
        "titre_dossier": titre_dossier
    }
    
    # Résoudre chaque champ (plusieurs passes pour templates imbriqués)
    champs = ["nom_affiché", "nom_TDM", "nom_navigation", "titre_table"]
    max_passes = 5  # Protection contre boucles infinies
    
    for passe in range(max_passes):
        changed = False
        
        for champ in champs:
            if champ not in resolved:
                continue
            
            valeur = resolved[champ]
            
            if not isinstance(valeur, str):
                continue
            
            # Ajouter valeurs déjà résolues aux variables disponibles
            vars_etendues = vars_disponibles.copy()
            for c in champs:
                if c in resolved and isinstance(resolved[c], str):
                    vars_etendues[c] = resolved[c]
            
            # Remplacer tous les templates {{var}}
            nouvelle_valeur = valeur
            for var_name, var_value in vars_etendues.items():
                pattern = f"{{{{{var_name}}}}}"
                if pattern in nouvelle_valeur:
                    nouvelle_valeur = nouvelle_valeur.replace(pattern, var_value)
                    changed = True
            
            resolved[champ] = nouvelle_valeur
        
        # Si aucun changement, on a fini
        if not changed:
            break
    
    return resolved

def charger_structure(dossier: Path) -> Dict[str, Any]:
    """Charge STRUCTURE.py d'un dossier."""
    fichier = dossier / "STRUCTURE.py"
    if not fichier.exists():
        return {"dossiers": [], "fichiers": []}
    
    try:
        from importlib.machinery import SourceFileLoader
        module = SourceFileLoader("STRUCTURE", str(fichier)).load_module()
        return module.STRUCTURE
    except Exception as e:
        print(f"Erreur lecture STRUCTURE.py dans {dossier}: {e}")
        return {"dossiers": [], "fichiers": []}

def ajouter_defaults_structure(structure: dict, dossier: Path, titre_site: str) -> dict:
    """Ajoute valeurs par défaut manquantes."""
    from pathlib import Path as PathLib
    
    # Titre par défaut
    is_root = str(dossier) == str(PathLib(dossier.parts[0]) if dossier.parts else dossier)
    titre_defaut = titre_site if is_root else dossier.name
    
    defaults = {
        "titre_dossier": titre_defaut,
        "titre_table": "{{titre_dossier}}",  # Template par défaut
        "entete_general": True,
        "pied_general": True,
        "entete": True,
        "pied": True,
        "navigation": True,
        "haut_page": True,
        "bas_page": True,
        "ajout_affichage": True,
    }
    
    modified = False
    for key, value in defaults.items():
        if key not in structure:
            structure[key] = value
            modified = True
    
    return structure

def filtrer_elements_existants(dossier: Path, elements: List[dict], log_func) -> List[dict]:
    """Filtre éléments dont fichier/dossier n'existe pas."""
    filtres = []
    for elem in elements:
        chemin = dossier / elem.get("nom_document", "")
        if chemin.exists():
            filtres.append(elem)
        else:
            log_func(f"Élément ignoré (inexistant): {elem.get('nom_document', '?')}")
    return filtres

def calculer_position_suivante(structure: dict) -> int:
    """Calcule prochaine position disponible."""
    all_items = structure.get("dossiers", []) + structure.get("fichiers", [])
    positions = [item.get("position", 0) for item in all_items]
    return max(positions, default=0) + 1

def element_existe(structure: dict, nom_document: str, categorie: str) -> bool:
    """Vérifie si élément existe dans catégorie."""
    return any(
        item["nom_document"] == nom_document 
        for item in structure.get(categorie, [])
    )

def ajouter_element_structure(structure: dict, nom_document: str, nom_html: str, 
                              categorie: str, position: int, log_func) -> None:
    """Ajoute nouvel élément à structure."""
    element = {
        "nom_document": nom_document,
        "nom_html": nom_html,
        "nom_affiché": "{{nom_document_sans_ext}}",  # Template
        "nom_TDM": "{{nom_document_sans_ext}}",
        "ajout_affichage": True,
        "affiché_index": True,
        "affiché_TDM": True,
        "position": position
    }
    
    if categorie == "dossiers":
        element["nom_navigation"] = "{{nom_document}}"
    
    structure.setdefault(categorie, []).append(element)
    log_func(f"Nouvel élément ajouté: {nom_document}")

def sauvegarder_structure(dossier: Path, structure: dict) -> None:
    """Sauvegarde structure dans STRUCTURE.py.
    
    IMPORTANT: Préserve les templates {{var}} tels quels.
    """
    # Trier par position
    if "dossiers" in structure:
        structure["dossiers"].sort(key=lambda x: x.get("position", 9999))
    if "fichiers" in structure:
        structure["fichiers"].sort(key=lambda x: x.get("position", 9999))
    
    # Générer contenu
    contenu = "# STRUCTURE.py – Généré automatiquement\n"
    contenu += "# Templates {{variable}} résolus à l'exécution\n\n"
    
    json_str = json.dumps(structure, ensure_ascii=False, indent=4)
    json_str = json_str.replace("true", "True").replace("false", "False")
    
    contenu += f"STRUCTURE = {json_str}\n"
    
    # Sauvegarder
    fichier = dossier / "STRUCTURE.py"
    fichier.write_text(contenu, encoding="utf-8")

# Fin structure_utils.py v2.0
