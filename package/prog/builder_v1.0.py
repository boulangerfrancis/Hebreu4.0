# builder.py — Version 1.0
# Module "BUILDER" : génération HTML et copie fichiers
#
# Extrait de genere_site.py v24.0 → refactorisation v25.0
# Contient :
#   - generer_page_index() : génération index.html de chaque dossier
#   - copier_fichiers_site() : copie DOCUMENTS → HTML
#   - Helpers navigation, templates HTML

version = ("builder.py", "1.0")
print(f"[Import] {version[0]} - Version {version[1]} chargé")

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG
from lib1 import html_utils as html
from lib1 import structure_utils as struct
from lib1 import pdf_utils as pdf
from lib1 import fichier_utils as fichiers
from documents import normaliser_nom

# Constantes issues de CONFIG
IGNORER = set(CONFIG.get("ignorer", [])) | {"__pycache__", "STRUCTURE.py"}
AJOUT_AFFICHAGE = CONFIG.get("ajout_affichage", ["", "", "", ""])
VOIR_STRUCTURE = CONFIG.get("voir_structure", False)
LIEN_SOULIGNÉ = CONFIG.get("lien_souligné_index", False)
EXTENSIONS_COPIABLES = {"pdf", "html", "htm", "jpg", "jpeg", "png", "gif", "css", "js"}
FICHIERS_ENTETE_PIED = {"entete.html", "entete_general.html", "pied.html", "pied_general.html"}


# ============================================================================
# HELPERS TEMPLATES HTML
# ============================================================================

def charger_html_avec_fallback(dossier: Path, fichier: str,
                               position: str = "", commun: str = "") -> str:
    """Charge un fichier HTML local ou depuis la racine documents.

    Interprète les variables {{BASE_PATH}}.

    Args:
        dossier: Dossier local à chercher en premier
        fichier: Nom du fichier (ex: entete.html)
        position: Pour commentaire debug (début/fin)
        commun: Pour commentaire debug (_général ou vide)

    Returns:
        Contenu HTML interprété, ou chaîne vide
    """
    local = dossier / fichier
    if local.exists():
        return html.charger_template_html(
            local, {"BASE_PATH": BASE_PATH},
            VOIR_STRUCTURE, position, commun
        )

    if fichier in ("entete_general.html", "pied_general.html"):
        racine_fichier = Path(DOSSIER_DOCUMENTS) / fichier
        if racine_fichier.exists():
            return html.charger_template_html(
                racine_fichier, {"BASE_PATH": BASE_PATH},
                VOIR_STRUCTURE, position, commun
            )

    return ""


# ============================================================================
# NAVIGATION FIL D'ARIANE
# ============================================================================

def trouver_nom_navigation(parent_dossier: Path, nom_dossier: str) -> str:
    """Retourne le nom_navigation d'un dossier depuis le STRUCTURE.py parent.

    Args:
        parent_dossier: Dossier contenant STRUCTURE.py
        nom_dossier: Nom du sous-dossier cherché

    Returns:
        nom_navigation résolu (ou nom_dossier par défaut)
    """
    structure = struct.charger_structure(parent_dossier)
    for item in structure.get("dossiers", []):
        if item["nom_document"] == nom_dossier:
            variables = {
                "nom_document": item["nom_document"],
                "titre_dossier": structure.get("titre_dossier", "")
            }
            resolved = struct.resoudre_templates_runtime(item, variables)
            return resolved.get("nom_navigation", nom_dossier)
    return nom_dossier


