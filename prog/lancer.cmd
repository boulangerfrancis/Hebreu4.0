@echo off
REM lancer.cmd — Version 4.0
REM Lance la génération du site avec options
echo lancer.cmd version 4.0
setlocal

REM Passer en mode UTF-8
chcp 65001 >nul
REM Génération site
rem vérifier que le dossier courant est bien c:\Sitegithub\Hebreu4.0
echo.
echo ============================================================
echo Generation du site
echo ============================================================
cd C:\SiteGITHUB\Hebreu4.0\prog
python genere_site.py
cd ..
echo ============================================================
echo pour utiliser le style en local
echo alors qu'il est généré pour github
echo ============================================================

md html\Hebreu4.0\html
copy package\html\Hebreu4.0\html\style.css html\Hebreu4.0\html\style.css

echo.
echo ============================================================
echo ===    GENERATION TERMINEE     ===
echo === Démarrage du serveur local ===
echo ============================================================
npx http-server html -p 3500 --cors -c-1 -o "/index.html"
echo.
echo Site disponible dans : localhost:3500/index.html
echo.
:fin
echo lancer.cmd — Version 4.0 achevé
REM lancer.cmd — Version 4.0
