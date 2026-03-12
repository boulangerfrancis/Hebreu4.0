# documents.py — Version 1.0
# Module "DOCUMENTS" : conversions PDF, partitions musicales, gestion STRUCTURE.py
#
# Extrait de genere_site.py v24.0 → refactorisation v25.0
# Contient :
#   - normaliser_nom()
#   - Règles de régénération PDF (corrigées v25.0)
#   - Nettoyage c:\temp après conversion
#   - Traitement partitions __partition_*.pdf → PDF avec boutons
#   - Mise à jour STRUCTURE.py

version = ("documents.py", "1.0")
print(f"[Import] {version[0]} - Version {version[1]} chargé")

import os
import sys
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Import configuration
from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG

# Import modules utilitaires
from lib1 import structure_utils as struct
from lib1 import fichier_utils as fichiers

# Import conversion PDF
try:
    from conversion_pdf import convertir_docx_vers_pdf, HAS_PDFCREATOR
    DOCX2PDF_DISPONIBLE = HAS_PDFCREATOR
except ImportError:
    DOCX2PDF_DISPONIBLE = False
    HAS_PDFCREATOR = False
    print("AVERTISSEMENT : conversion_pdf.py non trouvé")

# Import modules partitions
try:
    from lib1 import partition_utils as partitions
    HAS_PARTITION_LIBS = partitions.HAS_PDF_LIBS
except ImportError:
    HAS_PARTITION_LIBS = False
    partitions = None
    print("AVERTISSEMENT : partition_utils non disponible")

# Heure de début de session (pour règle régénération aujourd'hui)
SESSION_START_TIME = datetime.now()

# Fichiers entête/pied à ne pas inclure dans la structure
FICHIERS_ENTETE_PIED = {"entete.html", "entete_general.html", "pied.html", "pied_general.html"}
EXTENSIONS_ACCEPTEES = set(CONFIG.get("extensions_acceptees", ["pdf", "html", "htm", "txt"]))
IGNORER = set(CONFIG.get("ignorer", [])) | {"__pycache__", "STRUCTURE.py"}


# ============================================================================
# UTILITAIRES
# ============================================================================

def normaliser_nom(nom: str) -> str:
    """Normalise un nom de fichier pour URL.

    Transformations :
    - Minuscules
    - Suppression accents
    - Espaces et apostrophes → underscore

    Args:
        nom: Nom original (avec accents, espaces, etc.)

    Returns:
        Nom normalisé pour URL/fichier
    """
    nom = unicodedata.normalize('NFD', nom)
    nom = ''.join(c for c in nom if unicodedata.category(c) != 'Mn')
    nom = nom.replace("'", "_").replace("\u2019", "_")
    nom = nom.replace(" ", "_")
    return nom.lower()


def nettoyer_temp_pdf(nom_fichier: str, log_func) -> None:
    """Supprime le PDF résiduel dans c:\\temp après conversion.

    Word/PDFCreator laisse parfois des fichiers dans c:\\temp.
    Cette fonction les supprime proprement après déplacement réussi.

    Args:
        nom_fichier: Nom du fichier DOCX source (pour construire le nom PDF)
        log_func: Fonction de log
    """
    stem = Path(nom_fichier).stem
    pdf_temp = Path(r"c:\temp") / f"{stem}.pdf"

    if pdf_temp.exists():
        try:
            pdf_temp.unlink()
            log_func(f"  🗑 Résidu supprimé : {pdf_temp}")
        except Exception as e:
            log_func(f"  ⚠ Impossible de supprimer {pdf_temp} : {e}")


def nettoyer_tous_temp_pdf(log_func) -> None:
    """Nettoie TOUS les PDF résiduels dans c:\\temp au démarrage.

    Appelé en début de session pour repartir d'un état propre.

    Args:
        log_func: Fonction de log
    """
    temp_dir = Path(r"c:\temp")
    if not temp_dir.exists():
        return

    pdf_restes = list(temp_dir.glob("*.pdf"))
    if not pdf_restes:
        return

    log_func(f"Nettoyage c:\\temp ({len(pdf_restes)} PDF résiduels)...")
    for f in pdf_restes:
        try:
            f.unlink()
            log_func(f"  🗑 {f.name}")
        except Exception as e:
            log_func(f"  ⚠ {f.name} : {e}")


# ============================================================================
# RÈGLES DE RÉGÉNÉRATION PDF (v25.0 — corrigées)
# ============================================================================

