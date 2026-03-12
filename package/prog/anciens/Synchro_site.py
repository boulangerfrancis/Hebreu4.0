# Synchro_site.py version 0.4
"""
Synchronisation automatisée d'un site GitHub Pages collaboratif.

Fonctionnalités :
- Mode --dry-run (simulation sans modification)
- Sauvegarde ZIP avant nettoyage
- Copie d'une base commune
- Copie d'ajouts spécifiques au collaborateur
- Commit & push vers GitHub
"""

import argparse
import configparser
import logging
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

# ============================================================
# VERSION & CONFIG
# ============================================================

SCRIPT_VERSION = "0.4"
CONFIG_FILE_NAME = "config_Synchro_site.ini"
CONFIG_VERSION = "01"

# ============================================================
# OUTILS
# ============================================================


def run_cmd(command: str, cwd: Path | None = None, dry_run: bool = False) -> None:
    """Exécute une commande système ou la simule en dry-run."""
    if dry_run:
        logging.info("[DRY-RUN] %s", command)
        return
    subprocess.run(command, cwd=cwd, shell=True, check=True)


def create_backup(project_path: Path, backup_dir: Path) -> None:
    """Crée une archive ZIP du projet ami (hors .git)."""
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backup_dir / f"backup_ami_{timestamp}.zip"

    with ZipFile(zip_path, "w") as zipf:
        for item in project_path.rglob("*"):
            if ".git" in item.parts:
                continue
            zipf.write(item, item.relative_to(project_path))


def analyse_content(src: Path) -> tuple[set[str], Counter]:
    """Analyse dossiers racines et types de fichiers."""
    folders = set()
    extensions = Counter()

    for item in src.rglob("*"):
        if item.is_dir():
            folders.add(item.parts[0])
        else:
            extensions[item.suffix or "sans_extension"] += 1

    return folders, extensions


def copy_content(src: Path, dst: Path, dry_run: bool) -> None:
    """Copie le contenu d'un dossier vers un autre (hors .git)."""
    for item in src.iterdir():
        if item.name == ".git":
            continue
        dest = dst / item.name
        if dry_run:
            continue
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronisation GitHub Pages")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation sans aucune modification",
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    script_dir = script_path.parent

    print(
        f"Exécution de {script_path.name} "
        f"version {SCRIPT_VERSION}"
    )

    # --------------------------------------------------------
    # Vérification fichier de configuration
    # --------------------------------------------------------

    config_path = script_dir / CONFIG_FILE_NAME
    if not config_path.exists():
        print(
            f"ERREUR : fichier de configuration introuvable :\n"
            f"{config_path}"
        )
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    if config["meta"]["config_version"] != CONFIG_VERSION:
        print("ERREUR : version de configuration incompatible")
        sys.exit(1)

    # --------------------------------------------------------
    # Chargement configuration
    # --------------------------------------------------------

    mon_projet = Path(config["paths"]["mon_projet"])
    ami_projet = Path(config["paths"]["ami_projet"])
    ajouts_ami = Path(config["paths"]["dossier_specifique_ami"])

    nom_ami = config["github"]["nom_ami"]
    projet_ami = config["github"]["projet_ami"]
    branch = config["github"]["branch"]

    ami_repo = f"https://github.com/{nom_ami}/{projet_ami}.git"

    backup_enabled = config.getboolean("backup", "enabled")
    backup_dir = script_dir / config["backup"]["backup_dir"]

    # --------------------------------------------------------
    # Logging
    # --------------------------------------------------------

    log_level = config.get("logging", "log_level", fallback="INFO")
    log_file = config.get("logging", "log_file", fallback="Synchro_site.log")
  
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(script_dir / log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
  
    logging.info(
        "Mode DRY-RUN activé" if args.dry_run else "Mode EXECUTION"
    )

    # --------------------------------------------------------
    # Analyse préalable (résumé)
    # --------------------------------------------------------

    base_dirs, base_ext = analyse_content(mon_projet)
    logging.info("Base commune - dossiers : %s", sorted(base_dirs))
    logging.info("Base commune - types    : %s", dict(base_ext))

    if ajouts_ami.exists():
        ajout_dirs, ajout_ext = analyse_content(ajouts_ami)
        logging.info("Ajouts ami  - dossiers : %s", sorted(ajout_dirs))
        logging.info("Ajouts ami  - types    : %s", dict(ajout_ext))

    # --------------------------------------------------------
    # Git
    # --------------------------------------------------------

    run_cmd(f"git ls-remote {ami_repo}", dry_run=args.dry_run)

    if not (ami_projet / ".git").exists():
        run_cmd(
            f"git clone -b {branch} {ami_repo} \"{ami_projet}\"",
            dry_run=args.dry_run,
        )

    if backup_enabled:
        logging.info("Sauvegarde avant nettoyage")
        if not args.dry_run:
            create_backup(ami_projet, backup_dir)

    # Nettoyage dépôt ami
    logging.info("Nettoyage du dépôt ami")
    for item in ami_projet.iterdir():
        if item.name == ".git":
            continue
        if args.dry_run:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # Copies
    logging.info("Copie base commune")
    copy_content(mon_projet, ami_projet, args.dry_run)

    if ajouts_ami.exists():
        logging.info("Copie ajouts spécifiques ami")
        copy_content(ajouts_ami, ami_projet, args.dry_run)

    # Commit & push
    run_cmd("git add .", cwd=ami_projet, dry_run=args.dry_run)
    run_cmd(
        f'git commit -m "Synchronisation automatique v{SCRIPT_VERSION}"',
        cwd=ami_projet,
        dry_run=args.dry_run,
    )
    run_cmd("git push", cwd=ami_projet, dry_run=args.dry_run)
# Synchro_site.py version 0.4

    logging.info("Fin de synchronisation")


if __name__ == "__main__":
    main()
