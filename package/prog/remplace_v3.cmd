@echo off
REM remplace_v3.cmd — Version 3
REM Corrections : partition_utils v2.0 (rotation PDF), musique v1.5 (YouTube IFrame API)
REM               documents v2.1 (preserve cle partitions), structure_utils v2.1 (null->None)
chcp 65001 >nul

SET SRC=C:\SiteGITHUB\Hebreu4.0\package\prog
SET DST=C:\SiteGITHUB\Hebreu4.0\prog
SET LIB=C:\SiteGITHUB\Hebreu4.0\prog\lib1

echo.
echo ============================================================
echo  REMPLACEMENT v3
echo ============================================================

if not exist "%DST%" mkdir "%DST%"
if not exist "%LIB%" mkdir "%LIB%"

copy /Y "%SRC%\genere_site_v25.1.py"       "%DST%\genere_site.py"
copy /Y "%SRC%\settings_v1.0.py"           "%DST%\settings.py"
copy /Y "%SRC%\documents_v2.1.py"          "%DST%\documents.py"
copy /Y "%SRC%\builder_v1.0.py"            "%DST%\builder.py"
copy /Y "%SRC%\docx_to_pdf_v1.3.py"        "%DST%\docx_to_pdf.py"
copy /Y "%SRC%\musique_v1.5.py"            "%DST%\musique.py"
copy /Y "%SRC%\versions_v1.0.py"           "%DST%\versions.py"
copy /Y "%SRC%\partition_utils_v2.0.py"    "%LIB%\partition_utils.py"
copy /Y "%SRC%\structure_utils_v2.1.py"    "%LIB%\structure_utils.py"
copy /Y "%SRC%\lib1_options_shim_v2.0.py"  "%LIB%\options.py"
copy /Y "%SRC%\lib1_config_shim_v4.0.py"   "%LIB%\config.py"

echo.
echo Versions deployees :
cd "%DST%"
python versions.py
cd C:\SiteGITHUB\Hebreu4.0

echo.
echo IMPORTANT : supprimer le PDF final existant pour forcer la regeneration :
echo   del "documents\En empruntant quelques chemins DLTJ\Chants hebreux et Yiddish. Partitions\l_auvergnat_de_brassens_en_hebreu.pdf"
echo Puis relancer lancer.cmd
echo.
pause
