# normalisation_utils_v1.0.py — Version 1.0
# v1.0 : creation
#   Utilitaires de normalisation des noms de fichiers et chemins.
#   REGLE UNIQUE : normaliser_nom() est la seule fonction de normalisation.
#   Elle est identique a genere_site.normaliser_nom().
#   Tous les programmes (musique.py, documents.py, genere_site.py) doivent
#   utiliser cette fonction pour garantir des noms coherents.
#
#   Transformations appliquees :
#     - Suppression des accents (NFD + filtre Mn)
#     - Apostrophes -> _
#     - Espaces     -> _
#     - Mise en minuscules
#     - Les autres caracteres (. - _ chiffres) sont CONSERVES
#
#   Exemples :
#     'Mi ha-ish.Ps 34.13-15.pdf' -> 'mi_ha-ish.ps_34.13-15.pdf'
#     'A A.docx'                  -> 'a_a.docx'
#     'b A.pdf'                   -> 'b_a.pdf'
#     'a_c.pdf'                   -> 'a_c.pdf'
#     "L'Auvergnat.pdf"           -> 'l_auvergnat.pdf'
#     'Chants et Yiddish. Part'   -> 'chants_et_yiddish._part'  (segment dossier)

import unicodedata

version = ("normalisation_utils.py", "1.0")
print(f"[Import] {version[0]} - Version {version[1]} charge")


def normaliser_nom(nom: str) -> str:
    """
    Normalise un nom de fichier ou segment de chemin pour URL.
    Identique a genere_site.normaliser_nom().

    Conserve : . - _ chiffres lettres
    Transforme : accents supprimes, apostrophes -> _, espaces -> _, majuscules -> minuscules
    """
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    nom = nom.replace("'", "_").replace("\u2019", "_")
    nom = nom.replace(" ", "_")
    return nom.lower()


def normaliser_fichier(nom_fichier: str) -> str:
    """
    Normalise un nom de fichier complet (avec extension).
    Ex: 'Mi ha-ish.Ps 34.13-15.pdf' -> 'mi_ha-ish.ps_34.13-15.pdf'
    """
    return normaliser_nom(nom_fichier)


def normaliser_stem(stem: str) -> str:
    """
    Normalise uniquement le stem (sans extension).
    Ex: 'Mi ha-ish.Ps 34.13-15' -> 'mi_ha-ish.ps_34.13-15'
    """
    return normaliser_nom(stem)


def nom_pdf_depuis_source(nom_fichier: str) -> str:
    """
    Calcule le nom PDF normalise depuis n'importe quel fichier source.
    Change l'extension en .pdf et normalise.

    Ex: 'A A.docx'                  -> 'a_a.pdf'
        'Mi ha-ish.Ps 34.13-15.pdf' -> 'mi_ha-ish.ps_34.13-15.pdf'
        'b A.pdf'                   -> 'b_a.pdf'
        'a_c.pdf'                   -> 'a_c.pdf'
    """
    from pathlib import Path
    stem = Path(nom_fichier).stem
    return normaliser_nom(stem) + ".pdf"


def normaliser_chemin(chemin_relatif) -> "Path":
    """
    Normalise chaque segment d'un chemin relatif (Path ou iterable de str).
    Ex: Path('Chants et Yiddish. Partitions') -> Path('chants_et_yiddish._partitions')

    Usage :
        from pathlib import Path
        rel = Path('Mon Dossier/Sous Dossier')
        norm = normaliser_chemin(rel)  # Path('mon_dossier/sous_dossier')
    """
    from pathlib import Path
    if isinstance(chemin_relatif, (str, Path)):
        parties = Path(chemin_relatif).parts
    else:
        parties = list(chemin_relatif)
    return Path(*[normaliser_nom(p) for p in parties]) if parties else Path(".")


# ─────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cas = [
        ("Mi ha-ish.Ps 34.13-15.pdf",      "PDF avec tiret et points"),
        ("A A.docx",                        "DOCX avec espaces"),
        ("b A.pdf",                         "PDF non normalise"),
        ("a_c.pdf",                         "PDF deja normalise"),
        ("L'Auvergnat.pdf",                 "Apostrophe"),
        ("Chants et Yiddish. Partitions",   "Segment dossier"),
    ]
    print("\n=== normaliser_nom ===")
    for nom, desc in cas:
        print(f"  {nom!r:40} -> {normaliser_nom(nom)!r:40}  ({desc})")
    print("\n=== nom_pdf_depuis_source ===")
    for nom, desc in cas[:5]:
        print(f"  {nom!r:40} -> {nom_pdf_depuis_source(nom)!r:30}  ({desc})")
