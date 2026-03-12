# remplace_v10.py
# Version 10.1
# v10.1 : cree_table_des_matieres v6.30 (resolution templates TDM)
# v10.0 : genere_site v25.3 (style.css, suppression musique/, TDM)
# v9.1 : place_bouton v1.1 (NewWindow YouTube)
# Verifie et copie les fichiers du package vers le dossier prog.
# Affiche la version de chaque fichier source et cible.
# Signale les fichiers presents dans prog\ qui ne sont pas repertories.
#
# Usage : python remplace_v9.py

import shutil
import sys
import re
from pathlib import Path

version = ("remplace_v10.py", "10.1")

# ─────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────
RACINE = Path("C:/SiteGITHUB/Hebreu4.0")
SRC    = RACINE / "package" / "prog"
DST    = RACINE / "prog"
LIB    = DST / "lib1"

# (nom_fichier_source, chemin_cible, obligatoire)
FICHIERS = [
    # prog\
    ("genere_site_v25.3.py",       DST / "genere_site.py",       True),
    ("settings_v1.0.py",           DST / "settings.py",          True),
    ("documents_v2.1.py",          DST / "documents.py",         True),
    ("builder_v1.0.py",            DST / "builder.py",           True),
    ("docx_to_pdf_v1.3.py",        DST / "docx_to_pdf.py",       True),
    ("conversion_pdf_v1.0.py",     DST / "conversion_pdf.py",    True),
    ("cree_table_des_matieres_v6.30.py", DST / "cree_table_des_matieres.py", True),
    ("musique_v1.13.py",           DST / "musique.py",           True),
    ("normalisation_utils_v1.0.py", DST / "normalisation_utils.py", True),
    ("place_bouton_v02.py",        DST / "place_bouton.py",      True),
    ("versions_v1.0.py",           DST / "versions.py",          False),
    ("remplace_v10.py",            DST / "remplace.py",          False),
    ("style.css",                  DST / "style.css",            True),
    # lib1\
    ("structure_utils_v2.1.py",    LIB / "structure_utils.py",   True),
    ("fichier_utils_v1.0.py",      LIB / "fichier_utils.py",     True),
    ("html_utils_v1.0.py",         LIB / "html_utils.py",        True),
    ("pdf_utils_v1.1.py",          LIB / "pdf_utils.py",         True),
    ("partition_utils_v2.3.py",    LIB / "partition_utils.py",   True),
    ("lib1_options_shim_v2.0.py",  LIB / "options.py",           False),
    ("lib1_config_shim_v4.0.py",   LIB / "config.py",            False),
]

# Fichiers a supprimer si presents (anciens noms)
SUPPRIMER = [
    DST / "Place_Bouton_PDF.py",
    DST / "place_bouton_v01.py",
    DST / "place_bouton_v02.py",  # si deploye manuellement
]

# Fichiers connus dans prog\ et lib1\ (ne pas signaler comme inutiles)
# = toutes les cibles de FICHIERS + fichiers systeme Python
CONNUS_DST  = {Path(c).name for _, c, _ in FICHIERS}
CONNUS_LIB  = {Path(c).name for _, c, _ in FICHIERS if str(c).startswith(str(LIB))}
IGNORER_EXT = {".pyc", ".pyo"}
IGNORER_NOM = {"__pycache__", "__init__.py", "lancer.cmd", "lancer.bat"}


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def extraire_version(chemin: Path) -> str:
    """Extrait le numero de version depuis version = ('nom', 'X.Y') ou commentaire."""
    try:
        contenu = chemin.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'version\s*=\s*\([^,]+,\s*["\']([^"\']+)["\']', contenu)
        if m:
            return m.group(1)
        m = re.search(r'Version\s+([\d.]+)', contenu)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "?"


def afficher(statut, src_rel, dst_rel, ver_src="", ver_dst="", note=""):
    col_src = str(src_rel)[:38].ljust(38)
    col_dst = str(dst_rel)[:32].ljust(32)
    ver_col = ""
    if ver_src or ver_dst:
        ver_col = f"  v{ver_src} -> v{ver_dst}"
    note_col = f"  [{note}]" if note else ""
    print(f"  {statut:<8} {col_src} -> {col_dst}{ver_col}{note_col}")


