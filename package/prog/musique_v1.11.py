# musique_v1.11.py — Version 1.11
# v1.11: logique complete des 4 cas documentee et implementee
#   Cas 1 : DOCX converti par documents.py -> PDF normalise dans documents\
#            PDF normalise dans CSV -> bouton -> html/
#            STRUCTURE.py : nom_document = nom DOCX original
#   Cas 2 : PDF pas dans CSV -> copie renommee (normalise) dans html/
#            STRUCTURE.py : nom_document = nom PDF original
#   Cas 3 : PDF (nom non normalise) dans CSV (cle = nom normalise)
#            -> bouton -> html/
#            STRUCTURE.py : nom_document = nom PDF original
#   Cas 4 : PDF (nom deja normalise) dans CSV
#            -> bouton -> html/
#            STRUCTURE.py : nom_document = nom PDF original
#   Cle CSV = nom normalise du fichier source
# v1.10: normaliser_nom identique a genere_site.py, tous les PDF traites
# v1.9 : dossier_html normalise, bouton haut-gauche par defaut
# v1.8 : refactorisation complete

import csv
import shutil
import unicodedata
import re
from pathlib import Path
from typing import List, Dict, Optional

version = ("musique.py", "1.11")
print(f"[Import] {version[0]} - Version {version[1]} charge")

from lib1 import structure_utils as struct
from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG

# Import place_bouton depuis le meme dossier que musique.py
import importlib.util
_pbp_path = Path(__file__).parent / "place_bouton.py"
if not _pbp_path.exists():
    raise FileNotFoundError(
        f"place_bouton.py introuvable dans {Path(__file__).parent}"
    )
_spec = importlib.util.spec_from_file_location("place_bouton", _pbp_path)
_pbp  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pbp)
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
DEF_POS_Y_SENTINEL = -1.0   # pos_y calculee automatiquement (haut de page)
DEF_ROTATION       = "E"
DEF_ORIENT         = "2"
DEF_LARGEUR        = 160
DEF_HAUTEUR        = 35


# ─────────────────────────────────────────────────────────────────────
# NORMALISATION
# identique a genere_site.normaliser_nom pour les segments de dossier
# ─────────────────────────────────────────────────────────────────────
def normaliser_nom(nom: str) -> str:
    """Normalise un segment de chemin — identique a genere_site.normaliser_nom."""
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.replace("'", "_").replace("\u2019", "_")
    nom = nom.replace(" ", "_")
    return nom.lower()


def _normaliser_fichier(texte: str) -> str:
    """
    Normalise un nom de FICHIER PDF.
    Supprime accents, espaces, et tout caractere non alphanumerique/underscore.
    Ex: 'A b' -> 'a_b'  |  'b A' -> 'b_a'  |  'a_c' -> 'a_c'
    """
    t = normaliser_nom(texte)              # minuscules, sans accents, espaces->_
    t = re.sub(r"[^\w]", "_", t)          # non-alphanum -> _
    t = re.sub(r"_+", "_", t).strip("_")  # doublons et bords
    return t


def _nom_normalise_pdf(nom_fichier: str) -> str:
    """
    Calcule le nom normalise d'un PDF depuis n'importe quel fichier source.
    Ignore le prefixe __partition_ si present.
    Ex: 'A A.docx'  -> 'a_a.pdf'
        'A b.pdf'   -> 'a_b.pdf'
        'b A.pdf'   -> 'b_a.pdf'
        'a_c.pdf'   -> 'a_c.pdf'
    """
    stem = Path(nom_fichier).stem
    # Supprimer prefixe __partition_ si present
    for prefix in ("__partition_", "__partition _", "__partition"):
        if stem.lower().startswith(prefix):
            stem = stem[len(prefix):]
            break
    return _normaliser_fichier(stem) + ".pdf"


