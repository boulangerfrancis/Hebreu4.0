# genere_site.py — Version 25.2

version = ("genere_site.py", "25.2")

"""
Générateur de site statique - Version 25.2

NOUVEAUTÉS v25.2:
- PHASE 4 : musique.py appelé APRES copier_fichiers_site()
  Les PDF avec bouton YouTube ecrasent les copies sans bouton.

NOUVEAUTÉS v25.1:
- (voir historique)

NOUVEAUTÉS v24.0:
- Fichiers commentaires (__*) ignorés sauf partitions
- Partitions musicales avec boutons YouTube
- Lecteur musical /musique/index.html
- Regénération forcée via lancer.cmd regenere_tout
- Filtrage intelligent fichiers sources

Workflow v25.2:
Pour chaque dossier dans DOCUMENTS:
  1. Générer PDF manquants (DOCX→PDF)
  2. Traiter partitions (__partition_*.pdf → avec boutons)
  3. Scanner dossier et mettre à jour STRUCTURE.py
  4. Générer index.html

Ensuite:
  5. Copier fichiers vers HTML
  6. PHASE 4 : musique.py -> boutons YouTube sur PDF (ecrase copies sans bouton)
  7. Générer page lecteur musical
"""

import os
import shutil
import unicodedata
import tempfile
import psutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup

# Import module conversion PDF
try:
    from conversion_pdf import convertir_docx_vers_pdf, HAS_PDFCREATOR
    DOCX2PDF_DISPONIBLE = HAS_PDFCREATOR
except ImportError:
    DOCX2PDF_DISPONIBLE = False
    HAS_PDFCREATOR = False
    print("AVERTISSEMENT : conversion_pdf.py non trouvé")

# Import configuration et modules
from lib1.options import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH
from lib1.config import CONFIG
from lib1 import html_utils as html
from lib1 import structure_utils as struct
from lib1 import pdf_utils as pdf
from lib1 import fichier_utils as fichiers  # v24.0
from lib1 import partition_utils as partitions  # v24.0
import musique as _musique                        # v25.2 : boutons YouTube phase 4

print(f"[Version] {version[0]} — {version[1]}")

# ============================================================================
# CONSTANTES
# ============================================================================

IGNORER = set(CONFIG.get("ignorer", [])) | {"__pycache__", ".pyc", "STRUCTURE.py", r"~\$"}
FICHIERS_ENTETE_PIED = {"entete.html", "entete_general.html", "pied.html", "pied_general.html"}
EXTENSIONS_ACCEPTEES = set(CONFIG.get("extensions_acceptees", ["pdf", "html", "htm", "txt"]))
EXTENSIONS_COPIABLES = {"pdf", "html", "htm", "jpg", "jpeg", "png", "gif", "css", "js"}
DOSSIER_TDM = CONFIG.get("dossier_tdm", "TDM")
AJOUT_AFFICHAGE = CONFIG.get("ajout_affichage", ["", "", "", ""])
VOIR_STRUCTURE = CONFIG.get("voir_structure", False)
LIEN_SOULIGNÉ = CONFIG.get("lien_souligné_index", False)

log_file = Path("generation.log")
log_file.write_text(
    f"--- GÉNÉRATION v{version[1]} — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ---\n",
    encoding="utf-8"
)

# ============================================================================
# UTILITAIRES
# ============================================================================

def log(msg: str) -> None:
    """Log console + fichier."""
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def normaliser_nom(nom: str) -> str:
    """Normalise nom pour URL."""
    nom = unicodedata.normalize('NFD', nom)
    nom = ''.join(c for c in nom if unicodedata.category(c) != 'Mn')
    nom = nom.replace("'", "_").replace("'", "_")
    nom = nom.replace(" ", "_")
    return nom.lower()

def get_word_processes() -> List[Any]:
    """Retourne processus Word actifs."""
    return [
        proc for proc in psutil.process_iter(['pid', 'name'])
        if proc.info['name'] and proc.info['name'].upper() == 'WINWORD.EXE'
    ]

def kill_word_processes(processes: List[Any]) -> None:
    """Ferme processus Word."""
    for proc in processes:
        print(".", end=" ")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except:
                pass
    print(" !")

