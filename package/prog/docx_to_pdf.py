"""
docx_to_pdf.py
version 1.1
Convertit un fichier DOCX en PDF via l'imprimante PDFCreator.

Fonctionnalités :
- Vérifie si Word est déjà ouvert et demande de le fermer.
- pdf creator crée son fichier en c:\\temp\\<nomInitial>.pdf
- PDF généré par défaut dans le même dossier que le DOCX avec le même nom.
- Déplacement/renommage automatique si le chemin de sortie est différent.
- Timeout configurable pour l'attente du PDF.
- Création automatique du dossier de sortie si nécessaire.
- Compatible batch sur plusieurs fichiers.

Pré-requis :
- Microsoft Word installé
- PDFCreator installé et profil AutoSave configuré
- PyWin32 installé : pip install pywin32
- psutil installé : pip install psutil
"""
import io
import os
import sys
import time
import shutil
import psutil
import win32com.client
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DEFAULT_TIMEOUT = 30  # secondes max pour générer le PDF


def check_word_running():
    """Vérifie si Word est déjà en cours d'exécution et demande de le fermer."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and proc.info["name"].lower() in ("winword.exe", "word.exe"):
            input("⚠ Word est déjà ouvert. Merci de le fermer puis appuyez sur Entrée...")
            break


def wait_for_file(filepath, timeout=DEFAULT_TIMEOUT):
    """Attend que le fichier existe et ne soit plus verrouillé."""
    start = time.time()
    while True:
        if os.path.exists(filepath):
            try:
                with open(filepath, "rb"):
                    return True
            except PermissionError:
                pass
        if time.time() - start > timeout:
            return False
        time.sleep(0.5)


def docx_to_pdf(input_path, output_path=None, timeout=DEFAULT_TIMEOUT):
    """
    Convertit un DOCX en PDF via PDFCreator imprimante.

    Args:
        input_path (str): Chemin du fichier DOCX.
        output_path (str, optional): Chemin de sortie PDF. Si None, PDF
                                     est créé dans le même dossier que le DOCX.
        timeout (int, optional): Temps max pour attendre le PDF.

    Raises:
        FileNotFoundError: Si le fichier DOCX n'existe pas.
        TimeoutError: Si le PDF n'est pas généré dans le délai imparti.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")
    input_path = os.path.abspath(input_path)

    # PDF par défaut dans le même dossier que le DOCX
    base_name = os.path.splitext(os.path.basename(input_path))[0]
#    source_pdf = os.path.join(os.path.dirname(input_path), base_name + ".pdf")
    source_pdf = os.path.join("c:/test", base_name + ".pdf")
    # Définir output_path et créer dossier si nécessaire
    if output_path is None:
#        output_path = source_pdf
        output_path = os.path.dirname(input_path)
    else:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Supprimer ancien PDF si présent
    if os.path.exists(source_pdf):
        os.remove(source_pdf)

    # Vérifier Word
    check_word_running()

    # Lancement Word
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(input_path)

        # Imprimer vers PDFCreator (profil AutoSave)
        word.ActivePrinter = "PDFCreator"
        doc.PrintOut(Background=False)
        doc.Close(False)
        word.Quit()

        print("⏳ Attente génération PDF...")
        if not wait_for_file(source_pdf, timeout=timeout):
            raise TimeoutError(f"Le PDF n’a pas été généré dans {timeout} secondes.")

        # Déplacer/renommer si nécessaire
        if source_pdf.lower() != output_path.lower():
            shutil.move(source_pdf, output_path)

        print(f"✅ PDF final : {output_path}")

    except Exception as e:
        print(f"❌ Erreur : {e}")
        try:
            word.Quit()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python docx_to_pdf.py fichier.docx [sortie.pdf]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        docx_to_pdf(input_file, output_file)
    except Exception as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)