def nom_partition_depuis_docx(nom_docx: str):
    """Compatibilite avec documents.py."""
    stem        = Path(nom_docx).stem
    for prefix in ("__partition_", "__partition _"):
        if stem.lower().startswith(prefix.lower()):
            stem = stem[len(prefix):]
            break
    return (stem, _normaliser_fichier(stem) + ".pdf")


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
# La cle dans le dict retourne = nom NORMALISE du fichier source
# ─────────────────────────────────────────────────────────────────────
def lire_csv(csv_path: Path, log_func) -> Dict[str, dict]:
    """
    Lit __correspondance.csv (separateur ;).

    La colonne nom_partition__pdf contient le nom tel qu'ecrit dans documents\
    (avec ou sans accents, espaces). La cle du dict retourne est le nom
    NORMALISE pour permettre la correspondance insensible a la casse/accents.

    Ex CSV : 'b A.pdf' -> cle = 'b_a.pdf'
             'a_a.pdf' -> cle = 'a_a.pdf'
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

                # Cle = nom normalise du fichier source
                cle = _nom_normalise_pdf(nom_csv)

                params = {
                    "nom_csv"         : nom_csv.strip(),  # nom original dans le CSV
                    "youtube_url"     : url.strip(),
                    "transparence"    : _int(  _get(row, "transparence"),           DEF_TRANSPARENCE),
                    "pos_x"           : _float(_get(row, "position_horizontale",
                                                    "pos_x", "x"),                  DEF_POS_X),
                    "pos_y"           : _float(_get(row, "position_verticale",
                                                    "pos_y", "y"),                  DEF_POS_Y_SENTINEL),
                    "rotation"        : _get(row, "rotation",          defaut=DEF_ROTATION),
                    "orient_texte"    : _get(row, "orientation_texte",
                                             "orient",                 defaut=DEF_ORIENT),
                    "largeur"         : _int(  _get(row, "largeur", "width"),       DEF_LARGEUR),
                    "hauteur"         : _int(  _get(row, "hauteur", "height"),      DEF_HAUTEUR),
                }

                # Valider rotation et orient
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

    Cas 1 : PDF genere depuis DOCX par documents.py (nom normalise)
            + entree CSV avec meme cle -> bouton -> html/
            STRUCTURE.py : nom_document = nom DOCX original

    Cas 2 : PDF non normalise, PAS dans CSV
            -> copie renommee (nom normalise) -> html/
            STRUCTURE.py : nom_document = nom PDF original

    Cas 3 : PDF non normalise, dans CSV (cle = nom normalise)
            -> bouton -> html/ (nom normalise)
            STRUCTURE.py : nom_document = nom PDF original

    Cas 4 : PDF deja normalise, dans CSV
            -> bouton -> html/ (meme nom)
            STRUCTURE.py : nom_document = nom PDF original

    Retourne le nombre de PDFs traites.
    """
    # Dossier HTML cible avec normalisation identique a genere_site.py
    try:
        chemin_rel          = dossier.relative_to(Path(DOSSIER_DOCUMENTS))
        segments_normalises = [normaliser_nom(s) for s in chemin_rel.parts]
        dossier_html        = Path(DOSSIER_HTML).joinpath(*segments_normalises)
    except ValueError:
        dossier_html = Path(str(dossier).replace(
            str(DOSSIER_DOCUMENTS), str(DOSSIER_HTML), 1))

    dossier_html.mkdir(parents=True, exist_ok=True)
    log_func(f"  Dossier source : {dossier}")
    log_func(f"  Dossier cible  : {dossier_html}")

    # Lire CSV
    csv_path = dossier / "__correspondance.csv"
    csv_data = lire_csv(csv_path, log_func) if csv_path.exists() else {}

    # Lister tous les PDF du dossier
    pdfs = sorted(
        f for f in dossier.iterdir()
        if f.is_file()
        and f.suffix.lower() == ".pdf"
        and not f.name.lower().startswith("__correspondance")
    )

    if not pdfs:
        log_func("  Aucun PDF dans le dossier")
        return 0

    # Charger STRUCTURE.py existant pour ne pas ecraser les items manuels
    try:
        structure_existante = struct.charger_structure(dossier)
        partitions_exist    = {
            p["nom_document"]: p
            for p in structure_existante.get("partitions", [])
            if "nom_document" in p
        }
    except Exception:
        structure_existante = {}
        partitions_exist    = {}

    nb = 0
    partitions_structure = []

    for pdf_source in pdfs:
        nom_src     = pdf_source.name           # ex: 'b A.pdf', 'a_a.pdf'
        nom_dst     = _nom_normalise_pdf(nom_src)  # ex: 'b_a.pdf', 'a_a.pdf'
        pdf_cible   = dossier_html / nom_dst

        # Chercher DOCX associe (meme stem normalise)
        nom_docx = _trouver_docx(dossier, Path(nom_src).stem)

        # nom_document = DOCX en priorite, sinon PDF original
        nom_document = nom_docx if nom_docx else nom_src

        # Cle CSV = nom normalise du PDF source
        cle_csv = _nom_normalise_pdf(nom_src)

        dans_csv = cle_csv in csv_data

        if dans_csv and HAS_PDF_LIBS:
            # CAS 1, 3, 4 : ajouter bouton YouTube
            p = csv_data[cle_csv]
            log_func(f"  [BOUTON] {nom_src!r} -> {nom_dst!r}"
                     f"  (CSV: {p['nom_csv']!r})")

            try:
                angle_rot   = _pbp.parse_rotation(p["rotation"])
                vertical, _ = _pbp.parse_orient(p["orient_texte"])

                # pos_y auto : haut de page
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
                shutil.copy2(str(pdf_source), str(pdf_cible))
                log_func(f"         -> copie simple (fallback erreur)")
                nb += 1
                youtube_url = p["youtube_url"]
                avec_bouton = False

        elif dans_csv and not HAS_PDF_LIBS:
            # CSV mais libs manquantes -> copie simple
            log_func(f"  [COPIE ] {nom_src!r} -> {nom_dst!r}  (pypdf manquant)")
            shutil.copy2(str(pdf_source), str(pdf_cible))
            nb += 1
            youtube_url = csv_data[cle_csv]["youtube_url"]
            avec_bouton = False

        else:
            # CAS 2 : pas dans CSV -> copie directe renommee
            log_func(f"  [COPIE ] {nom_src!r} -> {nom_dst!r}  (hors CSV)")
            shutil.copy2(str(pdf_source), str(pdf_cible))
            nb += 1
            youtube_url = None
            avec_bouton = False

        # Construire l'entree STRUCTURE.py
        # Conserver l'entree existante si presente, sinon creer
        if nom_document in partitions_exist:
            entree = partitions_exist[nom_document]
            # Mettre a jour les champs techniques
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

    # Sauvegarder STRUCTURE.py
    _mettre_a_jour_structure(dossier, structure_existante,
                             partitions_structure, log_func)
    log_func(f"  {nb} PDF traite(s)  "
             f"({sum(1 for p in partitions_structure if p['avec_bouton'])} avec bouton)")
    return nb


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def _trouver_docx(dossier: Path, stem_pdf: str) -> Optional[str]:
    """
    Cherche un DOCX dont le stem normalise correspond au stem normalise du PDF.
    Retourne le nom ORIGINAL du DOCX (avec accents/espaces/casse) ou None.
    Ex: stem_pdf='A A' -> cherche DOCX dont normalise(stem)='a_a' -> 'A A.docx'
    """
    cible = _normaliser_fichier(stem_pdf)
    for f in dossier.iterdir():
        if f.is_file() and f.suffix.lower() in ('.doc', '.docx'):
            if _normaliser_fichier(f.stem) == cible:
                return f.name
    return None


def _mettre_a_jour_structure(dossier: Path, structure_existante: dict,
                              partitions: List[dict], log_func) -> None:
    """Met a jour la cle 'partitions' dans STRUCTURE.py sans ecraser le reste."""
    try:
        structure_existante["partitions"] = partitions
        struct.sauvegarder_structure(dossier, structure_existante)
        log_func(f"  STRUCTURE.py : {len(partitions)} entree(s)")
    except Exception as e:
        log_func(f"  ERREUR STRUCTURE.py : {e}")


def initialiser_dossier_musique(log_func) -> Path:
    dossier = Path(DOSSIER_HTML) / NOM_DOSSIER_MUSIQUE
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier

# Fin musique.py v1.11
