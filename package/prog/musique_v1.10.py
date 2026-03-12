# musique_v1.10.py — Version 1.10
# v1.10: normaliser_nom identique a genere_site.py
#        gestion complete du dossier : tous les PDF traites
#        - PDF dans CSV     -> bouton ajoute -> html\ + STRUCTURE.py
#        - PDF hors CSV     -> copie directe -> html\ + STRUCTURE.py
#        - nom_document = nom DOCX si existe, sinon nom PDF original
# v1.9 : dossier_html normalise, bouton haut-gauche par defaut
# v1.8 : refactorisation complete, CSV separateur ;, place_bouton

import csv
import shutil
import unicodedata
import re
from pathlib import Path
from typing import List, Dict, Optional

version = ("musique.py", "1.10")
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
DEF_POS_Y_SENTINEL = -1.0   # calcule automatiquement depuis haut de page
DEF_ROTATION       = "E"
DEF_ORIENT         = "2"
DEF_LARGEUR        = 160
DEF_HAUTEUR        = 35


# ─────────────────────────────────────────────────────────────────────
# NORMALISATION — identique a genere_site.py
# ─────────────────────────────────────────────────────────────────────
def normaliser_nom(nom: str) -> str:
    """Normalise un segment de chemin pour URL (garde . et autres)."""
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.replace("'", "_").replace("\u2019", "_")
    nom = nom.replace(" ", "_")
    return nom.lower()


