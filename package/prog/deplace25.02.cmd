@echo off
REM deplace25.0.cmd — Déploiement complet v25.0 (màj)
REM Depuis : C:\SiteGITHUB\Hebreu4.0\package\prog
REM Vers   : C:\SiteGITHUB\Hebreu4.0\prog  et  prog\lib1

SET SRC=C:\SiteGITHUB\Hebreu4.0\package\prog
SET DST=C:\SiteGITHUB\Hebreu4.0\prog
SET LIB=C:\SiteGITHUB\Hebreu4.0\prog\lib1

echo ============================================================
echo  DEPLOIEMENT v25.0
echo  Source      : %SRC%
echo  Cible prog  : %DST%
echo  Cible lib1  : %LIB%
echo ============================================================
echo.

if not exist "%DST%" mkdir "%DST%"
if not exist "%LIB%" mkdir "%LIB%"

REM --- Racine prog\ ---
echo [prog\] Fichiers principaux...
move /Y "%SRC%\genere_site_v25.0.py"       "%DST%\genere_site.py"
move /Y "%SRC%\settings_v1.0.py"           "%DST%\settings.py"
move /Y "%SRC%\documents_v1.3.py"          "%DST%\documents.py"
move /Y "%SRC%\builder_v1.0.py"            "%DST%\builder.py"
move /Y "%SRC%\docx_to_pdf_v1.3.py"        "%DST%\docx_to_pdf.py"

REM --- lib1\ ---
echo [lib1\] Modules utilitaires...
move /Y "%SRC%\partition_utils_v1.3.py"    "%LIB%\partition_utils.py"

REM --- lib1\ shims (redirigent vers settings.py) ---
echo [lib1\] Shims compatibilite...
move /Y "%SRC%\lib1_options_shim_v2.0.py"  "%LIB%\options.py"
move /Y "%SRC%\lib1_config_shim_v4.0.py"   "%LIB%\config.py"

echo.
echo ============================================================
echo  Resultat prog\ :
dir /B "%DST%\*.py"
echo.
echo  Resultat lib1\ :
dir /B "%LIB%\*.py"
echo ============================================================
echo.
echo Deploiement termine.
pause