def generer_navigation_ariane(chemin_relatif: List[str],
                               dossier_documents: Path) -> str:
    """Génère la barre de navigation fil d'Ariane.

    N'affiche rien si on est à la racine (pas de parent).

    Args:
        chemin_relatif: Liste des parties du chemin depuis DOCUMENTS
        dossier_documents: Racine des sources

    Returns:
        HTML de la barre de navigation, ou chaîne vide
    """
    if len(chemin_relatif) <= 1:
        return ""

    nav_html = f'<nav class="navigation"><div class="gauche">'
    current_parent = dossier_documents

    for i in range(len(chemin_relatif) - 1):
        nom_dossier = chemin_relatif[i]
        nom_nav = trouver_nom_navigation(current_parent, nom_dossier)
        lien_parts = [normaliser_nom(p) for p in chemin_relatif[:i+1]]
        lien = BASE_PATH + "/" + "/".join(lien_parts)
        nom_nav_html = html.appliquer_mini_markdown(nom_nav)

        if i > 0:
            nav_html += ' → '
        nav_html += f'<a href="{lien}/index.html" class="monbouton">{nom_nav_html}</a>'
        current_parent = current_parent / nom_dossier

    nav_html += f'</div><div class="droite">'
    nav_html += f'<a href="{BASE_PATH}/TDM/index.html" class="monbouton">Sommaire</a>'
    nav_html += f'</div></nav>'

    if VOIR_STRUCTURE:
        nav_html = f'<div><!-- début navigation -->{nav_html}<!-- fin navigation --></div>'

    return nav_html


# ============================================================================
# GÉNÉRATION index.html
# ============================================================================

def generer_page_index(dossier_documents: Path, version_generateur: str,
                       log_func) -> None:
    """Génère le fichier index.html d'un dossier.

    Lit STRUCTURE.py (déjà à jour), assemble les parties HTML
    et écrit dans le dossier HTML correspondant.

    Args:
        dossier_documents: Dossier source (dans DOCUMENTS)
        version_generateur: Version string pour le commentaire HTML final
        log_func: Fonction de log
    """
    structure = struct.charger_structure(dossier_documents)
    rel_path = dossier_documents.relative_to(DOSSIER_DOCUMENTS)

    # Préparer éléments (dossiers + fichiers, triés par position)
    elements = []
    titre = structure.get("titre_dossier", dossier_documents.name)

    for item in structure.get("dossiers", []) + structure.get("fichiers", []):
        variables = {
            "nom_document": item["nom_document"],
            "titre_dossier": titre
        }
        resolved = struct.resoudre_templates_runtime(item, variables)
        resolved["genre"] = "dossier" if item in structure.get("dossiers", []) else "fichier"
        elements.append(resolved)

    # Recalculer le genre proprement (la boucle fusion ci-dessus peut mélanger)
    elements_dossiers = []
    for item in structure.get("dossiers", []):
        variables = {"nom_document": item["nom_document"], "titre_dossier": titre}
        resolved = struct.resoudre_templates_runtime(item, variables)
        resolved["genre"] = "dossier"
        elements_dossiers.append(resolved)

    elements_fichiers = []
    for item in structure.get("fichiers", []):
        variables = {"nom_document": item["nom_document"], "titre_dossier": titre}
        resolved = struct.resoudre_templates_runtime(item, variables)
        resolved["genre"] = "fichier"
        elements_fichiers.append(resolved)

    elements = sorted(elements_dossiers + elements_fichiers,
                      key=lambda x: x.get("position", 9999))
    elements = struct.filtrer_elements_existants(dossier_documents, elements, log_func)

    # Assemblage HTML
    html_parts = [html.generer_debut_html(titre, BASE_PATH)]

    # Haut page (global)
    if structure.get("haut_page", False):
        contenu = "".join(CONFIG.get("haut_page", []))
        if contenu:
            html_parts.append(contenu)

    # Entête général
    if structure.get("entete_general", False):
        html_parts.append(charger_html_avec_fallback(
            dossier_documents, "entete_general.html", "début", "_général"))

    # Navigation fil d'Ariane
    if structure.get("navigation", False):
        nav = generer_navigation_ariane(list(rel_path.parts), Path(DOSSIER_DOCUMENTS))
        if nav:
            html_parts.append(nav)

    # Entête local
    if structure.get("entete", False):
        html_parts.append(charger_html_avec_fallback(
            dossier_documents, "entete.html", "début", ""))

    # Titre au-dessus de la table
    titre_table = structure.get("titre_table", "{{titre_dossier}}")
    if "{{titre_dossier}}" in titre_table:
        titre_table = titre_table.replace("{{titre_dossier}}", titre)
    if titre_table:
        html_parts.append(html.generer_titre_table(titre_table))

    # Table des liens
    html_parts.append(html.generer_table_index(elements, AJOUT_AFFICHAGE, LIEN_SOULIGNÉ))

    # Pied local
    if structure.get("pied", False):
        html_parts.append(charger_html_avec_fallback(
            dossier_documents, "pied.html", "fin", ""))

    # Pied général
    if structure.get("pied_general", False):
        html_parts.append(charger_html_avec_fallback(
            dossier_documents, "pied_general.html", "fin", "_général"))

    # Bas page (global)
    if structure.get("bas_page", False):
        contenu = "".join(CONFIG.get("bas_page", []))
        if contenu:
            html_parts.append(contenu)

    html_parts.append(html.generer_fin_html(version_generateur))

    # Prettier + sauvegarde
    html_brut = "".join(html_parts)
    html_final = BeautifulSoup(html_brut, 'html.parser').prettify()

    # Chemin cible normalisé
    cible_rel_norm = Path(*(normaliser_nom(p) for p in rel_path.parts)) if rel_path.parts else Path(".")
    cible = Path(DOSSIER_HTML) / cible_rel_norm
    cible.mkdir(parents=True, exist_ok=True)
    (cible / "index.html").write_text(html_final, encoding="utf-8")
    log_func(f"  ✓ index.html → {cible}")