def doit_supprimer_pdf_pour_regeneration(docx_path: Path, pdf_path: Path,
                                          log_func) -> Tuple[bool, str]:
    """Détermine si un PDF doit être supprimé (pour forcer la regénération).

    Règles (dans l'ordre de priorité) :

    A) CONFIG["regeneration"] == True
       → Supprimer si PDF présent ET DOCX source présent

    B) CONFIG["regenerer_pdf_aujourd_hui"] == True
       → Supprimer si le DOCX source a été modifié AUJOURD'HUI
         et que le PDF existe (pour le recréer avec les modifs du jour)

    C) CONFIG["regeneration"] == "JJ/MM/AAAA"
       → Supprimer si DOCX modifié après la date indiquée

    D) DOCX plus récent que PDF
       → Supprimer pour recréer

    Args:
        docx_path: Chemin du fichier DOCX source
        pdf_path: Chemin du fichier PDF cible
        log_func: Fonction de log

    Returns:
        (supprimer: bool, raison: str)
    """
    if not pdf_path.exists():
        return (False, "")  # Rien à supprimer, on créera directement

    config_regen = CONFIG.get("regeneration", False)
    config_aujourd_hui = CONFIG.get("regenerer_pdf_aujourd_hui", False)

    # A) Régénération totale forcée
    if config_regen is True:
        return (True, "Régénération forcée (CONFIG['regeneration']=True)")

    # B) DOCX modifié aujourd'hui → supprimer PDF pour recréer
    if config_aujourd_hui:
        docx_mtime = datetime.fromtimestamp(docx_path.stat().st_mtime)
        if docx_mtime.date() == datetime.now().date():
            # Sécurité : ne supprimer que si le PDF date d'AVANT cette session
            # (évite de supprimer un PDF qu'on vient juste de créer)
            pdf_mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime)
            if pdf_mtime < SESSION_START_TIME:
                return (True, "DOCX modifié aujourd'hui (CONFIG['regenerer_pdf_aujourd_hui']=True)")

    # C) Régénération à partir d'une date
    if isinstance(config_regen, str):
        try:
            date_limite = datetime.strptime(config_regen, "%d/%m/%Y")
            docx_mtime = datetime.fromtimestamp(docx_path.stat().st_mtime)
            if docx_mtime > date_limite:
                return (True, f"DOCX modifié après {config_regen}")
        except ValueError:
            log_func(f"  ⚠ Format date invalide dans CONFIG['regeneration'] : {config_regen}")

    # D) DOCX plus récent que PDF (comportement normal)
    if docx_path.stat().st_mtime > pdf_path.stat().st_mtime:
        return (True, "DOCX plus récent que le PDF")

    return (False, "")


def doit_creer_pdf(docx_path: Path, pdf_path: Path) -> bool:
    """Vérifie si le PDF doit être créé (inexistant).

    Args:
        docx_path: Chemin DOCX
        pdf_path: Chemin PDF cible

    Returns:
        True si PDF inexistant
    """
    return not pdf_path.exists()


# ============================================================================
# TRAITEMENT PDF : CONVERSIONS DOCX→PDF
# ============================================================================

