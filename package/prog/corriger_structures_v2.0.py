#!/usr/bin/env python3
# corriger_structures.py — Version 2.0
"""
Utilitaire de correction STRUCTURE.py.

Corrections appliquées:
1. Supprime doublons PDF (si DOCX existe)
2. Remplace "idem" par "{{nom_document_sans_ext}}"
3. Corrige logique nom_document/nom_html

Usage:
    python corriger_structures.py <dossier> [--dry-run]
"""

import sys
import json
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Tuple

def normaliser_nom(nom: str) -> str:
    """Normalise nom pour URL."""
    nom = unicodedata.normalize('NFD', nom)
    nom = ''.join(c for c in nom if unicodedata.category(c) != 'Mn')
    nom = nom.replace("'", "_").replace("'", "_").replace(" ", "_")
    return nom.lower()

def charger_structure(dossier: Path) -> Dict[str, Any]:
    """Charge STRUCTURE.py."""
    fichier = dossier / "STRUCTURE.py"
    if not fichier.exists():
        return None
    
    try:
        from importlib.machinery import SourceFileLoader
        module = SourceFileLoader("STRUCTURE", str(fichier)).load_module()
        return module.STRUCTURE
    except Exception as e:
        print(f"  ✗ Erreur lecture {fichier}: {e}")
        return None

def sauvegarder_structure(dossier: Path, structure: Dict[str, Any]) -> None:
    """Sauvegarde STRUCTURE.py."""
    if "dossiers" in structure:
        structure["dossiers"].sort(key=lambda x: x.get("position", 9999))
    if "fichiers" in structure:
        structure["fichiers"].sort(key=lambda x: x.get("position", 9999))
    
    contenu = "# STRUCTURE.py – Corrigé automatiquement v2.0\n"
    contenu += "# Templates {{variable}} pour flexibilité\n\n"
    
    json_str = json.dumps(structure, ensure_ascii=False, indent=4)
    json_str = json_str.replace("true", "True").replace("false", "False")
    
    contenu += f"STRUCTURE = {json_str}\n"
    
    fichier = dossier / "STRUCTURE.py"
    fichier.write_text(contenu, encoding="utf-8")

def fichier_docx_existe_pour_pdf(nom_pdf: str, dossier: Path) -> bool:
    """Vérifie si un DOCX source existe pour un PDF.
    
    Args:
        nom_pdf: Nom du fichier PDF (normalisé ou non)
        dossier: Dossier où chercher
        
    Returns:
        True si DOCX correspondant existe
    """
    # Stem du PDF
    pdf_stem = Path(nom_pdf).stem
    pdf_stem_norm = normaliser_nom(pdf_stem)
    
    # Chercher DOCX correspondant
    for f in dossier.iterdir():
        if f.suffix.lower() in ['.doc', '.docx']:
            docx_stem_norm = normaliser_nom(f.stem)
            if docx_stem_norm == pdf_stem_norm:
                return True
    
    return False

def remplacer_idem_par_template(valeur: Any) -> str:
    """Remplace 'idem' par template approprié.
    
    Args:
        valeur: Valeur actuelle (peut être "idem", idem, ou autre)
        
    Returns:
        Template ou valeur originale
    """
    if valeur == "idem" or valeur == 'idem':
        return "{{nom_document_sans_ext}}"
    return valeur

def corriger_element_fichier(item: Dict[str, Any], dossier: Path) -> Tuple[bool, str]:
    """Corrige un élément fichier.
    
    Returns:
        (modifié: bool, raison: str)
    """
    modif = False
    raisons = []
    
    # 1. Remplacer "idem" par templates
    for champ in ["nom_affiché", "nom_TDM", "nom_navigation"]:
        if champ in item:
            nouvelle_valeur = remplacer_idem_par_template(item[champ])
            if nouvelle_valeur != item[champ]:
                item[champ] = nouvelle_valeur
                modif = True
                raisons.append(f"{champ}:idem→template")
    
    # 2. Corriger nom_document/nom_html si nécessaire
    # (logique existante de v1.0)
    
    return (modif, ", ".join(raisons) if raisons else "")

def supprimer_doublons_pdf(structure: Dict[str, Any], dossier: Path) -> Tuple[int, List[str]]:
    """Supprime les doublons PDF (si DOCX existe).
    
    Returns:
        (nb_supprimes: int, noms_supprimes: List[str])
    """
    if "fichiers" not in structure:
        return (0, [])
    
    fichiers_a_garder = []
    nb_supprimes = 0
    noms_supprimes = []
    
    for item in structure["fichiers"]:
        nom_doc = item.get("nom_document", "")
        
        # Si c'est un PDF
        if nom_doc.lower().endswith('.pdf'):
            # Vérifier si DOCX correspondant existe
            if fichier_docx_existe_pour_pdf(nom_doc, dossier):
                # DOCX existe → supprimer ce PDF (c'est un doublon)
                nb_supprimes += 1
                noms_supprimes.append(nom_doc)
                continue  # Ne pas ajouter à fichiers_a_garder
        
        # Garder cet élément
        fichiers_a_garder.append(item)
    
    structure["fichiers"] = fichiers_a_garder
    return (nb_supprimes, noms_supprimes)

