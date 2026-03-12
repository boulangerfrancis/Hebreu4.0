#!/usr/bin/env python3
# regenerer_tous_pdf.py — Version 1.0
"""
Utilitaire de regénération forcée de TOUS les PDF.

Usage:
    python regenerer_tous_pdf.py

Supprime tous les PDF existants et relance genere_site.py
avec regeneration=True temporairement.
"""

import sys
import os
from pathlib import Path
import shutil

def supprimer_tous_pdf(racine: Path) -> int:
    """Supprime tous les PDF dans documents/ et html/."""
    nb_supprimes = 0
    
    # Parcourir documents/
    for root, dirs, files in os.walk(racine / "documents"):
        for f in files:
            if f.lower().endswith('.pdf') and not f.startswith('~$'):
                fichier = Path(root) / f
                fichier.unlink()
                nb_supprimes += 1
                print(f"✗ Supprimé : {fichier}")
    
    # Supprimer html/ complet (sera recréé)
    html_dir = racine / "html"
    if html_dir.exists():
        shutil.rmtree(html_dir)
        print(f"✗ Dossier html/ supprimé")
    
    return nb_supprimes

def main():
    # Support appel depuis lancer.cmd
    skip_confirm = "--skip-confirm" in sys.argv
    
    if not skip_confirm:
        print("=" * 60)
        print("RÉGÉNÉRATION FORCÉE TOUS LES PDF")
        print("=" * 60)
        print()
    
    # Trouver racine projet
    script_dir = Path(__file__).parent
    racine = script_dir.parent
    
    if not skip_confirm:
        print(f"Projet : {racine}")
        print()
        
        # Confirmation
        reponse = input("⚠️  Supprimer TOUS les PDF existants ? (oui/non) : ")
        if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
            print("Annulé.")
            return
        
        print()
    
    print("Suppression PDF...")
    nb = supprimer_tous_pdf(racine)
    print(f"{nb} PDF supprimés")
    
    if not skip_confirm:
        print()
        print("=" * 60)
        print("Maintenant lancez : prog\\lancer.cmd")
        print("Tous les PDF seront regénérés.")
        print("=" * 60)

if __name__ == "__main__":
    main()