# ============================================================================
# COPIE FICHIERS DOCUMENTS → HTML
# ============================================================================

def copier_fichiers_site(log_func) -> None:
    """Copie les fichiers depuis DOCUMENTS vers HTML.

    Règles :
    - Dossiers commençant par "__" : ignorés
    - Fichiers commençant par "__" : ignorés (sauf __partition_* déjà traités)
    - DOCX/DOC : jamais copiés (représentés par leur PDF)
    - STRUCTURE.py, fichiers temporaires Word (~$) : ignorés

    Args:
        log_func: Fonction de log
    """
    log_func("Copie fichiers DOCUMENTS → HTML")

    for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
        # Ignorer dossiers "__*" et dossiers de la liste IGNORER
        dirs[:] = [d for d in dirs
                   if not d.startswith("__") and d not in IGNORER]

        rel_path = Path(racine).relative_to(DOSSIER_DOCUMENTS)

        # Chemin HTML cible (normalisé)
        if rel_path.parts:
            cible_rel_norm = Path(*(normaliser_nom(p) for p in rel_path.parts))
        else:
            cible_rel_norm = Path(".")
        cible = Path(DOSSIER_HTML) / cible_rel_norm
        cible.mkdir(parents=True, exist_ok=True)

        for fichier in files:
            # Filtres
            if fichiers.doit_filtrer_fichier(fichier):
                continue

            src = Path(racine) / fichier
            if pdf.est_fichier_copiable(src, EXTENSIONS_COPIABLES):
                dst = cible / normaliser_nom(fichier)
                shutil.copy2(src, dst)
                log_func(f"  → {dst.relative_to(DOSSIER_HTML)}")

    log_func("✓ Copie terminée")


# ============================================================================
# INITIALISATION DOSSIER HTML
# ============================================================================

def initialiser_dossier_html(style_source: Path, dossier_tdm: str,
                              log_func) -> None:
    """Prépare le dossier HTML de sortie (vide + style.css + TDM/).

    Args:
        style_source: Chemin du fichier style.css source
        dossier_tdm: Nom du sous-dossier TDM (ex: "TDM")
        log_func: Fonction de log
    """
    html_dir = Path(DOSSIER_HTML)

    if html_dir.exists():
        shutil.rmtree(html_dir)
        log_func(f"  Dossier HTML vidé : {html_dir}")

    html_dir.mkdir(parents=True, exist_ok=True)

    if style_source.exists():
        shutil.copy2(style_source, html_dir / "style.css")
        log_func(f"  style.css copié")
    else:
        log_func(f"  ⚠ style.css introuvable : {style_source}")

    (html_dir / dossier_tdm).mkdir(parents=True, exist_ok=True)
    log_func(f"  Dossier {dossier_tdm}/ créé")

# Fin builder.py v1.0
