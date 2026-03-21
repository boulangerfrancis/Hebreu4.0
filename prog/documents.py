# documents.py — Version 2.2
# v2.2 : lib1 renomme en lib
# v2.1 : mettre_a_jour_structure préserve la clé "partitions"
# v2.0 : nettoyage fichiers .params residuels (remplaces par STRUCTURE.py)
# v1.9 : traiter_partitions_du_dossier + nom_partition_depuis_docx migres dans musique.py
# v1.5 : suppression messages [DBG]
# Module "DOCUMENTS" : conversions PDF, partitions musicales, gestion STRUCTURE.py
#
# Extrait de genere_site.py v24.0 → refactorisation v25.0
# Contient :
#   - normaliser_nom()
#   - Règles de régénération PDF (corrigées v25.0)
#   - Nettoyage c:\temp après conversion
#   - Traitement partitions __partition_*.pdf → PDF avec boutons
#   - Mise à jour STRUCTURE.py
#
# v1.1 : Correction traitement partitions
#   - nom_document dans STRUCTURE.py = "__partition_blabla et blabla.docx" (nom réel)
#   - nom_html = "blabla_et_blabla.pdf" (normalisé, sans préfixe __partition_)
#   - nom_affiché = "blabla et blabla" (lisible, sans préfixe, avec espaces)
#   - Le PDF surchargé (avec boutons) est bien créé sans préfixe dans documents/
#   - fichier_utils.doit_filtrer_fichier() mis à jour pour ne pas ignorer __partition_*.docx

version = ("documents.py", "2.2")
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
from lib import structure_utils as struct
from lib import fichier_utils as fichiers

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
    from lib import partition_utils as partitions
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
    """Nettoie les PDF residuels dans c:\\temp et les fichiers .params obsoletes.

    Les fichiers .params sont remplaces par la cle 'partitions' dans STRUCTURE.py.
    Cette fonction les supprime proprement lors de la migration.

    Args:
        log_func: Fonction de log
    """
    # Nettoyage c:\temp
    temp_dir = Path(r"c:\temp")
    if temp_dir.exists():
        pdf_restes = list(temp_dir.glob("*.pdf"))
        if pdf_restes:
            log_func(f"Nettoyage c:\\temp ({len(pdf_restes)} PDF residuels)...")
            for f in pdf_restes:
                try:
                    f.unlink()
                    log_func(f"  🗑 {f.name}")
                except Exception as e:
                    log_func(f"  ⚠ {f.name} : {e}")

    # Nettoyage fichiers .params (remplaces par STRUCTURE.py depuis v2.0)
    dossier_docs = Path(DOSSIER_DOCUMENTS)
    params_files = list(dossier_docs.rglob("*.params"))
    if params_files:
        log_func(f"Migration : suppression {len(params_files)} fichier(s) .params...")
        for f in params_files:
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
# TRAITEMENT PARTITIONS MUSICALES — migré dans musique.py v1.0
# ============================================================================
# nom_partition_depuis_docx() et traiter_partitions_du_dossier()
# sont désormais dans musique.py.
# Importé ici pour rétrocompatibilité si d'autres modules y font référence.

from musique import nom_partition_depuis_docx, traiter_partitions_du_dossier  # v1.3


# ============================================================================
# GESTION STRUCTURE.py
# ============================================================================
# GESTION STRUCTURE.py
# ============================================================================