def fichier_docx_existe(fichier_pdf: Path, dossier: Path) -> bool:
    """Vérifie si DOCX correspondant au PDF existe."""
    stem = fichier_pdf.stem
    
    for f in dossier.iterdir():
        if f.suffix.lower() in ['.doc', '.docx']:
            docx_stem_norm = normaliser_nom(f.stem)
            pdf_stem_norm = normaliser_nom(stem)
            
            if docx_stem_norm == pdf_stem_norm:
                return True
    
    return False

# ============================================================================
# TEMPLATES ET NAVIGATION
# ============================================================================

def charger_fichier_html_avec_fallback(dossier: Path, fichier: str, 
                                       position: str = "", commun: str = "") -> str:
    """Charge fichier HTML avec templates {{BASE_PATH}} interprétés."""
    local = dossier / fichier
    
    if local.exists():
        return html.charger_template_html(
            local,
            {"BASE_PATH": BASE_PATH},
            VOIR_STRUCTURE,
            position,
            commun
        )
    
    if fichier in ("entete_general.html", "pied_general.html"):
        racine = Path(DOSSIER_DOCUMENTS) / fichier
        if racine.exists():
            return html.charger_template_html(
                racine,
                {"BASE_PATH": BASE_PATH},
                VOIR_STRUCTURE,
                position,
                commun
            )
    
    return ""

def trouver_nom_navigation(parent_dossier: Path, nom_dossier: str) -> str:
    """Retourne nom_navigation depuis STRUCTURE.py parent."""
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

def generer_navigation_ariane(chemin_relatif: List[str], dossier_documents: Path) -> str:
    """Génère navigation fil d'Ariane."""
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
    
    nav_html += f'</div></nav>'
    
    if VOIR_STRUCTURE:
        nav_html = f'<div><!-- début navigation -->{nav_html}<!-- fin navigation --></div>'
    
    return nav_html

# ============================================================================
# TRAITEMENT DOSSIERS - STRUCTURE.py
# ============================================================================

def generer_pdf_manquants(dossier: Path) -> None:
    """Génère PDF manquants depuis DOCX + traite partitions musicales.
    
    v24.0: Ajout traitement partitions avec boutons YouTube.
    Phase 1 : DOCX→PDF
    Phase 2 : Partitions avec boutons
    """
    if not DOCX2PDF_DISPONIBLE:
        return
    
    fichiers_dir = list(dossier.iterdir())
    log(f"Vérification PDF manquants : {dossier}")
    
    # PHASE 1 : Conversions DOCX→PDF normales
    nb_conv = pdf.traiter_conversions_dossier(
        dossier,
        fichiers_dir,
        normaliser_nom,
        convertir_docx_vers_pdf,
        CONFIG,
        log
    )
    
    if nb_conv > 0:
        log(f"{nb_conv} PDF généré(s)")
    
    # === v24.0 : PHASE 2 - Partitions musicales ===
    if not partitions.HAS_PDF_LIBS:
        return
    
    # Chercher __correspondance.csv
    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return  # Pas de partitions dans ce dossier
    
    log(f"Traitement partitions : {dossier}")
    
    # Charger correspondances
    correspondances = partitions.charger_correspondances(csv_path)
    if not correspondances:
        log("  Aucune correspondance trouvée")
        return
    
    # Player URL
    player_url = CONFIG.get("player_url", f"{BASE_PATH}/musique/index.html")
    
    nb_partitions = 0
    
    # Traiter chaque partition
    for nom_pdf_final, video_id in correspondances.items():
        # Chercher PDF source (avec __partition_)
        pdf_source = None
        
        for f in dossier.iterdir():
            if f.name.startswith("__partition_") and f.suffix == ".pdf":
                # Vérifier si correspond au nom final
                nom_attendu = fichiers.nom_partition_final(f.name.replace(".pdf", ".docx"))
                if normaliser_nom(nom_attendu) == nom_pdf_final:
                    pdf_source = f
                    break
        
        if not pdf_source:
            log(f"  ⚠ PDF source partition introuvable : {nom_pdf_final}")
            continue
        
        # PDF final (sans __partition_)
        pdf_final = dossier / nom_pdf_final
        
        # Vérifier si regénération nécessaire
        if not partitions.doit_regenerer_partition(pdf_source, pdf_final):
            continue
        
        # Ajouter boutons
        log(f"  Partition : {nom_pdf_final} (YouTube: {video_id})")
        success = partitions.ajouter_boutons_partition(
            pdf_source,
            pdf_final,
            player_url,
            video_id
        )
        
        if success:
            nb_partitions += 1
    
    if nb_partitions > 0:
        log(f"{nb_partitions} partition(s) traitée(s)")