def traiter_docx_du_dossier(dossier: Path, log_func) -> int:
    """Génère les PDF manquants ou obsolètes depuis les DOCX d'un dossier.

    Gère aussi les partitions (__partition_*.docx) si présentes.

    Workflow par fichier DOCX :
    1. Calculer nom PDF cible (normalisé)
    2. Vérifier si suppression nécessaire (règles CONFIG)
    3. Supprimer si nécessaire
    4. Créer si PDF absent
    5. Nettoyer c:\\temp après conversion

    Args:
        dossier: Dossier à traiter
        log_func: Fonction de log

    Returns:
        Nombre de conversions effectuées
    """
    if not DOCX2PDF_DISPONIBLE:
        return 0

    nb_conversions = 0

    try:
        entries = list(dossier.iterdir())
    except PermissionError:
        log_func(f"  ⚠ Accès refusé : {dossier}")
        return 0

    for entry in entries:
        if not entry.is_file():
            continue

        # Fichiers temporaires Word → ignorer
        if entry.name.startswith('~$'):
            continue

        # Seuls .doc et .docx sont convertis
        if entry.suffix.lower() not in ('.doc', '.docx'):
            continue

        # Les fichiers "__*" sont ignorés SAUF "__partition_*.docx"
        if entry.name.startswith("__") and not entry.name.startswith("__partition_"):
            continue

        # Nom du PDF cible (normalisé)
        nom_pdf = normaliser_nom(entry.stem) + ".pdf"
        pdf_path = dossier / nom_pdf

        # Étape 1 : Faut-il supprimer le PDF existant ?
        supprimer, raison = doit_supprimer_pdf_pour_regeneration(entry, pdf_path, log_func)
        if supprimer:
            log_func(f"  ✗ Suppression PDF : {pdf_path.name} ({raison})")
            try:
                pdf_path.unlink()
            except Exception as e:
                log_func(f"  ⚠ Impossible de supprimer {pdf_path.name} : {e}")
                continue

        # Étape 2 : Faut-il créer le PDF ?
        if not doit_creer_pdf(entry, pdf_path):
            continue  # PDF à jour, rien à faire

        # Étape 3 : Conversion
        log_func(f"  Conversion : {entry.name} → {nom_pdf}")
        success = convertir_docx_vers_pdf(entry, pdf_path, log_func)

        if success:
            nb_conversions += 1
            # Étape 4 : Nettoyage c:\temp
            nettoyer_temp_pdf(entry.name, log_func)
        else:
            log_func(f"  ✗ Échec conversion : {entry.name}")

    return nb_conversions


# ============================================================================
# TRAITEMENT PARTITIONS MUSICALES
# ============================================================================

def traiter_partitions_du_dossier(dossier: Path, log_func) -> int:
    """Ajoute les boutons YouTube aux partitions PDF du dossier.

    Ne s'exécute que si __correspondance.csv est présent dans le dossier.

    Workflow par partition :
    1. Lire __correspondance.csv (mapping nom_pdf → video_id)
    2. Trouver le PDF source __partition_<nom>.pdf
    3. Vérifier si regénération nécessaire
    4. Créer PDF final <nom>.pdf avec boutons YouTube

    Args:
        dossier: Dossier à traiter
        log_func: Fonction de log

    Returns:
        Nombre de partitions traitées
    """
    if not HAS_PARTITION_LIBS or partitions is None:
        return 0

    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return 0

    log_func(f"  Partitions musicales détectées : {dossier.name}")
    correspondances = partitions.charger_correspondances(csv_path)

    if not correspondances:
        log_func("  ⚠ __correspondance.csv vide ou illisible")
        return 0

    player_url = CONFIG.get("player_url", f"{BASE_PATH}/musique/index.html")
    nb_partitions = 0

    for nom_pdf_final, video_id in correspondances.items():
        # Chercher le PDF source (__partition_<nom>.pdf)
        pdf_source = None
        for f in dossier.iterdir():
            if not f.is_file():
                continue
            if not f.name.startswith("__partition_") or f.suffix.lower() != ".pdf":
                continue

            # Construire le nom final attendu depuis le nom source
            nom_sans_prefix = f.name[len("__partition_"):]
            nom_final_attendu = normaliser_nom(Path(nom_sans_prefix).stem) + ".pdf"

            if nom_final_attendu == nom_pdf_final:
                pdf_source = f
                break

        if not pdf_source:
            log_func(f"  ⚠ PDF source partition introuvable pour : {nom_pdf_final}")
            continue

        pdf_final = dossier / nom_pdf_final

        # Vérifier si regénération nécessaire
        if not partitions.doit_regenerer_partition(pdf_source, pdf_final):
            continue

        log_func(f"  🎵 Partition : {nom_pdf_final} → YouTube {video_id}")
        success = partitions.ajouter_boutons_partition(
            pdf_source,
            pdf_final,
            player_url,
            video_id
        )

        if success:
            nb_partitions += 1
        else:
            log_func(f"  ✗ Échec ajout boutons : {nom_pdf_final}")

    return nb_partitions


# ============================================================================
# GESTION STRUCTURE.py
# ============================================================================

def fichier_docx_existe_pour(fichier_pdf: Path, dossier: Path) -> bool:
    """Vérifie si un DOCX source existe pour un PDF donné.

    Args:
        fichier_pdf: Fichier PDF dont on cherche la source
        dossier: Dossier où chercher

    Returns:
        True si DOCX correspondant existe
    """
    pdf_stem_norm = normaliser_nom(fichier_pdf.stem)

    for f in dossier.iterdir():
        if f.suffix.lower() not in ('.doc', '.docx'):
            continue
        if normaliser_nom(f.stem) == pdf_stem_norm:
            return True

    return False


