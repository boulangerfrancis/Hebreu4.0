@echo off
REM lancer_v4.4.cmd — Version 4.4
REM Lance la generation du site avec options
REM Usage :
REM   lancer.cmd             => genere le site ET demarre le serveur local
REM   lancer.cmd local       => idem (synonyme explicite)
REM   lancer.cmd nolocal     => genere le site SANS demarrer le serveur
REM                             (utilise par maj_github.py)
REM
REM v4.4 : style.css copie depuis prog\ (source correcte)
REM v4.3 : correction chemin CD (lancer.cmd est dans prog\, pas a la racine)
REM        suppression de html\ avant regeneration (evite fichiers residuels)
REM v4.2 : activation environnement virtuel Python auto
REM
REM Environnement virtuel Python :
REM   Si C:\virpy13\Scripts\activate.bat existe, il est active automatiquement
REM   Sinon le Python systeme est utilise (avec avertissement)

setlocal

REM Passer en mode UTF-8
chcp 65001 >nul

REM ── Chemins ────────────────────────────────────────────────────────
REM lancer.cmd se trouve dans prog\  donc :
REM   PROG_DIR = dossier de lancer.cmd  (= prog\)
REM   ROOT_DIR = dossier parent         (= racine du projet)
set "PROG_DIR=%~dp0"
REM Supprimer le \ final pour que %PROG_DIR%\.. soit valide
set "PROG_DIR=%PROG_DIR:~0,-1%"
for %%I in ("%PROG_DIR%\..") do set "ROOT_DIR=%%~fI"

REM ── Activation environnement virtuel Python ────────────────────────
set VENV=C:\virpy13
if exist "%VENV%\Scripts\activate.bat" (
    echo Activation environnement virtuel : %VENV%
    call "%VENV%\Scripts\activate.bat"
) else (
    echo AVERTISSEMENT : environnement virtuel %VENV% non trouve
    echo Utilisation du Python systeme - certains modules peuvent manquer
    echo Pour creer l environnement : python installer.py
)

REM ── Lire l'argument (insensible a la casse) ────────────────────────
set ARG=%~1
if /i "%ARG%"=="nolocal" (
    set LANCER_SERVEUR=non
) else (
    set LANCER_SERVEUR=oui
)

REM ── Suppression html\ avant regeneration ──────────────────────────
echo.
echo ============================================================
echo Suppression html\ avant regeneration
echo ============================================================
if exist "%ROOT_DIR%\html\" (
    rd /s /q "%ROOT_DIR%\html"
    echo html\ supprime.
) else (
    echo html\ absent - rien a supprimer.
)

REM ── Generation site ───────────────────────────────────────────────
echo.
echo ============================================================
echo Generation du site
echo ============================================================
cd /d "%PROG_DIR%"
python genere_site.py
if errorlevel 1 (
    echo.
    echo ERREUR : genere_site.py a echoue
    echo Verifiez que tous les modules sont installes : python installer.py
    cd /d "%ROOT_DIR%"
    exit /b 1
)
cd /d "%ROOT_DIR%"

REM ── Copie style.css pour consultation locale ───────────────────────
echo ============================================================
echo Copie style.css pour consultation locale
echo ============================================================
if exist "%PROG_DIR%\style.css" (
    md "%ROOT_DIR%\html\Hebreu4.0\html" 2>nul
    copy "%PROG_DIR%\style.css" ^
         "%ROOT_DIR%\html\Hebreu4.0\html\style.css" >nul
    echo style.css copie depuis prog\ vers html\Hebreu4.0\html\
) else (
    echo AVERTISSEMENT : prog\style.css absent - lancer remplace.py d abord
)

echo.
echo ============================================================
echo ===        GENERATION TERMINEE        ===
if "%LANCER_SERVEUR%"=="oui" (
echo ===  Demarrage du serveur local        ===
) else (
echo ===  Mode nolocal - pas de serveur     ===
)
echo ============================================================

if "%LANCER_SERVEUR%"=="non" goto fin

cd /d "%ROOT_DIR%"
npx http-server html -p 3500 --cors -c-1 -o "/index.html"
echo.
echo Site disponible dans : localhost:3500/index.html
echo.

:fin
echo.
echo lancer_v4.4.cmd — Version 4.4 acheve
REM lancer_v4.4.cmd — Version 4.4
