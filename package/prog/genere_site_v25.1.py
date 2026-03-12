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
