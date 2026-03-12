@echo off
REM Début de "lancer.cmd" version "2.3"
cls
echo.
echo lancer.cmd — Version 2.3
echo.

:: O entrer en mode virtualisation pour python
setlocal EnableExtensions EnableDelayedExpansion

rem Nom de l'environnement virtuel
set VENV_NAME=virPy13

rem Chemin d'activation
set VENV_PATH=c:\%VENV_NAME%\Scripts\activate.bat

rem Vérifier si le fichier activate.bat existe
if not exist "%VENV_PATH%" (
    echo L'environnement virtuel "%VENV_NAME%" n'a pas été trouvé.
    exit /b 1
)

rem Si l'environnement existe, activer l'environnement virtuel
echo L'environnement "%VENV_NAME%" a été trouvé. Activation en cours...
call "%VENV_PATH%"

rem Si l'activation réussie, exécuter le reste du script
if not errorlevel 1 (
    echo Environnement activé avec succès.
    rem Ajouter ici le reste des commandes que tu souhaites exécuter après activation
) else (
    echo Echec de l'activation de l'environnement.
    exit /b 1
)
:: Aller dans le répertoire du projet
cd /d "%~dp0\.."

echo.
echo === Génération du site réel à partir du dossier documents ===

:: 1. On lance d'abord genere_site.py (il crée html/ et tous les dossiers)
python prog\genere_site.py
if %errorlevel% neq 0 (
    echo [ERREUR] genere_site.py a échoué
    pause
    exit /b 1
)

:: 2. Ensuite seulement on génère la TDM (html/ existe maintenant → plus d'erreur)
python prog\cree_table_des_matieres.py
if %errorlevel% neq 0 (
    echo [ERREUR] cree_table_des_matieres.py a échoué
    pause
    exit /b 1
)
rem créer /Hebreu4.0/html/Hebreu4.0/html/style.css
xcopy html\style.css html\Hebreu4.0\html\*.*

echo.
echo === Démarrage du serveur local ===
npx http-server html -p 3500 --cors -c-1 -o "/index.html"

echo.
echo Site réel disponible sur : http://localhost:3500/index.html
echo.
pause
REM Fin de "lancer.cmd" version "2.3"