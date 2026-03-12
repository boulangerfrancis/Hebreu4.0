# effacePDF.py — Version 1.1

version = ("effacePDF", "1.1")

import os
import unicodedata
import logging
from datetime import datetime
import sys

# Ajoute le dossier racine du projet au PYTHONPATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from lib1.config import CONFIG
from lib1.options import DOSSIER_DOCUMENTS


class EffacePDF:
    def __init__(self, racine):
        self.racine = racine
        self.config = CONFIG
        self.logger = self._configurer_logger()

    # --------------------------------------------------
    # Configuration du logger (fichier + console)
    # --------------------------------------------------
    def _configurer_logger(self):
        logger = logging.getLogger("EffacePDF")

        # Évite doublons si relancé plusieurs fois
        if logger.hasHandlers():
            logger.handlers.clear()

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        # Log fichier
        file_handler = logging.FileHandler(
            "effacePDF.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)

        # Log console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    # --------------------------------------------------
    # Transformation DOCX → PDF
    # --------------------------------------------------
    def docxverspdf(self, fichier_docx):
        nom, _ = os.path.splitext(fichier_docx)

        # 1) minuscules
        nom = nom.lower()

        # 2) suppression des accents
        nom = unicodedata.normalize("NFD", nom)
        nom = "".join(
            c for c in nom if unicodedata.category(c) != "Mn"
        )

        # 3) remplacement ' et espaces par _
        nom = nom.replace("'", "_")
        nom = nom.replace(" ", "_")

        # 4) extension pdf
        return nom + ".pdf"

    # --------------------------------------------------
    # Dates (basées sur date de modification)
    # --------------------------------------------------
    def date_modification(self, path):
        return os.path.getmtime(path)

    def jour_modification(self, path):
        return datetime.fromtimestamp(
            os.path.getmtime(path)
        ).date()

    def aujourd_hui(self):
        return datetime.today().date()

    # --------------------------------------------------
    # Suppression sécurisée
    # --------------------------------------------------
    def supprimer(self, path):
        try:
            os.remove(path)
            self.logger.info(f"Suppression : {path}")
        except Exception as e:
            self.logger.error(
                f"Erreur suppression {path} : {e}"
            )

    # --------------------------------------------------
    # Parcours principal
    # --------------------------------------------------
    def executer(self):

        self.logger.info("==== DÉBUT TRAITEMENT ====")

        for racine, dossiers, fichiers in os.walk(self.racine):

            for fichier in fichiers:

                if not fichier.lower().endswith(".docx"):
                    continue

                docx_path = os.path.join(racine, fichier)
                pdf_nom = self.docxverspdf(fichier)
                pdf_path = os.path.join(racine, pdf_nom)

                if not os.path.exists(pdf_path):
                    continue

                # -----------------------------------------
                # MODE 1 : regeneration totale
                # -----------------------------------------
                if self.config["regeneration"]:
                    self.logger.info(
                        f"Regeneration=True → suppression {pdf_path}"
                    )
                    self.supprimer(pdf_path)

                # -----------------------------------------
                # MODE 2 : mode normal
                # -----------------------------------------
                else:
                    try:
                        date_pdf = self.date_modification(pdf_path)
                        date_docx = self.date_modification(docx_path)

                        # Cas 1 : PDF plus récent que DOCX
                        if date_pdf > date_docx:
                            self.logger.info(
                                f"PDF plus récent que DOCX → suppression {pdf_path}"
                            )
                            self.supprimer(pdf_path)

                        # Cas 2 : option regenerer aujourd'hui
                        elif self.config["regenerer_pdf_aujourd_hui"]:
                            if (
                                self.jour_modification(pdf_path)
                                == self.aujourd_hui()
                            ):
                                self.logger.info(
                                    f"PDF modifié aujourd'hui → suppression {pdf_path}"
                                )
                                self.supprimer(pdf_path)

                    except Exception as e:
                        self.logger.error(
                            f"Erreur traitement {pdf_path} : {e}"
                        )

        self.logger.info("==== FIN TRAITEMENT ====")


# --------------------------------------------------
# Lancement
# --------------------------------------------------
if __name__ == "__main__":
    programme = EffacePDF(DOSSIER_DOCUMENTS)
    programme.executer()
# effacePDF.py — Version 1.1
