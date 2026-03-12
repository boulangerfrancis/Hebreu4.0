# musique.py — Version 1.8
# v1.8 : refactorisation complete
#   - partition_utils supprime, remplace par Place_Bouton_PDF
#   - CSV separateur ; avec rubriques simplifiees
#   - plus de signature/hash : le PDF cible est TOUJOURS recree
#     (source dans documents/ jamais modifiee, cible dans html/ recreee a chaque build)
#   - plus de player local : bouton ouvre YouTube directement
#   - parametres CSV : nom_partition__pdf;youtube_url;transparence;
#                      position_Horizontale;position_verticale;
#                      rotation;orientation_texte;largeur;hauteur

"""
Workflow :
  1. Chercher __correspondance.csv dans le dossier documents/musique/
  2. Pour chaque ligne CSV :
     a. PDF source = dossier_documents / nom_partition__pdf
     b. PDF cible  = dossier_html      / nom_partition__pdf  (sans __)
     c. Appeler Place_Bouton_PDF.placer_bouton()
  3. Mettre a jour STRUCTURE.py avec la liste des partitions (pour le HTML)

Structure "partitions" dans STRUCTURE.py :
    "partitions": [
        {
            "nom_pdf"    : "l_auvergnat.pdf",    # nom dans html/ (sans __)
            "nom_affiche": "l_auvergnat",
            "youtube_url": "https://www.youtube.com/watch?v=morcvF-aFsg",
        }
    ]
"""

import csv
import unicodedata
import re
from pathlib import Path
from typing import List, Dict, Optional

version = ("musique.py", "1.8")
print(f"[Import] {version[0]} - Version {version[1]} charge")

from lib1 import structure_utils as struct
from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG

# Import Place_Bouton_PDF depuis le meme dossier que musique.py
import importlib.util, sys as _sys
_pbp_path = Path(__file__).parent / "Place_Bouton_PDF.py"
_spec = importlib.util.spec_from_file_location("Place_Bouton_PDF", _pbp_path)
_pbp  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pbp)

NOM_DOSSIER_MUSIQUE = "musique"

# Detection bibliotheques PDF (pour compatibilite avec genere_site.py)
try:
    import pypdf     # noqa
    import reportlab # noqa
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False

if HAS_PDF_LIBS:
    print(f"  [musique] pypdf + reportlab disponibles")
else:
    print(f"  [musique] ⚠ pypdf ou reportlab manquant — boutons desactives")

