# Méthodologie et Architecture — Site Hébreu 4.0

**Version** : 1.01 
**Projet** : C:\SiteGITHUB\Hebreu4.0  
**Générateur** : genere_site.py v25.1  

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture des dossiers](#2-architecture-des-dossiers)
3. [Modules Python](#3-modules-python)
4. [Workflow de génération](#4-workflow-de-génération)
5. [Gestion des partitions musicales](#5-gestion-des-partitions-musicales)
6. [STRUCTURE.py — clé de voûte](#6-structurepy--clé-de-voûte)
7. [Outils de développement et maintenance](#7-outils-de-développement-et-maintenance)
8. [Versioning et déploiement](#8-versioning-et-déploiement)
9. [Manuel utilisateur](#9-manuel-utilisateur)
10. [Référence CSV partitions](#10-référence-csv-partitions)

---

## 1. Vue d'ensemble

Le site est un **générateur de site statique** : il transforme une arborescence de fichiers Word (`.docx`) en un site HTML prêt pour GitHub Pages.

### Principe général

```
documents/          →   prog/genere_site.py   →   html/
  *.docx                                           *.html
  *.pdf                                            *.pdf
  STRUCTURE.py                                     index.html
  __partition_*.docx                               (+ TDM/)
```

Le site est ensuite servi localement via `npx http-server` (lancer.cmd) et publié sur GitHub Pages.

### Technologies

| Couche | Outil |
|--------|-------|
| Documents source | Microsoft Word (.docx) |
| Conversion PDF | PDFCreator (COM Windows) |
| Boutons YouTube | pypdf + reportlab |
| Génération HTML | Python 3 (modules custom) |
| Style | style.css unique |
| Publication | GitHub Pages |
| Test local | npx http-server |

---

## 2. Architecture des dossiers

```
C:\SiteGITHUB\Hebreu4.0\
│
├── documents\              Source : tous les DOCX et fichiers à publier
│   ├── STRUCTURE.py        Structure racine
│   ├── entete_general.html En-tête commun à toutes les pages
│   ├── pied_general.html   Pied de page commun
│   ├── musique\            Dossier player YouTube (créé automatiquement)
│   │   ├── STRUCTURE.py
│   │   ├── entete.html     Player iframe + fallback
│   │   └── entete_general.html
│   └── <sous-dossiers>\
│       ├── STRUCTURE.py
│       ├── *.docx          → converti en *.pdf
│       ├── __partition_*.docx  → PDF avec boutons YouTube
│       └── __correspondance.csv
│
├── html\                   Sortie : site statique (vidé à chaque génération)
│   ├── style.css
│   ├── index.html
│   ├── TDM\
│   └── <miroir de documents\>
│
├── prog\                   Moteur de génération
│   ├── genere_site.py      Point d'entrée
│   ├── settings.py         Configuration centrale
│   ├── documents.py        Conversions PDF + STRUCTURE.py
│   ├── musique.py          Dossier musique + partitions
│   ├── builder.py          Génération HTML
│   ├── docx_to_pdf.py      Conversion via PDFCreator
│   ├── versions.py         Affichage versions modules
│   └── lib1\
│       ├── partition_utils.py  Boutons YouTube sur PDF
│       ├── structure_utils.py  Lecture/écriture STRUCTURE.py
│       ├── html_utils.py
│       ├── fichier_utils.py
│       ├── pdf_utils.py
│       └── style.css
│
└── package\                Archive de déploiement
    └── prog\               Fichiers versionnés prêts à copier
        ├── genere_site_v25.1.py
        ├── musique_v1.4.py
        ├── documents_v2.0.py
        ├── ...
        └── remplace_v2.cmd
```

---

## 3. Modules Python

### `genere_site.py` — Point d'entrée
genere_site_v25.1.py
``` python 
# genere_site_v25.1.py — Version 25.1
"""
Générateur de site statique — Version 25.1

NOUVEAUTÉS v25.0 (refactorisation majeure) :
- settings.py  : fusion config.py + options.py (un seul fichier)
- documents.py : toute la logique DOCUMENTS (PDF, partitions, STRUCTURE.py)
- builder.py   : toute la logique HTML (index.html, copie, navigation)
- genere_site  : réduit au rôle de chef d'orchestre (~80 lignes)

CORRECTIONS v25.0 :
- Règles régénération PDF corrigées (A/B/C/D clairement séparées)
- Nettoyage automatique c:\\temp après chaque conversion (PDF résiduels)
- Log flush immédiat : plus de paquets, affichage en temps réel
- effacePDF.py supprimé (logique absorbée dans documents.py)

Workflow :
  Initialisation
    → Nettoyage c:\\temp
    → Préparation dossier HTML

  PHASE 1 : Pour chaque dossier DOCUMENTS
    → Conversion DOCX→PDF (règles CONFIG)
    → Traitement partitions musicales
    → Mise à jour STRUCTURE.py

  PHASE 2 : Pour chaque dossier DOCUMENTS
    → Génération index.html

  PHASE 3 :
    → Génération TDM/index.html
    → Copie fichiers vers HTML
    → Copie style.css
"""

import os
import sys
import psutil
from pathlib import Path
from datetime import datetime

# ============================================================================
# IMPORTS CONFIGURATION ET MODULES
# ============================================================================

from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG
import documents as docs
import builder as build
import musique as mus

# Import TDM (module séparé, inchangé)
try:
    from cree_table_des_matieres import generer_tdm
    HAS_TDM = True
except ImportError:
    HAS_TDM = False
    print("AVERTISSEMENT : cree_table_des_matieres.py non trouvé")

VERSION = ("genere_site.py", "25.1")
print(f"[Version] {VERSION[0]} — {VERSION[1]}")

# ============================================================================
# LOG
# ============================================================================

log_file = Path("generation.log")
log_file.write_text(
    f"--- GÉNÉRATION v{VERSION[1]} — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ---\n",
    encoding="utf-8"
)


def log(msg: str) -> None:
    """Log console (flush immédiat) + fichier."""
    print(msg, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ============================================================================
# GESTION WORD
# ============================================================================

def fermer_word_si_ouvert() -> None:
    """Ferme les processus Word résiduels en fin de traitement."""
    processes = [
        proc for proc in psutil.process_iter(['pid', 'name'])
        if proc.info['name'] and proc.info['name'].upper() == 'WINWORD.EXE'
    ]
    if not processes:
        return

    log("Fermeture Word résiduel...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            log("  ✓ Word fermé")
        except Exception:
            try:
                proc.kill()
                log("  ✓ Word forcé fermé")
            except Exception as e:
                log(f"  ⚠ Impossible de fermer Word : {e}")


# ============================================================================
# MAIN — CHEF D'ORCHESTRE
# ============================================================================

def main() -> None:
    """Génération complète du site statique — Workflow v25.0."""

    log("=" * 70)
    log(f"=== GÉNÉRATION SITE STATIQUE v{VERSION[1]} ===")
    log("=" * 70)
    log(f"Source    : {DOSSIER_DOCUMENTS}")
    log(f"HTML      : {DOSSIER_HTML}")
    log(f"BASE_PATH : {BASE_PATH}")
    log("")

    # Statut modules
    if docs.DOCX2PDF_DISPONIBLE:
        log("✓ Conversion PDF disponible (PDFCreator)")
    else:
        log("✗ Conversion PDF désactivée (PDFCreator manquant)")

    if docs.HAS_PARTITION_LIBS:
        log("✓ Modules partitions disponibles (pypdf + reportlab)")
    else:
        log("✗ Modules partitions manquants (pip install pypdf reportlab)")

    if HAS_TDM:
        log("✓ Module TDM disponible")
    else:
        log("✗ Module TDM manquant")
    log("")

    # ------------------------------------------------------------------
    # INITIALISATION
    # ------------------------------------------------------------------

    # Nettoyage c:\temp (PDF résiduels de sessions précédentes)
    docs.nettoyer_tous_temp_pdf(log)

    # Préparer dossier HTML (vider + style.css + TDM/)
    style_source = Path(__file__).parent / "lib1" / "style.css"
    dossier_tdm = CONFIG.get("dossier_tdm", "TDM")
    build.initialiser_dossier_html(style_source, dossier_tdm, log)
    log("")

    # Initialiser dossier musique (player YouTube)
    log("Initialisation dossier musique...")
    mus.initialiser_dossier_musique(log)
    log("")

    # ------------------------------------------------------------------
    # PHASE 1 : DOCUMENTS — PDF + PARTITIONS + STRUCTURE.py
    # ------------------------------------------------------------------
    log("=" * 70)
    log("PHASE 1 : GÉNÉRATION PDF + PARTITIONS + STRUCTURE.py")
    log("=" * 70)
    log("")

    for racine, dirs, _ in os.walk(DOSSIER_DOCUMENTS):
        dirs[:] = [d for d in dirs
                   if not d.startswith("__")
                   and d not in docs.IGNORER]
        docs.traiter_dossier_documents(Path(racine), log)

    # ------------------------------------------------------------------
    # PHASE 2 : GÉNÉRATION index.html
    # ------------------------------------------------------------------
    log("=" * 70)
    log("PHASE 2 : GÉNÉRATION index.html")
    log("=" * 70)
    log("")

    for racine, dirs, _ in os.walk(DOSSIER_DOCUMENTS):
        dirs[:] = [d for d in dirs if d not in docs.IGNORER]
        log(f"--- {Path(racine).name} ---")
        build.generer_page_index(Path(racine), VERSION[1], log)
        log("")

    # ------------------------------------------------------------------
    # PHASE 3 : TDM + COPIE FICHIERS
    # ------------------------------------------------------------------
    log("=" * 70)
    log("PHASE 3 : TABLE DES MATIÈRES + COPIE FICHIERS")
    log("=" * 70)
    log("")

    if HAS_TDM:
        log("Génération TDM/index.html...")
        generer_tdm()
        log("✓ TDM générée")
        log("")

    build.copier_fichiers_site(log)
    log("")

    # ------------------------------------------------------------------
    # NETTOYAGE FINAL
    # ------------------------------------------------------------------
    fermer_word_si_ouvert()

    log("")
    log("=" * 70)
    log(f"=== FIN GÉNÉRATION — {datetime.now().strftime('%H:%M:%S')} ===")
    log("=" * 70)


if __name__ == "__main__":
    main()

# Fin genere_site_v25.1.py


```

Orchestre les 3 phases de génération. Importe tous les autres modules.  
**Version actuelle** : 25.1

### `settings.py` — Configuration centrale
settings_v1.0.py
``` python 
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

```
Remplace les anciens `lib1/config.py` et `lib1/options.py`.  
Contient : `DOSSIER_DOCUMENTS`, `DOSSIER_HTML`, `BASE_PATH`, `CONFIG`.

**Clés CONFIG importantes** :

| Clé | Valeur par défaut | Description |
|-----|-------------------|-------------|
| `regeneration` | `False` | Force la régénération de tous les PDF |
| `titre_site` | `"Hebreu 4.0"` | Titre affiché dans le menu |
| `player_url` | `BASE_PATH/musique/index.html` | URL du player YouTube |
| `dossier_tdm` | `"TDM"` | Nom du dossier table des matières |

### `documents.py` — Gestion documents
documents_v2.0.py
``` python 
# documents.py — Version 2.0
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

version = ("documents.py", "2.0")
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

# Fin documents.py v2.0

```
- Conversion DOCX→PDF (règles A/B/C/D de régénération)
- Mise à jour STRUCTURE.py (détection nouveaux fichiers)
- Nettoyage `c:\temp` et fichiers `.params` obsolètes

**Règles de régénération PDF** :
- **A** : PDF absent → créer
- **B** : DOCX plus récent que PDF → recréer
- **C** : CONFIG `regeneration=True` → forcer
- **D** : Règle spéciale (voir code)

### `musique.py` — Partitions et player
musique_v1.4.py
``` python
# musique.py — Version 1.4
# v1.4 : patch chirurgical de STRUCTURE.py (preserve valeurs manuelles, ajout a la fin)
#         correction surcharge partition sans reinitialiser
"""
v1.3 :
  - Refactorisation majeure : parametres partitions stockes dans STRUCTURE.py
    sous la cle "partitions" (liste de dicts)
  - Plus de fichier .params sur le disque
  - CSV lu UNE SEULE FOIS (ou si plus recent que STRUCTURE.py)
  - doit_regenerer_partition() base sur params_signature dans STRUCTURE.py
  - B) Regles regeneration PDF identiques aux PDF ordinaires (CONFIG)
  - A) Ne jamais ecraser les fichiers existants dans documents/musique/
  - C) Player iframe + fallback "Ouvrir sur YouTube"

  Structure "partitions" dans STRUCTURE.py :
    "partitions": [
        {
            "nom_docx"        : "__partition_L'auvergnat.docx",
            "nom_pdf_source"  : "__partition_l_auvergnat.pdf",
            "nom_html"        : "l_auvergnat.pdf",
            "nom_affiche"     : "L'auvergnat de Brassens",
            "video_id"        : "morcvF-aFsg",
            "orientation"     : "H",
            "fond_opacite_pct": 100.0,
            "x"               : null,
            "y"               : null,
            "params_signature": "morcvF-aFsg|H|100.0|None|None"
        }
    ]
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional

version = ("musique.py", "1.4")
print(f"[Import] {version[0]} - Version {version[1]} charge")

from lib1 import partition_utils as partitions
from lib1 import structure_utils as struct
from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG

_pu_ver = getattr(partitions, "version", ("?", "?"))
print(f"  [musique] partition_utils : v{_pu_ver[1]}")

NOM_DOSSIER_MUSIQUE = "musique"


# ============================================================================
# TEMPLATES HTML
# ============================================================================

def _template_entete_player() -> str:
    return """<!-- entete.html — Player YouTube (iframe + fallback) -->
<div class="monTitre">&#127925; Lecteur Musical</div>
<div id="player-zone" style="display:flex;flex-direction:column;align-items:center;padding:20px;gap:16px;">

  <div id="video-wrapper" style="
      width:100%; max-width:800px; aspect-ratio:16/9;
      background:#111; border-radius:8px; overflow:hidden;
      box-shadow:0 4px 16px rgba(0,0,0,.3); display:none;">
    <iframe id="yt-iframe" width="100%" height="100%" frameborder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen style="display:block;"></iframe>
  </div>

  <div id="fallback-zone" style="display:none; text-align:center; padding:20px;">
    <p style="color:#888; margin-bottom:12px;">
      Le lecteur integre n'est pas disponible dans ce contexte.
    </p>
    <a id="yt-link" href="#" target="_blank"
       style="display:inline-block; background:#FF0000; color:#fff;
              padding:12px 28px; border-radius:6px; text-decoration:none;
              font-weight:bold; font-size:1.05em;">
      &#9654; Ouvrir sur YouTube
    </a>
  </div>

  <p id="no-video-msg" style="color:#888; font-style:italic;">
    Aucune video selectionnee. Cliquez sur &#127925; "Jouer ici" depuis une partition.
  </p>
</div>

<script>
(function() {
  var params   = new URLSearchParams(window.location.search);
  var videoId  = params.get('v');
  var iframe   = document.getElementById('yt-iframe');
  var wrapper  = document.getElementById('video-wrapper');
  var fallback = document.getElementById('fallback-zone');
  var noMsg    = document.getElementById('no-video-msg');
  var ytLink   = document.getElementById('yt-link');

  if (!videoId) return;

  noMsg.style.display = 'none';
  var ytUrl    = 'https://www.youtube.com/watch?v=' + encodeURIComponent(videoId);
  var embedUrl = 'https://www.youtube.com/embed/'   + encodeURIComponent(videoId)
               + '?autoplay=1&rel=0';
  ytLink.href = ytUrl;

  wrapper.style.display = 'block';
  iframe.src = embedUrl;

  var loaded = false;
  iframe.onload = function() { loaded = true; };
  setTimeout(function() {
    if (!loaded) {
      wrapper.style.display  = 'none';
      fallback.style.display = 'block';
    }
  }, 3000);
})();
</script>
"""


def _template_entete_general() -> str:
    return """<!-- entete_general.html musique -->
<div style="text-align:center; color:#7f8c8d; font-size:.95em; padding:8px 0 0 0;">
  Cliquez sur &#127925; &ldquo;Jouer ici&rdquo; depuis une partition pour lancer la musique
</div>
"""


def _template_structure_musique() -> str:
    return """# STRUCTURE.py — Dossier musique
# Cree automatiquement si absent. Modifiable manuellement.
# La cle "partitions" est geree par musique.py — ne pas modifier a la main.

STRUCTURE = {
    "titre_dossier"   : "Lecteur Musical",
    "nom_navigation"  : "Musique",
    "titre_table"     : "",
    "entete_general"  : True,
    "pied_general"    : True,
    "entete"          : True,
    "pied"            : False,
    "navigation"      : False,
    "haut_page"       : False,
    "bas_page"        : False,
    "ajout_affichage" : False,
    "affiche_index"   : False,
    "affiche_TDM"     : False,
    "dossiers"        : [],
    "fichiers"        : [],
    "partitions"      : []
}
"""


# ============================================================================
# INIT DOSSIER MUSIQUE
# ============================================================================

def initialiser_dossier_musique(log_func) -> Path:
    """Cree le dossier musique/ et ses fichiers UNIQUEMENT s'ils sont absents.

    Ne touche jamais aux fichiers existants (modifications manuelles preservees).
    """
    dossier = Path(DOSSIER_DOCUMENTS) / NOM_DOSSIER_MUSIQUE
    crees   = []

    if not dossier.exists():
        dossier.mkdir(parents=True)
        crees.append("dossier musique/")

    for nom, contenu in [
        ("entete.html",          _template_entete_player()),
        ("entete_general.html",  _template_entete_general()),
        ("STRUCTURE.py",         _template_structure_musique()),
    ]:
        dest = dossier / nom
        if not dest.exists():
            dest.write_text(contenu, encoding="utf-8")
            crees.append(nom)

    if crees:
        log_func(f"  Musique : crees -> {', '.join(crees)}")
    else:
        log_func(f"  Musique : dossier existant conserve")

    return dossier


# ============================================================================
# NORMALISATION NOM PARTITION
# ============================================================================

def _normaliser(texte: str) -> str:
    """Minusc. sans accents, espaces et apostrophes -> underscore."""
    t = unicodedata.normalize('NFD', texte)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = t.replace("'", "_").replace("\u2019", "_").replace(" ", "_").lower()
    return t


def nom_partition_depuis_docx(nom_docx: str):
    """Calcule (nom_lisible, nom_html) depuis __partition_*.docx."""
    sans_prefix = nom_docx
    for prefix in ("__partition_", "__partition _"):
        if nom_docx.lower().startswith(prefix.lower()):
            sans_prefix = nom_docx[len(prefix):]
            break
    stem        = Path(sans_prefix).stem
    nom_lisible = stem
    nom_html    = _normaliser(stem) + ".pdf"
    return (nom_lisible, nom_html)


# ============================================================================
# GESTION CLE "partitions" DANS STRUCTURE.py
# ============================================================================

def lire_partitions_structure(dossier: Path) -> List[dict]:
    """Lit la liste 'partitions' du STRUCTURE.py du dossier.
    Retourne [] si absente ou erreur.
    """
    s = struct.charger_structure(dossier)
    return s.get("partitions", [])


def sauvegarder_partitions_structure(dossier: Path, liste: List[dict],
                                      log_func) -> None:
    """Patche UNIQUEMENT la cle 'partitions' dans STRUCTURE.py.

    Toutes les autres cles et valeurs manuelles sont preservees.
    Si la cle 'partitions' n'existe pas, elle est ajoutee A LA FIN
    du dict STRUCTURE, avant le } fermant.

    Strategie : lecture texte + remplacement regex de la valeur de 'partitions'.
    Si absent : injection avant la derniere ligne de fermeture.
    """
    fichier = dossier / "STRUCTURE.py"
    if not fichier.exists():
        log_func("  ⚠ STRUCTURE.py absent, impossible de patcher")
        return

    import json, re

    # Serialiser la liste en Python valide
    val_json = json.dumps(liste, ensure_ascii=False, indent=4)
    val_py   = val_json.replace("true",  "True") \
                       .replace("false", "False") \
                       .replace("null",  "None")
    # Indenter pour s'integrer dans le dict STRUCTURE (4 espaces)
    val_indente = val_py.replace("\n", "\n    ")

    contenu = fichier.read_text(encoding="utf-8")

    # Cas 1 : cle 'partitions' deja presente -> remplacer sa valeur
    # Pattern : "partitions" : [...] ou "partitions": [...]
    pattern = r'("partitions"\s*:\s*)\[.*?\]'
    remplacement = r'\g<1>' + val_indente

    nouveau, nb = re.subn(pattern, remplacement, contenu, flags=re.DOTALL)
    if nb > 0:
        fichier.write_text(nouveau, encoding="utf-8")
        log_func(f"  STRUCTURE.py : cle 'partitions' mise a jour ({len(liste)} entree(s))")
        return

    # Cas 2 : cle absente -> injecter avant la derniere accolade fermante
    # Trouver la derniere ligne contenant "}" ou "})" du dict STRUCTURE
    lignes = contenu.splitlines()
    idx_insertion = None
    for i in range(len(lignes) - 1, -1, -1):
        stripped = lignes[i].strip()
        if stripped in ("}", "})"):
            idx_insertion = i
            break

    if idx_insertion is None:
        log_func("  ⚠ Structure STRUCTURE.py non reconnue, partition non sauvegardee")
        return

    ligne_partition = f'    "partitions"      : {val_indente}'
    # Ajouter une virgule a la ligne precedente si elle n'en a pas
    if idx_insertion > 0:
        prev = lignes[idx_insertion - 1].rstrip()
        if prev and not prev.endswith(","):
            lignes[idx_insertion - 1] = prev + ","

    lignes.insert(idx_insertion, ligne_partition)
    fichier.write_text("\n".join(lignes), encoding="utf-8")
    log_func(f"  STRUCTURE.py : cle 'partitions' ajoutee ({len(liste)} entree(s))")


def _signature_depuis_params(p: dict) -> str:
    return partitions.params_signature(
        p["video_id"], p["orientation"], p["fond_opacite_pct"],
        p.get("x"), p.get("y")
    )


def _csv_plus_recent_que_structure(dossier: Path) -> bool:
    """Vrai si __correspondance.csv est plus recent que STRUCTURE.py."""
    csv_p = dossier / "__correspondance.csv"
    str_p = dossier / "STRUCTURE.py"
    if not csv_p.exists():
        return False
    if not str_p.exists():
        return True
    return csv_p.stat().st_mtime > str_p.stat().st_mtime


def synchroniser_partitions_csv(dossier: Path, log_func) -> List[dict]:
    """Lit le CSV et met a jour la cle 'partitions' dans STRUCTURE.py.

    Appele seulement si CSV plus recent que STRUCTURE.py ou si
    une partition du dossier n'est pas encore dans STRUCTURE.py.

    Conserve les params_signature existantes pour les partitions inchangees.
    Retourne la liste mise a jour.
    """
    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return lire_partitions_structure(dossier)

    corresp = partitions.charger_correspondances(csv_path)
    if not corresp:
        return lire_partitions_structure(dossier)

    # Charger partitions existantes (indexees par nom_html)
    existantes = {p["nom_html"]: p for p in lire_partitions_structure(dossier)}

    nouvelle_liste = []
    for nom_html, params in corresp.items():
        video_id         = params["video_id"]
        orientation      = params.get("orientation", "V")
        fond_opacite_pct = params.get("fond_opacite_pct", 0.0)
        pos_x            = params.get("x")
        pos_y            = params.get("y")

        # Chercher le DOCX source dans le dossier
        nom_docx    = None
        nom_affiche = Path(nom_html).stem  # fallback
        for f in dossier.iterdir():
            if not f.is_file() or f.suffix.lower() not in ('.doc', '.docx'):
                continue
            nl = f.name.lower()
            if not (nl.startswith("__partition_") or nl.startswith("__partition _")):
                continue
            lisible, html_calcule = nom_partition_depuis_docx(f.name)
            if html_calcule == nom_html:
                nom_docx    = f.name
                nom_affiche = lisible
                break

        nom_pdf_source = None
        if nom_docx:
            # Le PDF source porte le meme nom normalise que le DOCX
            nom_pdf_source = "__partition_" + _normaliser(
                Path(nom_docx[len("__partition_"):] if
                     nom_docx.lower().startswith("__partition_") else nom_docx).stem
            ) + ".pdf"

        sig = partitions.params_signature(
            video_id, orientation, fond_opacite_pct, pos_x, pos_y)

        entree = {
            "nom_docx"        : nom_docx or "",
            "nom_pdf_source"  : nom_pdf_source or "",
            "nom_html"        : nom_html,
            "nom_affiche"     : nom_affiche,
            "video_id"        : video_id,
            "orientation"     : orientation,
            "fond_opacite_pct": fond_opacite_pct,
            "x"               : pos_x,
            "y"               : pos_y,
            "params_signature": sig,
        }
        nouvelle_liste.append(entree)

    sauvegarder_partitions_structure(dossier, nouvelle_liste, log_func)
    return nouvelle_liste


# ============================================================================
# TRAITEMENT PARTITIONS
# ============================================================================

def traiter_partitions_du_dossier(dossier: Path, log_func) -> int:
    """Ajoute boutons YouTube aux partitions PDF du dossier.

    Workflow :
    1. Si CSV plus recent que STRUCTURE.py -> synchroniser_partitions_csv()
    2. Lire liste "partitions" depuis STRUCTURE.py
    3. Pour chaque partition : regenerer si params_signature a change
       OU si __partition_*.pdf source est plus recent que PDF final (regle B)

    Args:
        dossier : Dossier a traiter
        log_func: Fonction de log
    Returns:
        Nombre de partitions traitees
    """
    if not getattr(partitions, "HAS_PDF_LIBS", False):
        return 0

    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return 0

    # Synchroniser si CSV plus recent ou partitions absentes de STRUCTURE
    liste_partitions = lire_partitions_structure(dossier)
    if _csv_plus_recent_que_structure(dossier) or not liste_partitions:
        log_func(f"  Lecture CSV partitions : {dossier.name}")
        liste_partitions = synchroniser_partitions_csv(dossier, log_func)

    if not liste_partitions:
        log_func("  ⚠ Aucune partition trouvee")
        return 0

    player_url = CONFIG.get("player_url",
                            f"{BASE_PATH}/{NOM_DOSSIER_MUSIQUE}/index.html")
    force = CONFIG.get("regeneration", False)
    nb    = 0

    for p in liste_partitions:
        nom_html        = p["nom_html"]
        nom_pdf_source  = p.get("nom_pdf_source", "")
        video_id        = p["video_id"]
        orientation     = p.get("orientation", "V")
        fond_opacite    = p.get("fond_opacite_pct", 0.0)
        pos_x           = p.get("x")
        pos_y           = p.get("y")
        sig_stockee     = p.get("params_signature", "")
        sig_actuelle    = partitions.params_signature(
                            video_id, orientation, fond_opacite, pos_x, pos_y)

        pdf_source = dossier / nom_pdf_source if nom_pdf_source else None
        # Fallback : chercher __partition_*.pdf correspondant
        if not pdf_source or not pdf_source.exists():
            pdf_source = None
            for f in dossier.iterdir():
                if not f.is_file() or f.suffix.lower() != ".pdf":
                    continue
                nl = f.name.lower()
                if not (nl.startswith("__partition_") or nl.startswith("__partition _")):
                    continue
                _, html_calcule = nom_partition_depuis_docx(f.stem + ".docx")
                if html_calcule == nom_html:
                    pdf_source = f
                    break

        if not pdf_source:
            log_func(f"  ⚠ Source PDF introuvable : {nom_html}")
            continue

        pdf_final = dossier / nom_html

        # Determiner si regeneration necessaire (Regle B)
        regenerer = force
        if not regenerer:
            if not pdf_final.exists():
                regenerer = True
            elif pdf_source.stat().st_mtime > pdf_final.stat().st_mtime:
                regenerer = True
            elif sig_actuelle != sig_stockee:
                regenerer = True

        if not regenerer:
            log_func(f"  ✓ Partition a jour : {nom_html}")
            continue

        raison = "force" if force else \
                 "absente" if not pdf_final.exists() else \
                 "source modifie" if pdf_source.stat().st_mtime > pdf_final.stat().st_mtime \
                 else "params changes"
        log_func(f"  🎵 {pdf_source.name} -> {nom_html}  ({raison})")

        ok = partitions.ajouter_boutons_partition(
            pdf_source, pdf_final, player_url, video_id,
            orientation=orientation, fond_opacite_pct=fond_opacite,
            pos_x=pos_x, pos_y=pos_y,
        )
        if ok:
            # Mettre a jour la signature dans STRUCTURE.py
            p["params_signature"] = sig_actuelle
            nb += 1
        else:
            log_func(f"  ✗ Echec : {nom_html}")

    # Sauvegarder les signatures mises a jour
    if nb > 0:
        sauvegarder_partitions_structure(dossier, liste_partitions, log_func)

    return nb

# Fin musique.py v1.4
 
```
Responsabilités :
- Création et maintenance de `documents/musique/`
- Lecture du CSV `__correspondance.csv`
- Mise à jour chirurgicale de la clé `"partitions"` dans STRUCTURE.py
- Ajout des boutons YouTube sur les PDF de partitions

### `builder.py` — Génération HTML
builder_v1.0.py
``` python
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
 
```

Génère les `index.html` de chaque dossier à partir de STRUCTURE.py.  
Gère : navigation fil d'Ariane, en-têtes/pieds, table des fichiers.

### `lib1/partition_utils.py` — Boutons PDF

partition_utils_v1.9.py
``` python
# partition_utils.py — Version 1.9
# Traitement partitions musicales avec boutons YouTube
"""
v1.9 :
  - Suppression fichiers .params — signature stockee dans STRUCTURE.py
  - doit_regenerer_partition() accepte params_signature en parametre direct
  - _params_signature() reste utile pour comparaison dans musique.py

v1.8 : _get_col() — lecture CSV insensible aux noms de colonnes
v1.7 : Y defaut=2%, semantique fond corrigee (0=opaque, 100=transparent)
v1.6 : V/H, fond en %, x/y flottants, debug CSV
"""

import csv
import re
import unicodedata
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
from typing import Dict, Optional

try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, white, Color
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False
    print("AVERTISSEMENT : pypdf ou reportlab manquant — pip install pypdf reportlab")

version = ("partition_utils.py", "1.9")
print(f"[Import] {version[0]} - Version {version[1]} charge")

# Constantes boutons
BUTTON_WIDTH   = 140
BUTTON_HEIGHT  = 50
BUTTON_SPACING = 20
FOND_PADDING   = 8

# Defauts CSV
DEFAULT_Y_PCT            = 2.0   # % hauteur depuis le bas (marge basse)
DEFAULT_X_PCT            = None  # None = centre automatiquement
DEFAULT_FOND_OPACITE_PCT = 0.0   # 0 = fond blanc opaque


# ============================================================================
# DESSIN BOUTONS
# ============================================================================

def draw_button(c, x, y, width, height, color, text):
    """Dessine un bouton arrondi avec icone play."""
    radius = height * 0.4
    c.setFillColor(color)
    c.roundRect(x, y, width, height, radius / 2, fill=1)
    circle_x = x + radius + 5
    circle_y = y + height / 2
    c.setFillColor(white)
    c.circle(circle_x, circle_y, radius, fill=1)
    c.setFillColor(color)
    tri_half = radius * 0.6
    path = c.beginPath()
    path.moveTo(circle_x - tri_half * 0.6, circle_y - tri_half)
    path.lineTo(circle_x - tri_half * 0.6, circle_y + tri_half)
    path.lineTo(circle_x + tri_half, circle_y)
    path.close()
    c.drawPath(path, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", int(height / 3))
    text_x = x + 2 * radius + 10
    text_y = y + (height - int(height / 3)) / 2 - 1
    c.drawString(text_x, text_y, text)


def create_overlay(page_width, page_height, player_url, video_id,
                   x_pct=None, y_pct=None, fond_opacite_pct=0.0):
    """Cree overlay PDF avec 2 boutons.

    x_pct / y_pct : % de la page depuis coin bas-gauche. None = defauts.
    fond_opacite_pct : 0=fond blanc opaque, 100=invisible.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    total_width = BUTTON_WIDTH * 2 + BUTTON_SPACING

    y_pct_val = y_pct if y_pct is not None else DEFAULT_Y_PCT
    start_y   = (y_pct_val / 100.0) * page_height
    start_x   = ((x_pct / 100.0) * page_width) if x_pct is not None \
                else (page_width - total_width) / 2

    # Fond blanc avec opacite
    alpha = max(0.0, min(1.0, 1.0 - fond_opacite_pct / 100.0))
    if alpha > 0.01:
        pad = FOND_PADDING
        c.setFillColor(Color(1, 1, 1, alpha=alpha))
        c.setStrokeColor(Color(1, 1, 1, alpha=alpha))
        c.rect(start_x - pad, start_y - pad,
               total_width + 2 * pad, BUTTON_HEIGHT + 2 * pad,
               fill=1, stroke=0)

    # Bouton rouge YouTube
    draw_button(c, start_x, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#FF0000"), "YouTube")
    c.linkURL(f"https://youtube.com/watch?v={quote(video_id)}",
              (start_x, start_y, start_x + BUTTON_WIDTH, start_y + BUTTON_HEIGHT),
              relative=0)

    # Bouton vert Jouer ici
    x2 = start_x + BUTTON_WIDTH + BUTTON_SPACING
    draw_button(c, x2, start_y, BUTTON_WIDTH, BUTTON_HEIGHT,
                HexColor("#28a745"), "Jouer ici")
    c.linkURL(f"{player_url}?v={quote(video_id)}",
              (x2, start_y, x2 + BUTTON_WIDTH, start_y + BUTTON_HEIGHT),
              relative=0)

    c.save()
    packet.seek(0)
    return PdfReader(packet)


# ============================================================================
# AJOUT BOUTONS SUR PDF
# ============================================================================

def ajouter_boutons_partition(source_pdf: Path, target_pdf: Path,
                               player_url: str, video_id: str,
                               orientation: str = "V",
                               fond_opacite_pct: float = 0.0,
                               pos_x: float = None,
                               pos_y: float = None) -> bool:
    """Ajoute boutons YouTube sur premiere page partition.

    Ne cree plus de fichier .params — la signature est geree par musique.py
    dans STRUCTURE.py.
    """
    if not HAS_PDF_LIBS:
        print("  ✗ pypdf/reportlab manquant")
        return False
    try:
        reader = PdfReader(source_pdf)
        writer = PdfWriter()
        first_page = reader.pages[0]
        width  = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)
        overlay_pdf = create_overlay(width, height, player_url, video_id,
                                     x_pct=pos_x, y_pct=pos_y,
                                     fond_opacite_pct=fond_opacite_pct)
        first_page.merge_page(overlay_pdf.pages[0])
        writer.add_page(first_page)
        for page in reader.pages[1:]:
            writer.add_page(page)
        target_pdf.parent.mkdir(parents=True, exist_ok=True)
        with open(target_pdf, "wb") as f:
            writer.write(f)
        return True
    except Exception as e:
        print(f"  ✗ Erreur ajout boutons : {e}")
        return False


# ============================================================================
# LECTURE __correspondance.csv
# ============================================================================

def _get_col(row: dict, *noms) -> str:
    """Lit la premiere colonne trouvee (insensible a la casse)."""
    row_lower = {k.lower().strip(): v for k, v in row.items() if k}
    for nom in noms:
        val = row_lower.get(nom.lower())
        if val is not None:
            return str(val).strip()
    return ""


def _normaliser_cle_csv(pdf_name: str) -> str:
    """Retire prefixe __partition_ et normalise : minusc., sans accents, espaces->_."""
    nom  = pdf_name.strip()
    nom  = re.sub(r'^__partition[\s_]+', '', nom, flags=re.IGNORECASE)
    stem = Path(nom).stem
    ext  = Path(nom).suffix
    stem = unicodedata.normalize('NFD', stem)
    stem = ''.join(c for c in stem if unicodedata.category(c) != 'Mn')
    stem = stem.replace("'", "_").replace("\u2019", "_").replace(" ", "_").lower()
    return stem + ext.lower()


def _parse_float(val, defaut=None) -> Optional[float]:
    v = val.strip() if val else ""
    if not v:
        return defaut
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return defaut


def _parse_orientation(val: str) -> str:
    v = val.strip().upper()
    return "H" if v in ("H", "LANDSCAPE", "L", "PAYSAGE") else "V"


def _parse_fond(val: str) -> float:
    v = val.strip() if val else ""
    if not v:
        return DEFAULT_FOND_OPACITE_PCT
    try:
        return max(0.0, min(100.0, float(v.replace(",", "."))))
    except ValueError:
        return DEFAULT_FOND_OPACITE_PCT


def charger_correspondances(csv_path: Path) -> Dict[str, dict]:
    """Charge correspondances depuis CSV avec noms de colonnes flexibles.

    Noms de colonnes supportes (insensible a la casse) :
        nom_partition__pdf  | pdf_name      -> nom fichier
        youtube_url         | url           -> URL YouTube
        orientation                         -> V ou H
        transparence        | fond_transparent -> 0-100%
        position_Horizontale | x             -> % largeur
        position_verticale  | y             -> % hauteur depuis bas

    Returns:
        Dict {nom_normalise: {video_id, orientation, fond_opacite_pct, x, y}}
    """
    if not csv_path.exists():
        return {}

    correspondances = {}
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pdf_name_brut = _get_col(row,
                    "nom_partition__pdf", "pdf_name", "nom_partition_pdf", "nom_pdf")
                youtube_url = _get_col(row, "youtube_url", "url", "youtube")

                if not pdf_name_brut:
                    continue

                pdf_name         = _normaliser_cle_csv(pdf_name_brut)
                video_id         = youtube_url.split("v=")[-1].split("&")[0] \
                                   if "v=" in youtube_url else youtube_url
                orientation      = _parse_orientation(_get_col(row, "orientation"))
                fond_opacite_pct = _parse_fond(_get_col(row,
                    "transparence", "fond_transparent", "fond", "transparency"))
                pos_x = _parse_float(_get_col(row,
                    "position_horizontale", "position_Horizontale", "x", "pos_x"))
                pos_y = _parse_float(_get_col(row,
                    "position_verticale", "position_Verticale", "y", "pos_y"))

                params = {
                    "video_id"        : video_id,
                    "orientation"     : orientation,
                    "fond_opacite_pct": fond_opacite_pct,
                    "x"               : pos_x,
                    "y"               : pos_y,
                }

                x_str = f"{pos_x}%" if pos_x is not None else "centre"
                y_str = f"{pos_y}%" if pos_y is not None else f"{DEFAULT_Y_PCT}% (defaut)"
                print(f"  [CSV] {pdf_name_brut!r}")
                print(f"        -> cle    : {pdf_name!r}")
                print(f"        -> video  : {video_id!r}")
                print(f"        -> orient : {'H (Paysage)' if orientation=='H' else 'V (Portrait)'}")
                print(f"        -> fond   : {fond_opacite_pct}% transparent")
                print(f"        -> x      : {x_str}")
                print(f"        -> y      : {y_str}")

                correspondances[pdf_name] = params

        return correspondances
    except Exception as e:
        print(f"  ✗ Erreur lecture correspondances : {e}")
        return {}


# ============================================================================
# SIGNATURE PARAMETRES (pour detecter les changements)
# ============================================================================

def params_signature(video_id: str, orientation: str, fond_opacite_pct: float,
                     pos_x, pos_y) -> str:
    """Chaine compacte representant les parametres d'une partition.
    Stockee dans STRUCTURE.py -> cle 'params_signature' de chaque partition.
    """
    return f"{video_id}|{orientation}|{fond_opacite_pct}|{pos_x}|{pos_y}"


def doit_regenerer_partition(source_pdf: Path, target_pdf: Path,
                              sig_actuelle: str = "") -> bool:
    """Verifie si partition doit etre regeneree.

    Regenere si :
    - target absent
    - source plus recent que target
    - sig_actuelle (params_signature) differente de celle stockee dans STRUCTURE.py

    La signature est passee directement (plus de fichier .params).
    La comparaison signature est faite par musique.py avant cet appel.

    Args:
        source_pdf    : PDF source (sans boutons)
        target_pdf    : PDF destination (avec boutons)
        sig_actuelle  : signature courante (depuis CSV / STRUCTURE)
    """
    if not target_pdf.exists():
        return True
    return source_pdf.stat().st_mtime > target_pdf.stat().st_mtime

# Fin partition_utils.py v1.9
 
```

Dessine les boutons YouTube (rouge) et Jouer ici (vert) sur la première page des PDF de partitions, à la position spécifiée en % de la page.

### `lib1/structure_utils.py` — STRUCTURE.py

structure_utils_v2.1.py
``` python
# structure_utils.py — Version 2.1
# v2.1 : correction null->None dans sauvegarder_structure (json.dumps ecrit null pour None)

version = ("structure_utils.py", "2.1")
print(f"[Import] {version[0]} - Version {version[1]} charge")

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
    json_str = json_str.replace("true", "True").replace("false", "False").replace("null", "None")
    
    contenu += f"STRUCTURE = {json_str}\n"
    
    # Sauvegarder
    fichier = dossier / "STRUCTURE.py"
    fichier.write_text(contenu, encoding="utf-8")

# Fin structure_utils.py v2.1

```

Lecture, écriture, et valeurs par défaut des fichiers STRUCTURE.py.  
**Important** : v2.1 corrige la conversion `null`→`None` (JSON→Python).

---

## 4. Workflow de génération

```
lancer.cmd
  └── python genere_site.py
        │
        ├── Vider html\ + copier style.css
        │
        ├── initialiser_dossier_musique()   [musique.py]
        │     Crée documents/musique/ si absent
        │
        ├── PHASE 1 : Pour chaque dossier documents\
        │     ├── traiter_docx_du_dossier()   [documents.py]
        │     │     Convertit *.docx → *.pdf (PDFCreator)
        │     │     Gère aussi __partition_*.docx
        │     ├── traiter_partitions_du_dossier()   [musique.py]
        │     │     Lit __correspondance.csv (si plus récent)
        │     │     Ajoute boutons YouTube sur PDF
        │     │     Met à jour clé "partitions" dans STRUCTURE.py
        │     └── mettre_a_jour_structure()   [documents.py]
        │           Enregistre nouveaux fichiers dans STRUCTURE.py
        │
        ├── PHASE 2 : Pour chaque dossier
        │     generer_page_index()   [builder.py]
        │       → index.html (avec entête, pied, navigation)
        │
        └── PHASE 3 :
              generer_tdm()          [cree_table_des_matieres.py]
              copier_fichiers_site() [builder.py]
                → copie PDF, HTML, images vers html\
```

---

## 5. Gestion des partitions musicales

### Principe

Une partition est un fichier Word avec un accompagnement YouTube :

```
__partition_L'auvergnat de Brassens en hébreu.docx
  ↓ conversion (PHASE 1)
__partition_l_auvergnat_de_brassens_en_hebreu.pdf   ← PDF source
  ↓ ajout boutons YouTube (musique.py)
l_auvergnat_de_brassens_en_hebreu.pdf               ← PDF final (publié)
```

Le bouton **YouTube** ouvre la vidéo sur YouTube.  
Le bouton **Jouer ici** ouvre le player intégré au site (`musique/index.html?v=VIDEO_ID`).

### Fichier `__correspondance.csv`

Placé dans le même dossier que les partitions.  
Colonnes (noms flexibles, insensibles à la casse) :

| Colonne attendue | Variantes acceptées | Valeur par défaut |
|------------------|--------------------|--------------------|
| `nom_partition__pdf` | `pdf_name`, `nom_pdf` | — (obligatoire) |
| `youtube_url` | `url`, `youtube` | — (obligatoire) |
| `orientation` | — | `V` (portrait) |
| `transparence` | `fond_transparent`, `fond` | `0` (fond blanc opaque) |
| `position_Horizontale` | `x`, `pos_x` | centré |
| `position_verticale` | `y`, `pos_y` | `2%` (marge basse) |

**Exemple** :
```
nom_partition__pdf,youtube_url,orientation,transparence,position_Horizontale,position_verticale,
__partition_l_auvergnat_de_brassens_en_hebreu.pdf,https://www.youtube.com/watch?v=morcvF-aFsg,H,100,,,
```

### Paramètres de positionnement des boutons

- **orientation** : `V` (portrait) ou `H` (paysage) — information de contexte
- **transparence** : `0` = fond blanc opaque, `100` = fond invisible (float 0–100)
- **x** : % de la largeur depuis la gauche (float, ex: `10.5`) — vide = centré
- **y** : % de la hauteur depuis le bas (float, ex: `2.5`) — vide = 2% (marge basse)

### Stockage dans STRUCTURE.py

Après le premier passage, `musique.py` injecte une clé `"partitions"` dans le STRUCTURE.py du dossier :

```python
"partitions": [
    {
        "nom_docx"        : "__partition_L'auvergnat de Brassens en hébreu.docx",
        "nom_pdf_source"  : "__partition_l_auvergnat_de_brassens_en_hebreu.pdf",
        "nom_html"        : "l_auvergnat_de_brassens_en_hebreu.pdf",
        "nom_affiche"     : "L'auvergnat de Brassens en hébreu",
        "video_id"        : "morcvF-aFsg",
        "orientation"     : "H",
        "fond_opacite_pct": 100.0,
        "x"               : None,
        "y"               : None,
        "params_signature": "morcvF-aFsg|H|100.0|None|None"
    }
]
```

Le CSV n'est relu que si il est **plus récent** que STRUCTURE.py.  
La `params_signature` permet de détecter un changement de paramètres et de forcer la régénération du PDF.

---

## 6. STRUCTURE.py — Clé de voûte

Chaque dossier de `documents\` contient un fichier `STRUCTURE.py`.  
C'est un fichier Python définissant un dictionnaire `STRUCTURE`.

### Clés du dictionnaire

| Clé | Type | Description |
|-----|------|-------------|
| `titre_dossier` | str | Titre affiché (navigation, page) |
| `nom_navigation` | str | Texte dans le fil d'Ariane |
| `titre_table` | str | Titre au-dessus de la liste des fichiers |
| `entete_general` | bool | Inclure `entete_general.html` racine |
| `pied_general` | bool | Inclure `pied_general.html` racine |
| `entete` | bool | Inclure `entete.html` local |
| `pied` | bool | Inclure `pied.html` local |
| `navigation` | bool | Afficher le fil d'Ariane |
| `ajout_affichage` | bool/list | Colonnes supplémentaires dans la table |
| `affiche_index` | bool | Apparaît dans l'index du parent |
| `affiche_TDM` | bool | Apparaît dans la table des matières |
| `dossiers` | list | Sous-dossiers avec leurs paramètres |
| `fichiers` | list | Fichiers avec leurs paramètres |
| `partitions` | list | **Géré par musique.py** — paramètres YouTube |

### Règle de modification manuelle

- Toutes les clés sauf `"partitions"` peuvent être modifiées manuellement.
- `"partitions"` est géré par `musique.py` — ne pas modifier à la main.
- Les nouvelles entrées `fichiers` sont toujours ajoutées à la fin (position croissante).
- `genere_site.py` ne supprime jamais d'entrée existante.

---

## 7. Outils de développement et maintenance

### `versions.py` — Audit des versions

```
(virPy13) C:\SiteGITHUB\Hebreu4.0\prog> python versions.py
```

Lit le tuple `version` de chaque module sans l'importer (lecture AST).  
Affiche un tableau avec statut (✓ présent / ✗ absent), version, description.

### `remplace_v2.cmd` — Déploiement

```
C:\SiteGITHUB\Hebreu4.0\package\prog\remplace_v2.cmd
```

Copie (sans supprimer) les fichiers versionnés depuis `package\prog\` vers `prog\`.  
Appelle `versions.py` en fin de déploiement pour confirmer les versions installées.

### `lancer.cmd` — Génération et serveur local
lancer_v4.0.cmd 
```
@echo off
REM lancer.cmd — Version 4.0
REM Lance la génération du site avec options
echo lancer.cmd version 4.0
setlocal

REM Passer en mode UTF-8
chcp 65001 >nul
REM Génération site
rem vérifier que le dossier courant est bien c:\Sitegithub\Hebreu4.0
echo.
echo ============================================================
echo Generation du site
echo ============================================================
cd prog
python genere_site.py
cd ..
echo ============================================================
echo pour utiliser le style en local
echo alors qu'il est généré pour github
echo ============================================================

md html\Hebreu4.0\html
copy package\html\Hebreu4.0\html\style.css html\Hebreu4.0\html\style.css

echo.
echo ============================================================
echo ===    GENERATION TERMINEE     ===
echo === Démarrage du serveur local ===
echo ============================================================
npx http-server html -p 3500 --cors -c-1 -o "/index.html"
echo.
echo Site disponible dans : localhost:3500/index.html
echo.
:fin
echo lancer.cmd — Version 4.0 achevé
REM lancer.cmd — Version 4.0

```

Lance `genere_site.py` puis démarre `npx http-server` sur le port 3500.  
Copie également `style.css` pour permettre un rendu local fidèle.

---

## 8. Versioning et déploiement

### Convention de nommage des fichiers versionnés

```
<module>_v<majeur>.<mineur>.py
```

Exemples :
- `genere_site_v25.1.py`
- `musique_v1.4.py`
- `structure_utils_v2.1.py`

actuellement :

|  Fichier                 |Version|Description|
|--------------------------|-------|----------------------|
|genere_site.py            |25.1|Generateur principal     |
|settings.py               |1.0 |Configuration            |
|documents.py              |2.0 |Gestion documents/PDF    |
|musique.py                |1.4 |Module musique/partitions|
|builder.py                |1.0 |Generation HTML          |
|docx_to_pdf.py            |1.3 |Conversion DOCX->PDF     |
|lib1/partition_utils.py   |1.9 |Boutons YouTube PDF      |
|lib1/structure_utils.py   |2.1 |Gestion STRUCTURE.py     |
|lib1/html_utils.py        |1.0 |Utilitaires HTML         |
|lib1/fichier_utils.py     |1.0 |Utilitaires fichiers     |
|lib1/pdf_utils.py         |1.1 |Utilitaires PDF          |
|lib1/options.py           |2.0 |Shim options             |
|lib1/config.py            |4.0 |Shim config              |
|cree_table_des_matieres.py|6.29|Table des matieres       |   

### Règles de versioning

- **Mineur** (ex: 1.3 → 1.4) : correction de bug ou ajout de fonctionnalité limitée
- **Majeur** (ex: 1.x → 2.0) : refactorisation significative ou changement d'interface
- Chaque fichier déclare son `version = ("nom.py", "x.y")` et affiche `[Import] nom.py - Version x.y chargé` au chargement

### Dossier `package\prog\`

Contient **toutes les versions** de tous les fichiers depuis le début du projet.  
Ne jamais supprimer — permet de revenir à une version antérieure.

Structure type :
```
package\prog\
  genere_site_v24.0.py       ← ancienne version conservée
  genere_site_v25.0.py
  genere_site_v25.1.py       ← version courante
  musique_v1.0.py
  musique_v1.1.py
  ...
  musique_v1.4.py            ← version courante
  remplace_v2.cmd            ← déploiement actuel
```

### Workflow de modification

1. Copier le fichier courant depuis `prog\` vers `package\prog\` avec le numéro de version
2. Modifier dans `package\prog\` (jamais directement dans `prog\`)
3. Incrémenter la version dans le code
4. Tester : `lancer.cmd`
5. Valider : `python versions.py`
6. Déployer : `remplace_v2.cmd`

---

## 9. Manuel utilisateur

### Ajouter un nouveau document

1. Placer le fichier `.docx` dans le bon sous-dossier de `documents\`
2. Lancer `lancer.cmd`
3. Le PDF est généré automatiquement et l'entrée ajoutée à `STRUCTURE.py`

### Modifier l'ordre d'affichage

Éditer `STRUCTURE.py` du dossier concerné — modifier la clé `"position"` de chaque entrée dans `"fichiers"`.

### Ajouter une partition musicale

1. Nommer le fichier `__partition_Titre exact.docx`
2. Ajouter une ligne dans `__correspondance.csv` :
   ```
   nom_partition__pdf,youtube_url,orientation,transparence,position_Horizontale,position_verticale,
   __partition_titre_exact.pdf,https://www.youtube.com/watch?v=XXXX,H,0,,2,
   ```
3. Lancer `lancer.cmd`

### Ajuster la position des boutons YouTube

Modifier les colonnes `position_Horizontale` (x%) et `position_verticale` (y%) dans `__correspondance.csv`.  
Supprimer le PDF final (ex: `l_auvergnat.pdf`) pour forcer la régénération, ou modifier le CSV — la détection par `params_signature` régénère automatiquement.

### Forcer la régénération de tous les PDF

Dans `settings.py`, mettre `"regeneration": True`.  
Remettre à `False` après.

### Personnaliser une page

Créer ou modifier `entete.html` et/ou `pied.html` dans le dossier concerné.

---

## 10. Référence CSV partitions

Fichier : `__correspondance.csv`  
Encodage : UTF-8  
Séparateur : virgule `,`

```
nom_partition__pdf,youtube_url,orientation,transparence,position_Horizontale,position_verticale,
__partition_l_auvergnat.pdf,https://www.youtube.com/watch?v=XXX,H,0,,,
__partition_hatikva.pdf,https://www.youtube.com/watch?v=YYY,V,50,10,5,
```

La virgule finale (7e colonne vide) est acceptée et ignorée.

### Valeurs orientation

| Valeur | Variantes acceptées | Résultat |
|--------|--------------------|----|
| `V` | `PORTRAIT`, `P` | Portrait |
| `H` | `LANDSCAPE`, `L`, `PAYSAGE` | Paysage |

### Valeurs transparence

| Valeur | Effet |
|--------|-------|
| `0` | Fond blanc opaque (défaut recommandé sur texte) |
| `50` | Fond semi-transparent |
| `100` | Aucun fond (boutons flottent sur la page) |

---

*Document généré avec le projet — à mettre à jour à chaque version majeure.*