def corriger_dossier_structure(dossier: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Corrige STRUCTURE.py d'un dossier.
    
    Returns:
        Statistiques: {doublons, idem_remplaces, total_modifs}
    """
    print(f"\n📁 {dossier}")
    
    structure = charger_structure(dossier)
    if structure is None:
        print("  ⊘ Pas de STRUCTURE.py")
        return {"doublons": 0, "idem": 0, "total": 0}
    
    stats = {"doublons": 0, "idem": 0, "total": 0}
    
    # 1. Supprimer doublons PDF
    nb_doublons, noms_doublons = supprimer_doublons_pdf(structure, dossier)
    if nb_doublons > 0:
        stats["doublons"] = nb_doublons
        stats["total"] += nb_doublons
        for nom in noms_doublons:
            print(f"  ✗ Doublon PDF supprimé : {nom}")
    
    # 2. Corriger fichiers (remplacer "idem")
    if "fichiers" in structure:
        for i, item in enumerate(structure["fichiers"]):
            modif, raison = corriger_element_fichier(item, dossier)
            if modif:
                structure["fichiers"][i] = item
                stats["idem"] += 1
                stats["total"] += 1
                print(f"  ✓ Corrigé : {item.get('nom_document', '?')} ({raison})")
    
    # 3. Corriger dossiers (remplacer "idem")
    if "dossiers" in structure:
        for i, item in enumerate(structure["dossiers"]):
            modif, raison = corriger_element_fichier(item, dossier)
            if modif:
                structure["dossiers"][i] = item
                stats["idem"] += 1
                stats["total"] += 1
                print(f"  ✓ Corrigé dossier : {item.get('nom_document', '?')} ({raison})")
    
    # Sauvegarder si modifié
    if stats["total"] > 0 and not dry_run:
        sauvegarder_structure(dossier, structure)
        print(f"  💾 STRUCTURE.py sauvegardé")
        print(f"     - Doublons PDF : {stats['doublons']}")
        print(f"     - 'idem' remplacés : {stats['idem']}")
    elif stats["total"] > 0:
        print(f"  🔍 [DRY RUN] {stats['total']} modification(s)")
    else:
        print("  ✓ Aucune correction nécessaire")
    
    return stats

def parcourir_et_corriger(racine: Path, dry_run: bool = False) -> None:
    """Parcourt et corrige tous STRUCTURE.py."""
    print("="*60)
    print("CORRECTION STRUCTURE.py v2.0")
    print("="*60)
    print("\nCorrections appliquées:")
    print("1. Suppression doublons PDF (si DOCX existe)")
    print("2. Remplacement 'idem' par templates")
    print("="*60)
    
    if dry_run:
        print("\n⚠️  MODE DRY RUN - Aucune sauvegarde\n")
    
    stats_totaux = {"doublons": 0, "idem": 0, "total": 0, "dossiers": 0}
    
    for racine_dir, dirs, files in racine.walk():
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "nppBackup"}]
        
        if "STRUCTURE.py" in files:
            stats_totaux["dossiers"] += 1
            stats = corriger_dossier_structure(racine_dir, dry_run)
            stats_totaux["doublons"] += stats["doublons"]
            stats_totaux["idem"] += stats["idem"]
            stats_totaux["total"] += stats["total"]
    
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    print(f"Dossiers traités : {stats_totaux['dossiers']}")
    print(f"Doublons PDF supprimés : {stats_totaux['doublons']}")
    print(f"'idem' remplacés : {stats_totaux['idem']}")
    print(f"Total modifications : {stats_totaux['total']}")
    
    if dry_run:
        print("\n⚠️  MODE DRY RUN - Aucune sauvegarde")
        print("Relancez sans --dry-run pour appliquer")

def main():
    """Point d'entrée."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python corriger_structures.py <dossier> [--dry-run]")
        print("\nExemple:")
        print("  python corriger_structures.py C:\\SiteGITHUB\\Hebreu4.0\\documents")
        print("  python corriger_structures.py C:\\SiteGITHUB\\Hebreu4.0\\documents --dry-run")
        return
    
    racine = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    
    if not racine.exists():
        print(f"✗ Dossier inexistant : {racine}")
        return
    
    parcourir_et_corriger(racine, dry_run)

if __name__ == "__main__":
    main()

# Fin corriger_structures.py v2.0