def mettre_a_jour_structure(dossier: Path) -> Dict[str, Any]:
    """Met à jour STRUCTURE.py d'un dossier.
    
    v23.4: Appelé APRÈS génération PDF, scanne les fichiers
    réellement présents dans DOCUMENTS.
    """
    log(f"Mise à jour STRUCTURE.py : {dossier}")
    
    # Charger structure existante
    structure = struct.charger_structure(dossier)
    structure = struct.ajouter_defaults_structure(
        structure,
        dossier,
        CONFIG.get("titre_site", "Site")
    )
    
    # Scanner nouveaux éléments
    modified = False
    position_suivante = struct.calculer_position_suivante(structure)
    
    entries = sorted(list(dossier.iterdir()), key=lambda x: x.name.lower())
    
    for entry in entries:
        # === v24.0 : Filtrage fichiers commentaires ===
        if fichiers.doit_filtrer_fichier(entry.name):
            continue  # Ignorer fichiers __* (commentaires)
        
        if entry.name in IGNORER or entry.name in FICHIERS_ENTETE_PIED:
            continue
        
        if entry.is_file() and entry.suffix.lower() == ".py":
            continue
        
        # Dossiers
        if entry.is_dir():
            if not struct.element_existe(structure, entry.name, "dossiers"):
                struct.ajouter_element_structure(
                    structure,
                    entry.name,
                    normaliser_nom(entry.name),
                    "dossiers",
                    position_suivante,
                    log
                )
                position_suivante += 1
                modified = True
        
        # Fichiers
        elif entry.is_file():
            ext = entry.suffix.lower().lstrip(".")
            
            # v23.4: Traiter DOCX spécialement
            if ext in ("doc", "docx"):
                # Vérifier si déjà dans STRUCTURE
                if not struct.element_existe(structure, entry.name, "fichiers"):
                    # Ajouter avec nom_html = PDF correspondant
                    nom_pdf_normalise = normaliser_nom(entry.stem + ".pdf")
                    
                    element = {
                        "nom_document": entry.name,
                        "nom_html": nom_pdf_normalise,
                        "nom_affiché": "{{nom_document_sans_ext}}",
                        "nom_TDM": "{{nom_document_sans_ext}}",
                        "ajout_affichage": True,
                        "affiché_index": True,
                        "affiché_TDM": True,
                        "position": position_suivante
                    }
                    
                    structure.setdefault("fichiers", []).append(element)
                    position_suivante += 1
                    modified = True
                    log(f"  Ajouté DOCX : {entry.name} → {nom_pdf_normalise}")
                
                continue  # Ne pas traiter dans EXTENSIONS_ACCEPTEES
            
            # v23.4: Ignorer PDF si DOCX existe
            if ext == "pdf":
                if fichier_docx_existe(entry, dossier):
                    log(f"  PDF ignoré : {entry.name} (dérivé de DOCX)")
                    continue
            
            if ext in EXTENSIONS_ACCEPTEES:
                if not struct.element_existe(structure, entry.name, "fichiers"):
                    struct.ajouter_element_structure(
                        structure,
                        entry.name,
                        normaliser_nom(entry.name),
                        "fichiers",
                        position_suivante,
                        log
                    )
                    position_suivante += 1
                    modified = True
                    log(f"  Ajouté : {entry.name}")
    
    # Sauvegarder si modifié
    if modified:
        struct.sauvegarder_structure(dossier, structure)
        log(f"✓ STRUCTURE.py mis à jour")
    else:
        log(f"✓ STRUCTURE.py inchangé")
    
    return structure

# ============================================================================
# GÉNÉRATION PAGES HTML
# ============================================================================

