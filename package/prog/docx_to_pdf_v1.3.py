"""
docx_to_pdf.py — Version 1.3
Convertit un fichier DOCX en PDF via l'imprimante PDFCreator.

Nouveautés v1.3 :
- Correction bug _print() : flush via sys.stdout.flush() (pas kwarg flush=)

Nouveautés v1.2 :
- Flush stdout après chaque print (log visible en temps réel, plus de paquets)
- Suppression automatique du PDF résiduel dans c:\\temp après déplacement
- Nettoyage initial de c:\\temp si des PDF traînent

Fonctionnalités :
- Vérifie si Word est déjà ouvert et demande de le fermer.
- PDFCreator crée son fichier en c:\\temp\\<nomInitial>.pdf
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

# Flush immédiat : log visible en temps réel (correction défaut v1.1)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

version = ("docx_to_pdf.py", "1.3")
print(f"[Version] {version[0]} — {version[1]}")

DEFAULT_TIMEOUT = 120  # secondes max pour générer le PDF
TEMP_DIR = r"c:\temp"


def _print(msg: str) -> None:
    """Print avec flush immédiat pour log en temps réel."""
    print(msg)
    sys.stdout.flush()


def check_word_running() -> None:
    """Vérifie si Word est déjà en cours d'exécution et demande de le fermer."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and proc.info["name"].lower() in ("winword.exe", "word.exe"):
            input("⚠ Word est déjà ouvert. Merci de le fermer puis appuyez sur Entrée...")
            break


def wait_for_file(filepath: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Attend que le fichier existe et ne soit plus verrouillé.

    Args:
        filepath: Chemin du fichier à attendre
        timeout: Délai maximum en secondes

    Returns:
        True si fichier disponible, False si timeout
    """
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


def nettoyer_temp(stem: str) -> None:
    """Supprime le PDF résiduel dans c:\\temp après conversion réussie.

    Word/PDFCreator peut laisser une copie dans c:\\temp même après
    que shutil.move() l'a déplacé vers la destination finale.

    Args:
        stem: Nom de base du fichier (sans extension) pour construire le nom PDF
    """
    pdf_temp = os.path.join(TEMP_DIR, stem + ".pdf")
    if os.path.exists(pdf_temp):
        try:
            os.remove(pdf_temp)
            _print(f"  🗑 Résidu c:\\temp supprimé : {os.path.basename(pdf_temp)}")
        except Exception as e:
            _print(f"  ⚠ Impossible de supprimer {pdf_temp} : {e}")


def docx_to_pdf(input_path: str, output_path: str = None,
                timeout: int = DEFAULT_TIMEOUT) -> None:
    """Convertit un DOCX en PDF via PDFCreator imprimante.

    v1.2 : Flush log en temps réel + nettoyage c:\\temp après déplacement.

    Args:
        input_path: Chemin du fichier DOCX.
        output_path: Chemin de sortie PDF. Si None, PDF créé dans le dossier du DOCX.
        timeout: Temps max (secondes) pour attendre le PDF.

    Raises:
        FileNotFoundError: Si le fichier DOCX n'existe pas.
        TimeoutError: Si le PDF n'est pas généré dans le délai imparti.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")

    input_path = os.path.abspath(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    # PDF intermédiaire créé par PDFCreator dans c:\temp
    source_pdf = os.path.join(TEMP_DIR, base_name + ".pdf")

    # Destination finale
    if output_path is None:
        output_path = os.path.join(os.path.dirname(input_path), base_name + ".pdf")
    else:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Supprimer ancien PDF intermédiaire si présent
    if os.path.exists(source_pdf):
        os.remove(source_pdf)

    # Vérifier Word
    check_word_running()

    # Lancement Word
    _print(f"⏳ Conversion : {os.path.basename(input_path)}")
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    try:
        doc = word.Documents.Open(input_path)
        word.ActivePrinter = "PDFCreator"
        doc.PrintOut(Background=False)
        doc.Close(False)
        word.Quit()

        _print(f"⏳ Attente PDF : {source_pdf}")
        if not wait_for_file(source_pdf, timeout=timeout):
            raise TimeoutError(f"PDF non généré en {timeout} secondes : {source_pdf}")

        # Déplacer vers destination finale
        if os.path.abspath(source_pdf).lower() != os.path.abspath(output_path).lower():
            shutil.move(source_pdf, output_path)
            # v1.2 : Nettoyage résidu c:\temp (au cas où move n'a pas supprimé la source)
            nettoyer_temp(base_name)
        
        _print(f"✅ PDF : {output_path}")

    except Exception as e:
        _print(f"❌ Erreur : {e}")
        try:
            word.Quit()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _print("Usage : python docx_to_pdf.py fichier.docx [sortie.pdf]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        docx_to_pdf(input_file, output_file)
    except Exception as e:
        _print(f"❌ Erreur : {e}")
        sys.exit(1)

# Fin docx_to_pdf.py — Version 1.2
