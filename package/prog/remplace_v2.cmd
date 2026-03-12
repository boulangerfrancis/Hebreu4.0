@echo off
REM remplace_v2.cmd — Version 2
REM Deploiement v25.1 : COPY (et non move) pour conserver les sources dans package\prog
REM Les fichiers sources sont preserves -> recuperation facile si besoin
REM
REM Usage : depuis C:\SiteGITHUB\Hebreu4.0\
REM   package\prog\remplace_v2.cmd

chcp 65001 >nul

SET SRC=C:\SiteGITHUB\Hebreu4.0\package\prog
SET DST=C:\SiteGITHUB\Hebreu4.0\prog
SET LIB=C:\SiteGITHUB\Hebreu4.0\prog\lib1

echo.
echo ============================================================
echo  REMPLACEMENT v2  (copy — sources conservees dans package\)
echo  Source : %SRC%
echo  Cible  : %DST%
echo ============================================================
echo.

if not exist "%DST%" mkdir "%DST%"
if not exist "%LIB%" mkdir "%LIB%"

REM --- Racine prog\ ---
echo [prog\] Fichiers principaux...
copy /Y "%SRC%\genere_site_v25.1.py"       "%DST%\genere_site.py"
copy /Y "%SRC%\settings_v1.0.py"           "%DST%\settings.py"
copy /Y "%SRC%\documents_v2.0.py"          "%DST%\documents.py"
copy /Y "%SRC%\builder_v1.0.py"            "%DST%\builder.py"
copy /Y "%SRC%\docx_to_pdf_v1.3.py"        "%DST%\docx_to_pdf.py"
copy /Y "%SRC%\musique_v1.4.py"            "%DST%\musique.py"
copy /Y "%SRC%\versions_v1.0.py"           "%DST%\versions.py"

REM --- lib1\ ---
echo [lib1\] Modules utilitaires...
copy /Y "%SRC%\partition_utils_v1.9.py"    "%LIB%\partition_utils.py"
copy /Y "%SRC%\structure_utils_v2.1.py"    "%LIB%\structure_utils.py"

REM --- lib1\ shims ---
echo [lib1\] Shims compatibilite...
copy /Y "%SRC%\lib1_options_shim_v2.0.py"  "%LIB%\options.py"
copy /Y "%SRC%\lib1_config_shim_v4.0.py"   "%LIB%\config.py"

echo.
echo ============================================================
echo  Verification versions deployees :
echo ============================================================
cd "%DST%"
python versions.py
cd C:\SiteGITHUB\Hebreu4.0
echo.
echo Remplacement termine. Sources conservees dans package\prog\
pause