def generer_page_index(dossier_documents: Path) -> None:
    """Génère index.html pour un dossier.
    
    v23.4: Assume que STRUCTURE.py est déjà à jour.
    """
    log(f"Génération index.html : {dossier_documents}")
    
    # Charger structure (déjà à jour)
    structure = struct.charger_structure(dossier_documents)
    
    rel_path = dossier_documents.relative_to(DOSSIER_DOCUMENTS)
    
    # Préparer éléments
    elements = []
    
    for item in structure.get("dossiers", []):
        variables = {
            "nom_document": item["nom_document"],
            "titre_dossier": structure.get("titre_dossier", "")
        }
        resolved = struct.resoudre_templates_runtime(item, variables)
        resolved["genre"] = "dossier"
        elements.append(resolved)
    
    for item in structure.get("fichiers", []):
        variables = {
            "nom_document": item["nom_document"],
            "titre_dossier": structure.get("titre_dossier", "")
        }
        resolved = struct.resoudre_templates_runtime(item, variables)
        resolved["genre"] = "fichier"
        elements.append(resolved)
    
    elements.sort(key=lambda x: x.get("position", 9999))
    elements = struct.filtrer_elements_existants(dossier_documents, elements, log)
    
    # Assemblage HTML
    html_parts = []
    
    titre = structure.get("titre_dossier", dossier_documents.name)
    html_parts.append(html.generer_debut_html(titre, BASE_PATH))
    
    if structure.get("haut_page", False):
        contenu = "".join(CONFIG.get("haut_page", []))
        if contenu:
            html_parts.append(contenu)
    
    if structure.get("entete_general", False):
        html_parts.append(
            charger_fichier_html_avec_fallback(dossier_documents, "entete_general.html", "début", "_général")
        )
    
    if structure.get("navigation", False):
        nav = generer_navigation_ariane(list(rel_path.parts), Path(DOSSIER_DOCUMENTS))
        if nav:
            html_parts.append(nav)
    
    if structure.get("entete", False):
        html_parts.append(
            charger_fichier_html_avec_fallback(dossier_documents, "entete.html", "début", "")
        )
    
    titre_table = structure.get("titre_table", "{{titre_dossier}}")
    if "{{" in titre_table:
        titre_table = titre_table.replace("{{titre_dossier}}", titre)
    
    if titre_table:
        html_parts.append(html.generer_titre_table(titre_table))
    
    html_parts.append(
        html.generer_table_index(elements, AJOUT_AFFICHAGE, LIEN_SOULIGNÉ)
    )
    
    if structure.get("pied", False):
        html_parts.append(
            charger_fichier_html_avec_fallback(dossier_documents, "pied.html", "fin", "")
        )
    
    if structure.get("pied_general", False):
        html_parts.append(
            charger_fichier_html_avec_fallback(dossier_documents, "pied_general.html", "fin", "_général")
        )
    
    if structure.get("bas_page", False):
        contenu = "".join(CONFIG.get("bas_page", []))
        if contenu:
            html_parts.append(contenu)
    
    html_parts.append(html.generer_fin_html(version[1]))
    
    # Sauvegarde dans HTML
    html_brut = "".join(html_parts)
    html_final = BeautifulSoup(html_brut, 'html.parser').prettify()
    
    cible_rel_norm = Path(*(normaliser_nom(part) for part in rel_path.parts))
    cible = Path(DOSSIER_HTML) / cible_rel_norm
    cible.mkdir(parents=True, exist_ok=True)
    
    (cible / "index.html").write_text(html_final, encoding="utf-8")
    log(f"✓ index.html généré")

# ============================================================================
# COPIE FICHIERS
# ============================================================================

def copier_fichiers_site() -> None:
    """Copie fichiers DOCUMENTS → HTML.
    
    v24.0: Filtre fichiers commentaires (__*).
    """
    log("Copie fichiers vers HTML")
    
    for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
        # v24.0 : Ignorer dossiers commentaires
        dirs[:] = [d for d in dirs if not d.startswith("__") and d not in IGNORER]
        
        rel_path = Path(racine).relative_to(DOSSIER_DOCUMENTS)
        cible_rel_norm = Path(*(normaliser_nom(part) for part in rel_path.parts))
        cible = Path(DOSSIER_HTML) / cible_rel_norm
        cible.mkdir(parents=True, exist_ok=True)
        
        for fichier in files:
            # v24.0 : Filtrer fichiers commentaires
            if fichiers.doit_filtrer_fichier(fichier):
                continue
            
            src_file = Path(racine) / fichier
            if pdf.est_fichier_copiable(src_file, EXTENSIONS_COPIABLES):
                dst_file = cible / normaliser_nom(fichier)
                shutil.copy2(src_file, dst_file)

# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Génération complète - WORKFLOW v24.0."""
    log("=" * 70)
    log("=== GÉNÉRATION SITE STATIQUE v24.0 ===")
    log("=" * 70)
    
    log(f"Source : {DOSSIER_DOCUMENTS}")
    log(f"HTML : {DOSSIER_HTML}")
    log(f"BASE_PATH : {BASE_PATH}")
    log("")
    
    # Config
    if DOCX2PDF_DISPONIBLE and HAS_PDFCREATOR:
        log("✓ Conversion PDF disponible (PDFCreator)")
    else:
        log("✗ Conversion PDF désactivée (PDFCreator manquant)")
    
    # v24.0 : Modules partitions
    if partitions.HAS_PDF_LIBS:
        log("✓ Modules partitions disponibles (pypdf + reportlab)")
    else:
        log("✗ Modules partitions manquants (pip install pypdf reportlab)")
    log("")
    
    # Créer dossier HTML et copier style.css
    if Path(DOSSIER_HTML).exists():
        shutil.rmtree(DOSSIER_HTML)
    Path(DOSSIER_HTML).mkdir(parents=True, exist_ok=True)
    
    style_src = Path(__file__).parent / "lib1" / "style.css"
    if style_src.exists():
        shutil.copy2(style_src, Path(DOSSIER_HTML) / "style.css")
    
    tdm_path = Path(DOSSIER_HTML) / DOSSIER_TDM
    tdm_path.mkdir(parents=True, exist_ok=True)
    
    log("=" * 70)
    log("PHASE 1 : GÉNÉRATION PDF + PARTITIONS + STRUCTURE.py")
    log("=" * 70)
    log("")
    
    # PHASE 1 : Pour chaque dossier, générer PDF et mettre à jour STRUCTURE
    for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
        # v24.0 : Ignorer dossiers commentaires
        dirs[:] = [d for d in dirs if not d.startswith("__") and d not in IGNORER]
        dossier = Path(racine)
        
        log(f"--- {dossier} ---")
        generer_pdf_manquants(dossier)
        mettre_a_jour_structure(dossier)
        log("")
    
    log("=" * 70)
    log("PHASE 2 : GÉNÉRATION index.html")
    log("=" * 70)
    log("")
    
    # PHASE 2 : Générer tous les index.html
    for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
        dirs[:] = [d for d in dirs if d not in IGNORER]
        generer_page_index(Path(racine))
        log("")
    
    log("=" * 70)
    log("PHASE 3 : COPIE FICHIERS VERS HTML")
    log("=" * 70)
    log("")
    
    # PHASE 3 : Copier fichiers
    copier_fichiers_site()

    log("=" * 70)
    log("PHASE 4 : BOUTONS YOUTUBE SUR PARTITIONS PDF")
    log("=" * 70)
    log("")

    # PHASE 4 : Pour chaque dossier ayant un __correspondance.csv,
    # appeler musique.traiter_partitions_du_dossier().
    # S'execute APRES copier_fichiers_site() pour ecraser les copies sans bouton.
    nb_total_partitions = 0
    for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
        dirs[:] = [d for d in dirs if not d.startswith("__") and d not in IGNORER]
        dossier = Path(racine)
        if (dossier / "__correspondance.csv").exists():
            log(f"--- Partitions : {dossier} ---")
            nb = _musique.traiter_partitions_du_dossier(dossier, log)
            nb_total_partitions += nb
            log("")
    if nb_total_partitions == 0:
        log("  Aucune partition traitee (pas de __correspondance.csv)")
    log("")
    
    # Nettoyage
    processes = get_word_processes()
    if processes:
        log("")
        log("Fermeture Word")
        kill_word_processes(processes)
    
    log("")
    log("=" * 70)
    log("=== FIN GÉNÉRATION ===")
    log("=" * 70)

if __name__ == "__main__":
    main()

# Fin genere_site.py v24.0
