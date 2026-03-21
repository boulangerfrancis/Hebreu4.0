# installer_v1.1.py — Version 1.1
# v1.1 : ajout beautifulsoup4 (requis pour TDM et genere_site)
# v1.0 : creation
#   Cree l'environnement virtuel Python C:\virpy13 et installe
#   toutes les bibliotheques necessaires au projet Hebreu4.0.
#   Compatible Windows 10/11, Python 3.11+.
#
# Usage :
#   python installer.py        (depuis prog\ ou n'importe ou)
#   Double-clic sur installer.py
#
# Ce programme peut etre relance sans risque : si l'environnement existe
# deja, il met a jour les packages si necessaire.

import sys
import os
import subprocess
import shutil
from pathlib import Path

version = ("installer.py", "1.1")

# ─────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

VENV_DIR = Path(r"C:\virpy13")

# Packages requis : (nom_pip, description)
PACKAGES = [
    ("pyyaml",          "Lecture fichiers config.yaml"),
    ("python-docx",     "Lecture/ecriture fichiers Word .docx"),
    ("pypdf",           "Manipulation PDF (boutons YouTube)"),
    ("reportlab",       "Generation PDF"),
    ("psutil",          "Detection processus (serveur local)"),
    ("beautifulsoup4",  "Generation table des matieres (TDM)"),
    ("requests",        "Requetes HTTP (optionnel)"),
]

# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

VERT  = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
BLEU  = "\033[94m"
RESET = "\033[0m"
GRAS  = "\033[1m"

def C(t, c=""):
    return f"{c}{t}{RESET}" if c else t

def ok(msg):
    print(f"  {C('OK', VERT)}      {msg}")

def err(msg):
    print(f"  {C('ERREUR', ROUGE)}  {msg}")

def info(msg):
    print(f"  {C('...', JAUNE)}    {msg}")

def titre(msg):
    print()
    print(C("  " + msg, GRAS))
    print(f"  {'-' * (len(msg) + 2)}")


def verifier_python():
    """Verifie que la version Python est suffisante."""
    v = sys.version_info
    if v < (3, 11):
        err(f"Python {v.major}.{v.minor} detecte — Python 3.11+ requis")
        sys.exit(1)
    ok(f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})")
    return True


def creer_venv():
    """Cree l'environnement virtuel si absent."""
    titre("Environnement virtuel")

    if VENV_DIR.exists():
        pip_path = VENV_DIR / "Scripts" / "pip.exe"
        if pip_path.exists():
            ok(f"{VENV_DIR} existe deja")
            return True
        else:
            info(f"{VENV_DIR} incomplet — recreation...")
            shutil.rmtree(str(VENV_DIR))

    info(f"Creation de {VENV_DIR} ...")
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"Echec creation venv : {result.stderr.strip()}")
        return False

    ok(f"{VENV_DIR} cree")
    return True


def pip_venv() -> Path:
    """Retourne le chemin de pip dans le venv."""
    return VENV_DIR / "Scripts" / "pip.exe"


def python_venv() -> Path:
    """Retourne le chemin de python dans le venv."""
    return VENV_DIR / "Scripts" / "python.exe"


def package_installe(nom: str) -> bool:
    """Verifie si un package est deja installe dans le venv."""
    result = subprocess.run(
        [str(pip_venv()), "show", nom],
        capture_output=True, text=True
    )
    return result.returncode == 0


def installer_packages():
    """Installe ou met a jour tous les packages requis."""
    titre("Installation des packages")

    # Mise a jour pip
    info("Mise a jour de pip...")
    subprocess.run(
        [str(python_venv()), "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True, text=True
    )

    erreurs = 0
    for pkg, desc in PACKAGES:
        deja = package_installe(pkg)
        if deja:
            ok(f"{pkg:<20}  {desc}  (deja installe)")
            continue

        info(f"Installation de {pkg}...")
        result = subprocess.run(
            [str(pip_venv()), "install", pkg],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok(f"{pkg:<20}  {desc}")
        else:
            err(f"{pkg:<20}  ECHEC — {result.stderr.strip()[-100:]}")
            erreurs += 1

    return erreurs == 0


def verifier_imports():
    """Verifie que les imports critiques fonctionnent dans le venv."""
    titre("Verification des imports")

    tests = [
        ("import yaml",               "pyyaml"),
        ("import docx",               "python-docx"),
        ("import pypdf",              "pypdf"),
        ("import reportlab",          "reportlab"),
        ("import psutil",             "psutil"),
        ("from bs4 import BeautifulSoup", "beautifulsoup4"),
    ]

    py = str(python_venv())
    ok_count = 0
    for import_stmt, pkg in tests:
        result = subprocess.run(
            [py, "-c", import_stmt],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok(f"{import_stmt}")
            ok_count += 1
        else:
            err(f"{import_stmt}  — package {pkg} non disponible")

    return ok_count == len(tests)


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def main():
    # Activer les couleurs ANSI sur Windows
    os.system("")

    print()
    print(C("=" * 60, BLEU))
    print(C("  INSTALLATION — Environnement Python Hebreu4.0", GRAS))
    print(C("  installer.py v1.0", BLEU))
    print(C("=" * 60, BLEU))

    titre("Version Python")
    verifier_python()

    if not creer_venv():
        print()
        err("Impossible de creer l'environnement virtuel.")
        err("Verifiez que Python est dans le PATH et que vous avez")
        err(f"les droits d'ecriture sur {VENV_DIR.parent}")
        sys.exit(1)

    if not installer_packages():
        print()
        err("Certains packages n'ont pas pu etre installes.")
        err("Verifiez votre connexion internet et relancez installer.py")
        sys.exit(1)

    imports_ok = verifier_imports()

    print()
    print(C("=" * 60, BLEU))
    if imports_ok:
        print(C("  INSTALLATION REUSSIE", VERT + GRAS))
        print(C(f"  Environnement : {VENV_DIR}", VERT))
        print(C("  Vous pouvez maintenant utiliser lancer.cmd", VERT))
    else:
        print(C("  INSTALLATION PARTIELLE — voir erreurs ci-dessus", JAUNE + GRAS))
    print(C("=" * 60, BLEU))
    print()

    if not imports_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

# fin installer_v1.1.py — Version 1.1
