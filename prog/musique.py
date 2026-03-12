# musique_v1.13.py — Version 1.13
# v1.13: traceback complet sur erreur bouton pour diagnostic
# v1.12: utilise normalisation_utils.py
#        suppression de _normaliser_fichier() interne
#        normaliser_nom() est desormais la seule regle de normalisation
# v1.11: logique complete des 4 cas
# v1.10: normaliser_nom identique a genere_site.py
# v1.9 : dossier_html normalise, bouton haut-gauche par defaut
# v1.8 : refactorisation complete

import csv
import shutil
from pathlib import Path
from typing import List, Dict, Optional

version = ("musique.py", "1.13")
print(f"[Import] {version[0]} - Version {version[1]} charge")

import traceback as _traceback

from lib1 import structure_utils as struct
from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG

# Import normalisation_utils depuis le meme dossier que musique.py
import importlib.util as _ilu

def _charger_module(nom_fichier, nom_module):
    p = Path(__file__).parent / nom_fichier
    if not p.exists():
        raise FileNotFoundError(f"{nom_fichier} introuvable dans {Path(__file__).parent}")
    spec = _ilu.spec_from_file_location(nom_module, p)
    mod  = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_norm = _charger_module("normalisation_utils.py", "normalisation_utils")
_pbp  = _charger_module("place_bouton.py",         "place_bouton")
print(f"  [musique] place_bouton.py v{_pbp.version[1]} charge")

NOM_DOSSIER_MUSIQUE = "musique"

# Detection bibliotheques PDF
try:
    import pypdf     # noqa
    import reportlab # noqa
    HAS_PDF_LIBS = True
    print(f"  [musique] pypdf + reportlab disponibles")
except ImportError:
    HAS_PDF_LIBS = False
    print(f"  [musique] WARNING pypdf ou reportlab manquant")

# Valeurs par defaut CSV
DEF_TRANSPARENCE   = 100
DEF_POS_X          = 0.0
DEF_POS_Y_SENTINEL = -1.0
DEF_ROTATION       = "E"
DEF_ORIENT         = "2"
DEF_LARGEUR        = 160
DEF_HAUTEUR        = 35


# ─────────────────────────────────────────────────────────────────────
# NORMALISATION  (deleguee a normalisation_utils)
# ─────────────────────────────────────────────────────────────────────
def _nom_pdf(nom_fichier: str) -> str:
    """Nom PDF normalise depuis n'importe quel fichier source."""
    return _norm.nom_pdf_depuis_source(nom_fichier)

def _norm_chemin(chemin_relatif) -> Path:
    """Normalise chaque segment d'un chemin relatif."""
    return _norm.normaliser_chemin(chemin_relatif)


# ─────────────────────────────────────────────────────────────────────
# COMPATIBILITE documents.py
# ─────────────────────────────────────────────────────────────────────
def nom_partition_depuis_docx(nom_docx: str):
    """Retourne (nom_lisible, nom_html) depuis un fichier DOCX."""
    stem = Path(nom_docx).stem
    return (stem, _nom_pdf(nom_docx))


