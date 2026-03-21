@echo off
REM MAJ_GITHUB.cmd — Mise a jour du site GitHub Hebreu4.0
REM Placer ce fichier sur le Bureau (ou creer un raccourci vers lui)
REM Double-cliquer pour lancer la mise a jour

title Mise a jour site GitHub

REM ── Activation de l'environnement Python virtuel ──────────────
call C:\virpy13\Scripts\activate
if errorlevel 1 (
    echo ERREUR : Impossible d'activer C:\virpy13\Scripts\activate
    echo Verifiez que l'environnement virtuel existe.
    pause
    exit /b 1
)

REM ── Dossier du script (meme dossier que ce .cmd) ──────────────
set SCRIPT_DIR=%~dp0
set SCRIPT=%SCRIPT_DIR%maj_github.py

REM ── Lancement du script Python ────────────────────────────────
if not exist "%SCRIPT%" (
    echo ERREUR : maj_github.py introuvable dans %SCRIPT_DIR%
    pause
    exit /b 1
)

python "%SCRIPT%"

REM ── En cas d'erreur Python, garder la fenetre ouverte ─────────
if errorlevel 1 (
    echo.
    echo Le programme s'est termine avec une erreur.
    pause
)