def mettre_a_jour_structure(dossier: Path, log_func) -> Dict[str, Any]:
    """Met à jour STRUCTURE.py d'un dossier.

    Scanne les fichiers réellement présents et ajoute les nouveaux.
    Les fichiers commençant par "__" sont ignorés dans la structure
    (sauf traitement PDF déjà fait en amont).

    Args:
        dossier: Dossier à traiter
        log_func: Fonction de log

    Returns:
        Structure mise à jour
    """
    log_func(f"  Structure : {dossier.name}")

    structure = struct.charger_structure(dossier)
    structure = struct.ajouter_defaults_structure(
        structure, dossier, CONFIG.get("titre_site", "Site")
    )

    modified = False
    position_suivante = struct.calculer_position_suivante(structure)

    entries = sorted(list(dossier.iterdir()), key=lambda x: x.name.lower())

    for entry in entries:
        # Filtrage global
        if fichiers.doit_filtrer_fichier(entry.name):
            continue
        if entry.name in IGNORER or entry.name in FICHIERS_ENTETE_PIED:
            continue
        if entry.is_file() and entry.suffix.lower() == ".py":
            continue

        # --- Dossiers ---
        if entry.is_dir():
            if not struct.element_existe(structure, entry.name, "dossiers"):
                struct.ajouter_element_structure(
                    structure, entry.name, normaliser_nom(entry.name),
                    "dossiers", position_suivante, log_func
                )
                position_suivante += 1
                modified = True
            continue

        # --- Fichiers ---
        ext = entry.suffix.lower().lstrip(".")

        # DOCX → enregistré dans structure avec nom_html = PDF normalisé
        if ext in ("doc", "docx"):
            if not struct.element_existe(structure, entry.name, "fichiers"):
                nom_pdf_norm = normaliser_nom(entry.stem) + ".pdf"
                element = {
                    "nom_document": entry.name,
                    "nom_html": nom_pdf_norm,
                    "nom_affiché": "{{nom_document_sans_ext}}",
                    "nom_TDM": "{{nom_document_sans_ext}}",
                    "ajout_affichage": True,
                    "affiché_index": True,
                    "affiché_TDM": True,
                    "position": position_suivante,
                }
                structure.setdefault("fichiers", []).append(element)
                position_suivante += 1
                modified = True
                log_func(f"    + DOCX ajouté : {entry.name} → {nom_pdf_norm}")
            continue

        # PDF dérivé d'un DOCX → ignoré dans STRUCTURE (le DOCX le représente)
        if ext == "pdf":
            if fichier_docx_existe_pour(entry, dossier):
                continue

        # Autres extensions acceptées
        if ext in EXTENSIONS_ACCEPTEES:
            if not struct.element_existe(structure, entry.name, "fichiers"):
                struct.ajouter_element_structure(
                    structure, entry.name, normaliser_nom(entry.name),
                    "fichiers", position_suivante, log_func
                )
                position_suivante += 1
                modified = True
                log_func(f"    + Fichier ajouté : {entry.name}")

    if modified:
        struct.sauvegarder_structure(dossier, structure)
        log_func(f"  ✓ STRUCTURE.py mis à jour")
    else:
        log_func(f"  ✓ STRUCTURE.py inchangé")

    return structure


# ============================================================================
# POINT D'ENTRÉE : traitement complet d'un dossier
# ============================================================================

def traiter_dossier_documents(dossier: Path, log_func) -> None:
    """Traite un dossier DOCUMENTS complet.

    Ordre :
    1. Conversion DOCX→PDF (avec règles régénération)
    2. Traitement partitions musicales
    3. Mise à jour STRUCTURE.py

    Args:
        dossier: Dossier à traiter
        log_func: Fonction de log
    """
    log_func(f"--- {dossier} ---")

    nb_pdf = traiter_docx_du_dossier(dossier, log_func)
    if nb_pdf > 0:
        log_func(f"  → {nb_pdf} PDF généré(s)")

    nb_partitions = traiter_partitions_du_dossier(dossier, log_func)
    if nb_partitions > 0:
        log_func(f"  → {nb_partitions} partition(s) traitée(s)")

    mettre_a_jour_structure(dossier, log_func)
    log_func("")

# Fin documents.py v1.0
