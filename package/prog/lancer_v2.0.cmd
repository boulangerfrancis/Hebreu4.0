@echo off
REM lancer.cmd — Version 2.0
REM Lance la génération du site avec options

setlocal

REM Vérifier argument
set REGENERE_TOUT=0
if "%1"=="regenere_tout" set REGENERE_TOUT=1

REM Passer en mode UTF-8
chcp 65001 >nul

echo.
echo ============================================================
echo GENERATION SITE HEBREU BIBLIQUE v24.0
echo ============================================================
echo.

REM Supprimer ancien HTML
if exist html (
    echo Suppression dossier html/...
    rmdir /s /q html
)

REM Si regenere_tout, supprimer aussi les PDF
if %REGENERE_TOUT%==1 (
    echo.
    echo *** MODE REGENERATION COMPLETE ***
    echo Suppression de tous les PDF existants...
    echo.
    python prog\regenerer_tous_pdf.py --skip-confirm
)

REM Génération site
echo.
echo Phase 1 : Generation PDF + STRUCTURE.py + pages HTML
cd prog
python genere_site.py
cd ..

REM Table des matières
echo.
echo Phase 2 : Generation table des matieres
cd prog
python cree_table_des_matieres.py
cd ..

echo.
echo ============================================================
echo GENERATION TERMINEE
echo ============================================================
echo.
echo Site disponible dans : html\index.html
echo.

pause