# Valeurs par defaut si colonne absente ou vide dans le CSV
DEF_TRANSPARENCE = 100
DEF_POS_X        = 0.0
DEF_POS_Y        = 0.0
DEF_ROTATION     = "E"
DEF_ORIENT       = "2"
DEF_LARGEUR      = 160
DEF_HAUTEUR      = 35


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def _normaliser(texte: str) -> str:
    """Normalise un nom de fichier : minuscules, sans accents, espaces->_."""
    t = unicodedata.normalize("NFD", texte)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower().replace(" ", "_")
    t = re.sub(r"[^\w]", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def nom_partition_depuis_docx(nom_docx: str):
    """Calcule (nom_lisible, nom_html) depuis __partition_*.docx.
    Conservee pour compatibilite avec documents.py."""
    sans_prefix = nom_docx
    for prefix in ("__partition_", "__partition _"):
        if nom_docx.lower().startswith(prefix.lower()):
            sans_prefix = nom_docx[len(prefix):]
            break
    stem        = Path(sans_prefix).stem
    nom_lisible = stem
    nom_html    = _normaliser(stem) + ".pdf"
    return (nom_lisible, nom_html)


def _nom_html(nom_pdf_source: str) -> str:
    """
    Calcule le nom du PDF dans html/ depuis le nom source.
    '__partition_l_auvergnat.pdf' -> 'l_auvergnat.pdf'
    Supprime le prefixe '__partition_' ou '__partition _'.
    """
    n = Path(nom_pdf_source).name
    for prefix in ("__partition_", "__partition _", "__partition"):
        if n.lower().startswith(prefix):
            n = n[len(prefix):]
            break
    return _normaliser(Path(n).stem) + ".pdf"


def _get(row: dict, *cles, defaut=None):
    """Lit la premiere cle trouvee dans un dict CSV, retourne defaut si vide."""
    for cle in cles:
        for k in row:
            if k.strip().lower() == cle.lower():
                v = row[k].strip()
                return v if v else defaut
    return defaut


def _int(val, defaut):
    try:    return int(val)
    except: return defaut


def _float(val, defaut):
    try:    return float(val)
    except: return defaut


# ─────────────────────────────────────────────────────────────────────
# LECTURE CSV
# ─────────────────────────────────────────────────────────────────────
def lire_csv(csv_path: Path, log_func) -> List[dict]:
    """
    Lit __correspondance.csv (separateur ;).
    Retourne une liste de dicts avec tous les parametres normalises.

    Colonnes attendues (toutes optionnelles sauf les 2 premieres) :
      nom_partition__pdf ; youtube_url ; transparence ;
      position_Horizontale ; position_verticale ;
      rotation ; orientation_texte ; largeur ; hauteur
    """
    if not csv_path.exists():
        return []

    resultats = []
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for i, row in enumerate(reader):
                nom_pdf = _get(row, "nom_partition__pdf", "nom_partition", "nom")
                url     = _get(row, "youtube_url", "url", "youtube")
                if not nom_pdf or not url:
                    continue

                params = {
                    "nom_pdf_source"  : nom_pdf.strip(),
                    "youtube_url"     : url.strip(),
                    "transparence"    : _int(  _get(row, "transparence"),                   DEF_TRANSPARENCE),
                    "pos_x"           : _float(_get(row, "position_horizontale", "pos_x",
                                                    "position_h", "x"),                     DEF_POS_X),
                    "pos_y"           : _float(_get(row, "position_verticale",   "pos_y",
                                                    "position_v", "y"),                     DEF_POS_Y),
                    "rotation"        : _get(row, "rotation",          defaut=DEF_ROTATION),
                    "orient_texte"    : _get(row, "orientation_texte", "orient",
                                             "orientation_texte",      defaut=DEF_ORIENT),
                    "largeur"         : _int(  _get(row, "largeur", "l", "width"),          DEF_LARGEUR),
                    "hauteur"         : _int(  _get(row, "hauteur", "h", "height"),         DEF_HAUTEUR),
                }

                # Valider rotation et orient_texte
                try:
                    _pbp.parse_rotation(params["rotation"])
                except ValueError:
                    log_func(f"  ⚠ CSV ligne {i+2} : rotation invalide "
                             f"{params['rotation']!r} -> E par defaut")
                    params["rotation"] = DEF_ROTATION

                try:
                    _pbp.parse_orient(params["orient_texte"])
                except ValueError:
                    log_func(f"  ⚠ CSV ligne {i+2} : orientation_texte invalide "
                             f"{params['orient_texte']!r} -> 2 par defaut")
                    params["orient_texte"] = DEF_ORIENT

                log_func(f"  [CSV] {nom_pdf}")
                log_func(f"        url={url}")
                log_func(f"        transp={params['transparence']}%  "
                         f"x={params['pos_x']}  y={params['pos_y']}  "
                         f"rot={params['rotation']}  orient={params['orient_texte']}  "
                         f"taille={params['largeur']}x{params['hauteur']}")

                resultats.append(params)

    except Exception as e:
        log_func(f"  ⚠ Erreur lecture CSV : {e}")

    return resultats


# ─────────────────────────────────────────────────────────────────────
# TRAITEMENT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────
def traiter_partitions_du_dossier(dossier: Path, log_func) -> int:
    """
    Ajoute les boutons YouTube sur les PDFs du dossier.

    Pour chaque ligne du CSV :
      - source : dossier          / nom_partition__pdf   (jamais modifie)
      - cible  : dossier_html/... / nom_html             (ecrase a chaque build)

    Retourne le nombre de PDFs traites.
    """
    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        log_func(f"  Pas de CSV : {csv_path.name}")
        return 0

    if not HAS_PDF_LIBS:
        log_func("  ⚠ pypdf/reportlab manquants — boutons ignores")
        return 0

    log_func(f"  Lecture CSV : {csv_path}")
    lignes = lire_csv(csv_path, log_func)
    if not lignes:
        log_func("  CSV vide ou sans lignes valides")
        return 0

    # Dossier HTML cible (meme structure que documents/)
    # dossier = .../documents/musique  -> cible = .../html/musique
    dossier_html = Path(str(dossier).replace(
        str(DOSSIER_DOCUMENTS), str(DOSSIER_HTML), 1))
    dossier_html.mkdir(parents=True, exist_ok=True)

    nb = 0
    partitions_structure = []

    for p in lignes:
        nom_src = p["nom_pdf_source"]
        nom_dst = _nom_html(nom_src)

        pdf_source = dossier / nom_src
        pdf_cible  = dossier_html / nom_dst

        if not pdf_source.exists():
            log_func(f"  ⚠ PDF source introuvable : {pdf_source}")
            continue

        log_func(f"  [PDF] {nom_src} -> {nom_dst}")

        try:
            angle_rot      = _pbp.parse_rotation(p["rotation"])
            vertical, _    = _pbp.parse_orient(p["orient_texte"])

            _pbp.placer_bouton(
                fichier_src     = pdf_source,
                fichier_dst     = pdf_cible,
                youtube_url     = p["youtube_url"],
                transparence    = p["transparence"],
                pos_x           = p["pos_x"],
                pos_y           = p["pos_y"],
                angle_rot       = angle_rot,
                texte_vertical  = vertical,
                largeur         = p["largeur"],
                hauteur         = p["hauteur"],
            )
            nb += 1
            log_func(f"      => OK : {pdf_cible.name}")

        except Exception as e:
            log_func(f"  ⚠ Erreur traitement {nom_src} : {e}")
            continue

        # Entree pour STRUCTURE.py
        partitions_structure.append({
            "nom_pdf"     : nom_dst,
            "nom_affiche" : Path(nom_dst).stem.replace("_", " ").title(),
            "youtube_url" : p["youtube_url"],
        })

    # Mettre a jour STRUCTURE.py avec la liste des partitions
    if partitions_structure:
        _mettre_a_jour_structure(dossier, partitions_structure, log_func)

    log_func(f"  {nb} partition(s) traitee(s)")
    return nb


def _mettre_a_jour_structure(dossier: Path, partitions: List[dict],
                              log_func) -> None:
    """Met a jour la cle 'partitions' dans STRUCTURE.py du dossier."""
    try:
        structure = struct.charger_structure(dossier)
        structure["partitions"] = partitions
        struct.sauvegarder_structure(dossier, structure)
        log_func(f"  STRUCTURE.py : {len(partitions)} partition(s) enregistree(s)")
    except Exception as e:
        log_func(f"  ⚠ Erreur mise a jour STRUCTURE.py : {e}")


# ─────────────────────────────────────────────────────────────────────
# TEMPLATES HTML (inchanges depuis v1.7)
# ─────────────────────────────────────────────────────────────────────
def _template_entete_general() -> str:
    return ""

def _template_structure_musique() -> str:
    return ""

def initialiser_dossier_musique(log_func) -> Path:
    """Cree le dossier html/musique si necessaire."""
    dossier = Path(DOSSIER_HTML) / NOM_DOSSIER_MUSIQUE
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier

# Fin musique.py v1.8
