@echo off
REM lancer_v4_1.cmd — Version 4.1
REM Lance la generation du site avec options
REM Usage :
REM   lancer.cmd             => genere le site ET demarre le serveur local
REM   lancer.cmd local       => idem (synonyme explicite)
REM   lancer.cmd nolocal     => genere le site SANS demarrer le serveur
REM                             (utilise par maj_github.py)

setlocal

REM Passer en mode UTF-8
chcp 65001 >nul

REM Lire l'argument (insensible a la casse)
set ARG=%~1
if /i "%ARG%"=="nolocal" (
    set LANCER_SERVEUR=non
) else (
    set LANCER_SERVEUR=oui
)

REM Generation site
echo.
echo ============================================================
echo Generation du site
echo ============================================================
cd C:\SiteGITHUB\Hebreu4.0\prog
python genere_site.py
if errorlevel 1 (
    echo ERREUR : genere_site.py a echoue
    exit /b 1
)
cd ..

echo ============================================================
echo pour utiliser le style en local
echo alors qu'il est genere pour github
echo ============================================================

md html\Hebreu4.0\html 2>nul
copy package\html\Hebreu4.0\html\style.css html\Hebreu4.0\html\style.css >nul

echo.
echo ============================================================
echo ===      GENERATION TERMINEE      ===
if "%LANCER_SERVEUR%"=="oui" (
echo === Demarrage du serveur local     ===
) else (
echo === Mode nolocal - pas de serveur  ===
)
echo ============================================================

if "%LANCER_SERVEUR%"=="non" goto fin

npx http-server html -p 3500 --cors -c-1 -o "/index.html"
echo.
echo Site disponible dans : localhost:3500/index.html
echo.

:fin
echo.
echo lancer_v4_1.cmd — Version 4.1 acheve
REM lancer_v4_1.cmd — Version 4.1
