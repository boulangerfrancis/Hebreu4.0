@echo off
REM deplace25.0.cmd — Déploiement fichiers v25.0
REM Depuis : C:\SiteGITHUB\Hebreu4.0\package\prog
REM Vers   : C:\SiteGITHUB\Hebreu4.0\prog

SET SRC=C:\SiteGITHUB\Hebreu4.0\package\prog
SET DST=C:\SiteGITHUB\Hebreu4.0\prog

echo ============================================================
echo  DEPLOIEMENT v25.0
echo  Source : %SRC%
echo  Cible  : %DST%
echo ============================================================
echo.

REM Créer le dossier cible si nécessaire
if not exist "%DST%" mkdir "%DST%"

REM --- Fichiers à renommer lors du déplacement ---
echo Déplacement et renommage...

move /Y "%SRC%\genere_site_v25.0.py"   "%DST%\genere_site.py"
move /Y "%SRC%\settings_v1.0.py"       "%DST%\settings.py"
move /Y "%SRC%\documents_v1.0.py"      "%DST%\documents.py"
move /Y "%SRC%\builder_v1.0.py"        "%DST%\builder.py"
move /Y "%SRC%\docx_to_pdf_v1.2.py"    "%DST%\docx_to_pdf.py"

echo.
echo ============================================================
echo  Résultat dans %DST% :
dir /B "%DST%\*.py"
echo ============================================================
echo.
echo Déploiement terminé.
pause