def _normaliser_fichier(texte: str) -> str:
    """Normalise un nom de fichier PDF (supprime . et caracteres speciaux)."""
    t = normaliser_nom(texte)
    t = re.sub(r"[^\w]", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def _nom_html_depuis_pdf(nom_pdf: str) -> str:
    """
    Calcule le nom normalise du PDF dans html/.
    '__partition_L Auvergnat.pdf' -> 'l_auvergnat.pdf'
    'Ma Partition.pdf'           -> 'ma_partition.pdf'
    Supprime le prefixe __partition_ si present.
    """
    n = Path(nom_pdf).name
    for prefix in ("__partition_", "__partition _", "__partition"):
        if n.lower().startswith(prefix):
            n = n[len(prefix):]
            break
    return _normaliser_fichier(Path(n).stem) + ".pdf"


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
    nom_html    = _normaliser_fichier(stem) + ".pdf"
    return (nom_lisible, nom_html)


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
    Retourne un dict { nom_pdf_source_lower: params }.
    La cle est en minuscules pour comparaison insensible a la casse.
    """
    if not csv_path.exists():
        return {}

    resultats = {}
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
                    "transparence"    : _int(  _get(row, "transparence"),              DEF_TRANSPARENCE),
                    "pos_x"           : _float(_get(row, "position_horizontale",
                                                    "pos_x", "x"),                    DEF_POS_X),
                    "pos_y"           : _float(_get(row, "position_verticale",
                                                    "pos_y", "y"),                    DEF_POS_Y_SENTINEL),
                    "rotation"        : _get(row, "rotation",           defaut=DEF_ROTATION),
                    "orient_texte"    : _get(row, "orientation_texte",
                                             "orient",                  defaut=DEF_ORIENT),
                    "largeur"         : _int(  _get(row, "largeur", "width"),          DEF_LARGEUR),
                    "hauteur"         : _int(  _get(row, "hauteur", "height"),         DEF_HAUTEUR),
                }

                # Valider rotation et orient
                try:
                    _pbp.parse_rotation(params["rotation"])
                except ValueError:
                    log_func(f"  CSV ligne {i+2} : rotation invalide "
                             f"{params['rotation']!r} -> {DEF_ROTATION} par defaut")
                    params["rotation"] = DEF_ROTATION

                try:
                    _pbp.parse_orient(params["orient_texte"])
                except ValueError:
                    log_func(f"  CSV ligne {i+2} : orientation_texte invalide "
                             f"{params['orient_texte']!r} -> {DEF_ORIENT} par defaut")
                    params["orient_texte"] = DEF_ORIENT

                resultats[nom_pdf.strip().lower()] = params

    except Exception as e:
        log_func(f"  ERREUR lecture CSV : {e}")

    log_func(f"  CSV : {len(resultats)} entree(s)")
    return resultats


# ─────────────────────────────────────────────────────────────────────
# RECHERCHE DU DOCX ASSOCIE
# ─────────────────────────────────────────────────────────────────────
def _trouver_docx(dossier: Path, stem_pdf: str) -> Optional[str]:
    """
    Cherche un fichier DOCX dont le nom normalise correspond au stem du PDF.
    Retourne le nom original du DOCX (avec accents/espaces) ou None.
    """
    stem_norm = _normaliser_fichier(stem_pdf)
    for f in dossier.iterdir():
        if not f.is_file() or f.suffix.lower() not in ('.doc', '.docx'):
            continue
        if _normaliser_fichier(f.stem) == stem_norm:
            return f.name
    return None


# ─────────────────────────────────────────────────────────────────────
# TRAITEMENT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────
def traiter_partitions_du_dossier(dossier: Path, log_func) -> int:
    """
    Traite tous les PDF du dossier :
      - PDF dans CSV     -> bouton YouTube ajoute -> copie dans html\
      - PDF hors CSV     -> copie directe         -> copie dans html\
    Met a jour STRUCTURE.py avec la liste complete.
    Retourne le nombre de PDFs traites.
    """
    # Dossier HTML cible avec normalisation identique a genere_site.py
    try:
        chemin_relatif      = dossier.relative_to(Path(DOSSIER_DOCUMENTS))
        segments_normalises = [normaliser_nom(s) for s in chemin_relatif.parts]
        dossier_html        = Path(DOSSIER_HTML).joinpath(*segments_normalises)
    except ValueError:
        dossier_html = Path(str(dossier).replace(
            str(DOSSIER_DOCUMENTS), str(DOSSIER_HTML), 1))

    dossier_html.mkdir(parents=True, exist_ok=True)
    log_func(f"  Dossier cible : {dossier_html}")

    # Lire CSV (vide si absent)
    csv_path = dossier / "__correspondance.csv"
    csv_data = lire_csv(csv_path, log_func) if csv_path.exists() else {}

    # Lister tous les PDF du dossier (ignorer les __correspondance etc.)
    pdfs = sorted(
        f for f in dossier.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
        and not f.name.startswith("__correspondance")
    )

    if not pdfs:
        log_func("  Aucun PDF dans le dossier")
        return 0

    nb = 0
    partitions_structure = []

    for pdf_source in pdfs:
        nom_src  = pdf_source.name
        nom_dst  = _nom_html_depuis_pdf(nom_src)
        pdf_cible = dossier_html / nom_dst

        # Chercher DOCX associe pour nom_document
        stem_src  = Path(nom_src).stem
        # Pour __partition_X, chercher DOCX avec nom X
        stem_docx = stem_src
        for prefix in ("__partition_", "__partition _", "__partition"):
            if stem_src.lower().startswith(prefix):
                stem_docx = stem_src[len(prefix):]
                break
        nom_docx = _trouver_docx(dossier, stem_docx)
        nom_document = nom_docx if nom_docx else nom_src

        # PDF dans le CSV -> ajouter bouton
        if nom_src.lower() in csv_data and HAS_PDF_LIBS:
            p = csv_data[nom_src.lower()]
            log_func(f"  [BOUTON] {nom_src} -> {nom_dst}")

            try:
                angle_rot      = _pbp.parse_rotation(p["rotation"])
                vertical, _    = _pbp.parse_orient(p["orient_texte"])

                # pos_y auto : haut de page si non defini
                pos_x = p["pos_x"]
                pos_y = p["pos_y"]
                if pos_y == DEF_POS_Y_SENTINEL:
                    from pypdf import PdfReader as _PR
                    ph    = float(_PR(str(pdf_source)).pages[0].mediabox.height)
                    pos_y = ph - p["hauteur"]
                    log_func(f"         pos_y auto : {ph:.0f} - {p['hauteur']} = {pos_y:.0f}")

                log_func(f"         commande equivalente :")
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

                partitions_structure.append({
                    "nom_pdf"      : nom_dst,
                    "nom_document" : nom_document,
                    "youtube_url"  : p["youtube_url"],
                    "avec_bouton"  : True,
                })

            except Exception as e:
                log_func(f"  ERREUR bouton {nom_src} : {e}")
                # Fallback : copie simple
                shutil.copy2(str(pdf_source), str(pdf_cible))
                log_func(f"         -> copie simple (fallback)")
                partitions_structure.append({
                    "nom_pdf"      : nom_dst,
                    "nom_document" : nom_document,
                    "youtube_url"  : p["youtube_url"],
                    "avec_bouton"  : False,
                })
                nb += 1

        else:
            # PDF hors CSV -> copie directe
            if nom_src.lower() in csv_data and not HAS_PDF_LIBS:
                log_func(f"  [COPIE ] {nom_src} -> {nom_dst} (pypdf manquant)")
            else:
                log_func(f"  [COPIE ] {nom_src} -> {nom_dst}")
            shutil.copy2(str(pdf_source), str(pdf_cible))
            nb += 1

            partitions_structure.append({
                "nom_pdf"      : nom_dst,
                "nom_document" : nom_document,
                "youtube_url"  : None,
                "avec_bouton"  : False,
            })

    # Mettre a jour STRUCTURE.py
    _mettre_a_jour_structure(dossier, partitions_structure, log_func)
    log_func(f"  {nb} PDF traite(s) ({len(csv_data)} avec bouton)")
    return nb


def _mettre_a_jour_structure(dossier: Path, partitions: List[dict],
                              log_func) -> None:
    try:
        structure = struct.charger_structure(dossier)
        structure["partitions"] = partitions
        struct.sauvegarder_structure(dossier, structure)
        log_func(f"  STRUCTURE.py : {len(partitions)} entree(s)")
    except Exception as e:
        log_func(f"  ERREUR STRUCTURE.py : {e}")


def initialiser_dossier_musique(log_func) -> Path:
    dossier = Path(DOSSIER_HTML) / NOM_DOSSIER_MUSIQUE
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier

# Fin musique.py v1.10