# ─────────────────────────────────────────────────────────────────────
# HELPERS CSV
# ─────────────────────────────────────────────────────────────────────
def _get(row: dict, *cles, defaut=None):
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
def lire_csv(csv_path: Path, log_func) -> Dict[str, dict]:
    """
    Lit __correspondance.csv (separateur ;).
    Cle du dict = nom PDF normalise du fichier source (nom_pdf_depuis_source).
    Ex : 'b A.pdf'  -> cle 'b_a.pdf'
         'a_c.pdf'  -> cle 'a_c.pdf'
         'A A.docx' -> cle 'a_a.pdf'
    """
    if not csv_path.exists():
        return {}
    resultats = {}
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for i, row in enumerate(reader):
                nom_csv = _get(row, "nom_partition__pdf", "nom_partition", "nom")
                url     = _get(row, "youtube_url", "url", "youtube")
                if not nom_csv or not url:
                    continue

                cle = _nom_pdf(nom_csv)
                params = {
                    "nom_csv"      : nom_csv.strip(),
                    "youtube_url"  : url.strip(),
                    "transparence" : _int(  _get(row, "transparence"),                DEF_TRANSPARENCE),
                    "pos_x"        : _float(_get(row, "position_horizontale",
                                                 "pos_x", "x"),                       DEF_POS_X),
                    "pos_y"        : _float(_get(row, "position_verticale",
                                                 "pos_y", "y"),                       DEF_POS_Y_SENTINEL),
                    "rotation"     : _get(row, "rotation",         defaut=DEF_ROTATION),
                    "orient_texte" : _get(row, "orientation_texte",
                                          "orient",                defaut=DEF_ORIENT),
                    "largeur"      : _int(  _get(row, "largeur", "width"),             DEF_LARGEUR),
                    "hauteur"      : _int(  _get(row, "hauteur", "height"),            DEF_HAUTEUR),
                }
                try:    _pbp.parse_rotation(params["rotation"])
                except ValueError:
                    log_func(f"  CSV ligne {i+2} : rotation invalide -> {DEF_ROTATION}")
                    params["rotation"] = DEF_ROTATION
                try:    _pbp.parse_orient(params["orient_texte"])
                except ValueError:
                    log_func(f"  CSV ligne {i+2} : orient invalide -> {DEF_ORIENT}")
                    params["orient_texte"] = DEF_ORIENT

                log_func(f"  CSV : {nom_csv!r} -> cle={cle!r}")
                resultats[cle] = params
    except Exception as e:
        log_func(f"  ERREUR lecture CSV : {e}")

    log_func(f"  CSV : {len(resultats)} entree(s)")
    return resultats