def rel(chemin: Path) -> Path:
    try:    return chemin.relative_to(RACINE)
    except: return chemin


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 72)
    print(f"  remplace_v9.py v9.0  —  verification et deploiement")
    print(f"  Source : {SRC}")
    print(f"  Cible  : {DST}")
    print("=" * 72)

    erreurs = 0
    copies  = 0
    a_jour  = 0

    # Dossiers obligatoires
    for d in (SRC, DST, LIB):
        if not d.exists():
            print(f"  ERREUR dossier introuvable : {d}")
            erreurs += 1
    if erreurs:
        print(f"\n  {erreurs} erreur(s) bloquante(s) — arret.")
        sys.exit(1)

    # ── Copie des fichiers ────────────────────────────────────────────
    print()
    print("  DEPLOIEMENT")
    print()

    for nom_src, chemin_dst, obligatoire in FICHIERS:
        chemin_src = SRC / nom_src
        src_r = rel(chemin_src)
        dst_r = rel(chemin_dst)

        if not chemin_src.exists():
            note = "OBLIGATOIRE" if obligatoire else "optionnel"
            afficher("ABSENT", src_r, dst_r, note=note)
            if obligatoire:
                erreurs += 1
            continue

        ver_src = extraire_version(chemin_src)
        ver_dst = extraire_version(chemin_dst) if chemin_dst.exists() else "—"

        if ver_src == ver_dst:
            afficher("OK", src_r, dst_r, ver_src, ver_dst, "a jour")
            a_jour += 1
        else:
            shutil.copy2(str(chemin_src), str(chemin_dst))
            afficher("COPIE", src_r, dst_r, ver_src, ver_dst)
            copies += 1

    # ── Suppressions ─────────────────────────────────────────────────
    print()
    print("  SUPPRESSIONS (anciens fichiers)")
    print()
    for chemin in SUPPRIMER:
        if chemin.exists():
            chemin.unlink()
            print(f"  SUPPRIME {rel(chemin)}")
        else:
            print(f"  ABSENT   {rel(chemin)}  (deja supprime)")

    # ── Fichiers non repertories dans prog\ ──────────────────────────
    inutiles_dst = []
    inutiles_lib = []

    for f in DST.iterdir():
        if f.is_dir():
            continue
        if f.suffix in IGNORER_EXT or f.name in IGNORER_NOM:
            continue
        if f.name not in CONNUS_DST:
            inutiles_dst.append(f)

    if LIB.exists():
        for f in LIB.iterdir():
            if f.is_dir():
                continue
            if f.suffix in IGNORER_EXT or f.name in IGNORER_NOM:
                continue
            if f.name not in CONNUS_LIB:
                inutiles_lib.append(f)

    if inutiles_dst or inutiles_lib:
        print()
        print("  FICHIERS NON REPERTORIES (a verifier / supprimer manuellement)")
        print()
        for f in sorted(inutiles_dst):
            ver = extraire_version(f)
            print(f"  ?? prog\\{f.name:<40}  v{ver}")
        for f in sorted(inutiles_lib):
            ver = extraire_version(f)
            print(f"  ?? lib1\\{f.name:<40}  v{ver}")
    else:
        print()
        print("  Aucun fichier non repertorie dans prog\\ et lib1\\")

    # ── Bilan ─────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    if erreurs:
        print(f"  ATTENTION : {erreurs} erreur(s) — voir ABSENT OBLIGATOIRE ci-dessus")
    else:
        print(f"  OK : {copies} copie(s)   {a_jour} deja a jour   "
              f"{len(inutiles_dst)+len(inutiles_lib)} fichier(s) non repertorie(s)")
    print("=" * 72)
    print()

    if erreurs:
        sys.exit(1)


if __name__ == "__main__":
    main()
