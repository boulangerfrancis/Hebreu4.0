# versions.py — Version 1.0
# Affiche la version de chaque module Python du projet
"""
Usage :
    python versions.py  (depuis prog/)

Lit le tuple 'version' ou 'VERSION' de chaque fichier .py
sans l'importer (lecture texte + ast) pour eviter les effets de bord.
"""

import ast
import sys
from pathlib import Path

PROG_DIR = Path(__file__).parent
LIB1_DIR = PROG_DIR / "lib1"

FICHIERS = [
    # (chemin relatif a PROG_DIR, description)
    ("genere_site.py",         "Generateur principal"),
    ("settings.py",            "Configuration"),
    ("documents.py",           "Gestion documents/PDF"),
    ("musique.py",             "Module musique/partitions"),
    ("builder.py",             "Generation HTML"),
    ("docx_to_pdf.py",         "Conversion DOCX->PDF"),
    ("lib1/partition_utils.py","Boutons YouTube PDF"),
    ("lib1/structure_utils.py","Gestion STRUCTURE.py"),
    ("lib1/html_utils.py",     "Utilitaires HTML"),
    ("lib1/fichier_utils.py",  "Utilitaires fichiers"),
    ("lib1/pdf_utils.py",      "Utilitaires PDF"),
    ("lib1/options.py",        "Shim options"),
    ("lib1/config.py",         "Shim config"),
    ("cree_table_des_matieres.py", "Table des matieres"),
]


def lire_version(chemin: Path):
    """Extrait le tuple version d'un fichier .py sans l'importer.

    Cherche :
        version = ("nom.py", "1.0")
        VERSION = ("nom.py", "25.1")
        __version__ = "1.0"
    """
    if not chemin.exists():
        return None, "ABSENT"

    try:
        src  = chemin.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception as e:
        return None, f"ERREUR LECTURE: {e}"

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            nom = target.id.lower()
            if nom not in ("version", "__version__"):
                continue
            val = node.value
            # Tuple ("nom.py", "1.0")
            if isinstance(val, ast.Tuple) and len(val.elts) == 2:
                try:
                    nom_fich = ast.literal_eval(val.elts[0])
                    ver_str  = ast.literal_eval(val.elts[1])
                    return nom_fich, ver_str
                except Exception:
                    pass
            # String simple "1.0"
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                return chemin.name, val.value

    # Fallback : chercher dans les commentaires d'en-tete
    for line in src.splitlines()[:5]:
        if "Version" in line or "version" in line:
            import re
            m = re.search(r'[Vv]ersion\s*[:\-]?\s*([\d.]+)', line)
            if m:
                return chemin.name, m.group(1)

    return chemin.name, "?"


def main():
    print()
    print("=" * 60)
    print(f"  VERSIONS DES MODULES — {PROG_DIR}")
    print("=" * 60)
    print(f"  {'Fichier':<35} {'Version':<10} Description")
    print(f"  {'-'*35} {'-'*10} {'-'*25}")

    for rel, desc in FICHIERS:
        chemin = PROG_DIR / rel
        nom_lu, ver = lire_version(chemin)
        statut = "✓" if chemin.exists() else "✗"
        print(f"  {statut} {rel:<33} {ver:<10} {desc}")

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

# Fin versions.py v1.0