# ─────────────────────────────────────────────────────────────────────
# TRAITEMENT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────
def traiter_partitions_du_dossier(dossier: Path, log_func) -> int:
    """
    Traite tous les PDF du dossier. Pour chaque PDF :
      PDF dans CSV  -> bouton YouTube ajoute -> html/ (nom normalise)
      PDF hors CSV  -> copie directe         -> html/ (nom normalise)
    Met a jour STRUCTURE.py. Retourne le nombre de PDFs traites.
    """
    # Dossier HTML cible
    try:
        chemin_rel   = dossier.relative_to(Path(DOSSIER_DOCUMENTS))
        dossier_html = Path(DOSSIER_HTML) / _norm_chemin(chemin_rel)
    except ValueError:
        dossier_html = Path(str(dossier).replace(
            str(DOSSIER_DOCUMENTS), str(DOSSIER_HTML), 1))

    dossier_html.mkdir(parents=True, exist_ok=True)
    log_func(f"  Dossier source : {dossier}")
    log_func(f"  Dossier cible  : {dossier_html}")

    # CSV
    csv_path = dossier / "__correspondance.csv"
    csv_data = lire_csv(csv_path, log_func) if csv_path.exists() else {}

    # Liste des PDF
    pdfs = sorted(
        f for f in dossier.iterdir()
        if f.is_file()
        and f.suffix.lower() == ".pdf"
        and not f.name.lower().startswith("__correspondance")
    )
    if not pdfs:
        log_func("  Aucun PDF dans le dossier")
        return 0

    # STRUCTURE.py existant
    try:
        structure_exist  = struct.charger_structure(dossier)
        partitions_exist = {
            p["nom_document"]: p
            for p in structure_exist.get("partitions", [])
            if "nom_document" in p
        }
    except Exception:
        structure_exist  = {}
        partitions_exist = {}

    nb = 0
    partitions_structure = []

    for pdf_source in pdfs:
        nom_src   = pdf_source.name
        nom_dst   = _nom_pdf(nom_src)
        pdf_cible = dossier_html / nom_dst

        # DOCX associe -> nom_document prioritaire
        nom_docx     = _trouver_docx(dossier, Path(nom_src).stem)
        nom_document = nom_docx if nom_docx else nom_src

        # Cle CSV = nom normalise du PDF source
        cle_csv  = _nom_pdf(nom_src)
        dans_csv = cle_csv in csv_data

        if dans_csv and HAS_PDF_LIBS:
            p = csv_data[cle_csv]
            log_func(f"  [BOUTON] {nom_src!r} -> {nom_dst!r}  (CSV: {p['nom_csv']!r})")
            try:
                angle_rot   = _pbp.parse_rotation(p["rotation"])
                vertical, _ = _pbp.parse_orient(p["orient_texte"])

                pos_x = p["pos_x"]
                pos_y = p["pos_y"]
                if pos_y == DEF_POS_Y_SENTINEL:
                    from pypdf import PdfReader as _PR
                    ph    = float(_PR(str(pdf_source)).pages[0].mediabox.height)
                    pos_y = ph - p["hauteur"]
                    log_func(f"         pos_y auto : {ph:.0f} - {p['hauteur']} = {pos_y:.0f}")

                log_func(f"         python place_bouton.py"
                         f" \"{dossier}\" \"{nom_src}\""
                         f" \"{dossier_html}\" \"{nom_dst}\""
                         f" \"{p['youtube_url']}\""
                         f" {p['transparence']} {pos_x} {pos_y}"
                         f" {p['rotation']} {p['orient_texte']}"
                         f" {p['largeur']} {p['hauteur']}")

                _pbp.placer_bouton(
                    fichier_src    = pdf_source,
                    fichier_dst    = pdf_cible,
                    youtube_url    = p["youtube_url"],
                    transparence   = p["transparence"],
                    pos_x          = pos_x,
                    pos_y          = pos_y,
                    angle_rot      = angle_rot,
                    texte_vertical = vertical,
                    largeur        = p["largeur"],
                    hauteur        = p["hauteur"],
                )
                nb += 1
                youtube_url = p["youtube_url"]
                avec_bouton = True

            except Exception as e:
                log_func(f"  ERREUR bouton {nom_src!r} : {e}")
                log_func(_traceback.format_exc())
                shutil.copy2(str(pdf_source), str(pdf_cible))
                log_func(f"         -> copie simple (fallback)")
                nb += 1
                youtube_url = p["youtube_url"]
                avec_bouton = False

        elif dans_csv and not HAS_PDF_LIBS:
            log_func(f"  [COPIE ] {nom_src!r} -> {nom_dst!r}  (libs manquantes)")
            shutil.copy2(str(pdf_source), str(pdf_cible))
            nb += 1
            youtube_url = csv_data[cle_csv]["youtube_url"]
            avec_bouton = False

        else:
            log_func(f"  [COPIE ] {nom_src!r} -> {nom_dst!r}  (hors CSV)")
            shutil.copy2(str(pdf_source), str(pdf_cible))
            nb += 1
            youtube_url = None
            avec_bouton = False

        # Entree STRUCTURE.py
        if nom_document in partitions_exist:
            entree = partitions_exist[nom_document]
            entree["nom_html"]    = nom_dst
            entree["youtube_url"] = youtube_url
            entree["avec_bouton"] = avec_bouton
        else:
            entree = {
                "nom_document": nom_document,
                "nom_html"    : nom_dst,
                "nom_affiche" : "{{nom_document_sans_ext}}",
                "nom_TDM"     : "{{nom_document_sans_ext}}",
                "youtube_url" : youtube_url,
                "avec_bouton" : avec_bouton,
            }
        partitions_structure.append(entree)

    _mettre_a_jour_structure(dossier, structure_exist, partitions_structure, log_func)
    log_func(f"  {nb} PDF traite(s)  "
             f"({sum(1 for p in partitions_structure if p['avec_bouton'])} avec bouton)")
    return nb


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def _trouver_docx(dossier: Path, stem_pdf: str) -> Optional[str]:
    """
    Cherche un DOCX dont le stem normalise correspond au stem normalise du PDF.
    Retourne le nom ORIGINAL du DOCX ou None.
    """
    cible = _norm.normaliser_nom(stem_pdf)
    for f in dossier.iterdir():
        if f.is_file() and f.suffix.lower() in ('.doc', '.docx'):
            if _norm.normaliser_nom(f.stem) == cible:
                return f.name
    return None


def _mettre_a_jour_structure(dossier, structure_exist, partitions, log_func):
    try:
        structure_exist["partitions"] = partitions
        struct.sauvegarder_structure(dossier, structure_exist)
        log_func(f"  STRUCTURE.py : {len(partitions)} entree(s)")
    except Exception as e:
        log_func(f"  ERREUR STRUCTURE.py : {e}")


def initialiser_dossier_musique(log_func) -> Path:
    dossier = Path(DOSSIER_HTML) / NOM_DOSSIER_MUSIQUE
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier

# Fin musique.py v1.12
