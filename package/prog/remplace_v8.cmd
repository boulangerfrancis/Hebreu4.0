@echo off
REM remplace_v8.cmd — Version 8
REM musique v1.8 : refactorisation complete, nouveau CSV avec ;
REM partition_utils supprime, remplace par Place_Bouton_PDF.py
chcp 65001 >nul
setlocal enabledelayedexpansion

SET SRC=C:\SiteGITHUB\Hebreu4.0\package\prog
SET DST=C:\SiteGITHUB\Hebreu4.0\prog
SET LIB=C:\SiteGITHUB\Hebreu4.0\prog\lib1

echo.
echo ============================================================
echo  REMPLACEMENT v8
echo  musique v1.8 + Place_Bouton_PDF.py
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
call :copier "%SRC%\musique_v1.8.py"           "%DST%\musique.py"
call :copier "%SRC%\Place_Bouton_PDF.py"       "%DST%\Place_Bouton_PDF.py"
call :copier "%SRC%\versions_v1.0.py"          "%DST%\versions.py"
echo.
echo [lib1\] Modules utilitaires...
call :copier "%SRC%\structure_utils_v2.1.py"   "%LIB%\structure_utils.py"
echo.
echo [lib1\] Shims compatibilite...
call :copier "%SRC%\lib1_options_shim_v2.0.py" "%LIB%\options.py"
call :copier "%SRC%\lib1_config_shim_v4.0.py"  "%LIB%\config.py"

echo.
echo SUPPRESSION partition_utils.py (remplace par Place_Bouton_PDF.py^)
if exist "%LIB%\partition_utils.py" (
    del "%LIB%\partition_utils.py"
    echo   OK       supprime lib1\partition_utils.py
) else (
    echo   ABSENT   lib1\partition_utils.py (deja supprime^)
)

echo.
echo ============================================================
if %ERREURS%==0 (
    echo  Toutes les copies effectuees avec succes.
) else (
    echo  ATTENTION : %ERREURS% erreur(s^) -- verifier ABSENT et ECHEC ci-dessus.
)
echo ============================================================
echo.
echo Versions deployees :
cd "%DST%"
python versions.py
cd C:\SiteGITHUB\Hebreu4.0

echo.
echo ============================================================
echo  FORMAT CSV (separateur ;^) :
echo  nom_partition__pdf;youtube_url;transparence;
echo  position_Horizontale;position_verticale;
echo  rotation;orientation_texte;largeur;hauteur
echo.
echo  VALEURS PAR DEFAUT si colonne vide :
echo    transparence=100  x=0  y=0  rotation=E  orient=2  L=160  H=35
echo.
echo  ROTATION  : N E S O  ou  1 2 3 4
echo  ORIENT    : 1-4 texte horizontal  5-8 texte vertical (lettres empilees^)
echo.
echo  NOTE : le PDF cible est TOUJOURS recree a chaque build.
echo         Supprimer le CSV pour desactiver les boutons.
echo ============================================================
echo.
pause
goto :eof


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
