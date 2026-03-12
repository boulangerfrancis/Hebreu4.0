@echo off
REM remplace_v5.cmd — Version 5
REM partition_utils v2.1 (bord/sens_texte, zones clic corrigees), musique v1.6
chcp 65001 >nul
setlocal enabledelayedexpansion

SET SRC=C:\SiteGITHUB\Hebreu4.0\package\prog
SET DST=C:\SiteGITHUB\Hebreu4.0\prog
SET LIB=C:\SiteGITHUB\Hebreu4.0\prog\lib1

echo.
echo ============================================================
echo  REMPLACEMENT v5
echo  Source : %SRC%
echo  Cible  : %DST%
echo ============================================================
echo.

if not exist "%DST%" mkdir "%DST%"
if not exist "%LIB%" mkdir "%LIB%"

SET ERREURS=0

echo [prog\] Fichiers principaux...
call :copier "%SRC%\genere_site_v25.1.py"      "%DST%\genere_site.py"
call :copier "%SRC%\settings_v1.0.py"          "%DST%\settings.py"
call :copier "%SRC%\documents_v2.1.py"         "%DST%\documents.py"
call :copier "%SRC%\builder_v1.0.py"           "%DST%\builder.py"
call :copier "%SRC%\docx_to_pdf_v1.3.py"       "%DST%\docx_to_pdf.py"
call :copier "%SRC%\musique_v1.6.py"           "%DST%\musique.py"
call :copier "%SRC%\versions_v1.0.py"          "%DST%\versions.py"
echo.
echo [lib1\] Modules utilitaires...
call :copier "%SRC%\partition_utils_v2.1.py"   "%LIB%\partition_utils.py"
call :copier "%SRC%\structure_utils_v2.1.py"   "%LIB%\structure_utils.py"
echo.
echo [lib1\] Shims compatibilite...
call :copier "%SRC%\lib1_options_shim_v2.0.py" "%LIB%\options.py"
call :copier "%SRC%\lib1_config_shim_v4.0.py"  "%LIB%\config.py"

echo.
echo ============================================================
if %ERREURS%==0 (
    echo  Toutes les copies effectuees avec succes.
) else (
    echo  ATTENTION : %ERREURS% erreur(s^) -- verifier les lignes ABSENT et ECHEC ci-dessus.
)
echo ============================================================

echo.
echo Versions deployees :
cd "%DST%"
python versions.py
cd C:\SiteGITHUB\Hebreu4.0

echo.
echo ============================================================
echo  ACTIONS MANUELLES REQUISES :
echo ============================================================
echo.
echo  1. Supprimer le PDF final pour forcer la regeneration :
echo     del "documents\...\l_auvergnat_de_brassens_en_hebreu.pdf"
echo.
echo  2. Dans __correspondance.csv, verifier/ajouter les colonnes :
echo     bord (0=bas affiche, 1=haut)  et  sens_texte (0=normal, 1=retourne)
echo     Exemple : ....,H,100,0,0,,,
echo.
echo  3. Relancer lancer.cmd
echo.
echo ============================================================
echo.
pause
goto :eof


REM ================================================================
REM  :copier  SOURCE  CIBLE
REM  Affiche OK / ABSENT / ECHEC avec chemins relatifs
REM ================================================================
:copier
SET "_SRC=%~1"
SET "_DST=%~2"
SET "_REL_SRC=%~1"
SET "_REL_DST=%~2"
SET "_REL_SRC=%_REL_SRC:C:\SiteGITHUB\Hebreu4.0\=%"
SET "_REL_DST=%_REL_DST:C:\SiteGITHUB\Hebreu4.0\=%"

if not exist "%_SRC%" (
    echo   ABSENT   %_REL_SRC%
    SET /A ERREURS+=1
    goto :eof
)

copy /Y "%_SRC%" "%_DST%" >nul 2>&1

if exist "%_DST%" (
    echo   OK       %_REL_SRC%  copie en  %_REL_DST%
) else (
    echo   ECHEC    %_REL_SRC%  copie en  %_REL_DST%
    SET /A ERREURS+=1
)
goto :eof