def est_pdf_surcharge_partition(fichier_pdf: Path, dossier: Path) -> bool:
    """Vérifie si un PDF est le résultat de surcharge d'une partition.

    Un PDF `l_auvergnat_de_brassens_en_hebreu.pdf` est un PDF surchargé
    si un fichier `__partition_*.docx` existe dans le même dossier et
    produit le même nom normalisé.

    On ne doit PAS l'ajouter dans STRUCTURE.py car l'entrée
    `__partition_*.docx` le représente déjà.

    Args:
        fichier_pdf: Fichier PDF à tester
        dossier: Dossier où chercher les __partition_*.docx

    Returns:
        True si ce PDF est le surchargé d'une partition existante
    """
    pdf_stem_norm = normaliser_nom(fichier_pdf.stem)

    for f in dossier.iterdir():
        if not f.is_file():
            continue
        nom_lower = f.name.lower()
        if not (nom_lower.startswith("__partition_") or
                nom_lower.startswith("__partition _")):
            continue
        if f.suffix.lower() not in ('.doc', '.docx'):
            continue
        # Calculer le nom html que produirait ce __partition_*.docx
        _, nom_html = nom_partition_depuis_docx(f.name)
        if normaliser_nom(Path(nom_html).stem) == pdf_stem_norm:
            return True

    return False


def fichier_docx_existe_pour(fichier_pdf: Path, dossier: Path) -> bool:
    """Vérifie si un DOCX normal (non-partition) existe pour un PDF donné.

    Les __partition_*.docx sont exclus : leur PDF surchargé est géré
    séparément via est_pdf_surcharge_partition().

    Args:
        fichier_pdf: Fichier PDF dont on cherche la source
        dossier: Dossier où chercher

    Returns:
        True si DOCX normal correspondant existe
    """
    pdf_stem_norm = normaliser_nom(fichier_pdf.stem)

    for f in dossier.iterdir():
        if f.suffix.lower() not in ('.doc', '.docx'):
            continue
        nom_lower = f.name.lower()
        if nom_lower.startswith("__partition_") or nom_lower.startswith("__partition _"):
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

    # Préserver la clé "partitions" injectée par musique.py
    # Elle est déjà dans le fichier si musique.py vient de l'écrire ;
    # on la garde explicitement pour qu'elle survive à sauvegarder_structure()
    partitions_preservees = structure.get("partitions", None)

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

        # __partition_*.docx → entrée spéciale dans STRUCTURE.py
        # nom_document = "__partition_blabla et blabla.docx"  (nom réel du fichier)
        # nom_html     = "blabla_et_blabla.pdf"               (PDF surchargé, sans préfixe)
        # nom_affiché  = "blabla et blabla"                   (lisible, sans préfixe)
        if ext in ("doc", "docx") and entry.name.lower().startswith("__partition"):
            if not struct.element_existe(structure, entry.name, "fichiers"):
                nom_lisible, nom_html = nom_partition_depuis_docx(entry.name)
                element = {
                    "nom_document": entry.name,
                    "nom_html": nom_html,
                    "nom_affiché": nom_lisible,
                    "nom_TDM": "{{nom_affiché}}",
                    "ajout_affichage": True,
                    "affiché_index": True,
                    "affiché_TDM": True,
                    "position": position_suivante,
                }
                structure.setdefault("fichiers", []).append(element)
                position_suivante += 1
                modified = True
                log_func(f"    + Partition ajoutée : {entry.name} → {nom_html}")
            continue

        # DOCX normal → enregistré avec nom_html = PDF normalisé
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

        # PDF __partition_* → ignoré dans STRUCTURE (représenté par son DOCX source)
        if ext == "pdf" and (entry.name.lower().startswith("__partition_") or
                              entry.name.lower().startswith("__partition _")):
            continue

        # PDF surchargé (ex: l_auvergnat.pdf) issu d'un __partition_*.docx → ignoré
        # L'entrée __partition_*.docx dans STRUCTURE le représente déjà
        if ext == "pdf" and est_pdf_surcharge_partition(entry, dossier):
            continue

        # PDF "normal" dérivé d'un DOCX normal → ignoré (le DOCX le représente)
        if ext == "pdf" and fichier_docx_existe_pour(entry, dossier):
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
        # Réinjecter "partitions" si elle existait (patch musique.py)
        if partitions_preservees is not None:
            structure["partitions"] = partitions_preservees
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

# Fin documents.py v2.1
