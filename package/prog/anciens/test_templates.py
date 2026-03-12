#!/usr/bin/env python3
# test_templates.py — Diagnostic templates

from pathlib import Path
import sys

# Ajouter lib1 au path
sys.path.insert(0, str(Path(__file__).parent / "lib1"))

from lib1.options import BASE_PATH
from lib1 import html_utils as html

print("=" * 60)
print("TEST INTERPRÉTATION TEMPLATES")
print("=" * 60)
print(f"BASE_PATH = '{BASE_PATH}'")
print()

# Test 1 : Fonction interpreter_template
print("TEST 1 : interpreter_template()")
print("-" * 60)
template = '<a href="{{BASE_PATH}}/index.html">Accueil</a>'
print(f"Template : {template}")
resultat = html.interpreter_template(template, {"BASE_PATH": BASE_PATH})
print(f"Résultat : {resultat}")
print(f"✓ OK" if "{{BASE_PATH}}" not in resultat else "✗ ÉCHEC - {{BASE_PATH}} non remplacé")
print()

# Test 2 : Fichier TDM/entete_general.html
print("TEST 2 : Fichier TDM/entete_general.html")
print("-" * 60)

fichier_tdm = Path("c:/SiteGITHUB/Hebreu4.0/documents/TDM/entete_general.html")
if not fichier_tdm.exists():
    print(f"✗ FICHIER INEXISTANT : {fichier_tdm}")
else:
    print(f"✓ Fichier existe : {fichier_tdm}")
    
    # Lire contenu brut
    with open(fichier_tdm, "r", encoding="utf-8") as f:
        contenu_brut = f.read()
    
    print(f"\nContenu brut (premiers 200 chars) :")
    print(contenu_brut[:200])
    
    if "{{BASE_PATH}}" in contenu_brut:
        print("\n✓ Contient {{BASE_PATH}}")
    else:
        print("\n✗ Ne contient PAS {{BASE_PATH}}")
        print("Recherche de variations...")
        if "{ {BASE_PATH} }" in contenu_brut:
            print("  ✗ Trouvé avec espaces : { {BASE_PATH} }")
        if "{{BASE_PATH }}" in contenu_brut or "{{ BASE_PATH}}" in contenu_brut:
            print("  ✗ Trouvé avec espace interne")
    
    # Charger via fonction
    print(f"\nChargement via charger_template_html()...")
    resultat = html.charger_template_html(
        fichier_tdm,
        {"BASE_PATH": BASE_PATH},
        False
    )
    
    print(f"Résultat (premiers 200 chars) :")
    print(resultat[:200])
    
    if "{{BASE_PATH}}" in resultat:
        print("\n✗ ÉCHEC - {{BASE_PATH}} non remplacé dans résultat")
        
        # Diagnostic détaillé
        print("\nDIAGNOSTIC :")
        print(f"  BASE_PATH = '{BASE_PATH}' (type: {type(BASE_PATH)})")
        print(f"  len(BASE_PATH) = {len(BASE_PATH)}")
        print(f"  repr(BASE_PATH) = {repr(BASE_PATH)}")
    else:
        print(f"\n✓ OK - {{{{BASE_PATH}}}} remplacé par '{BASE_PATH}'")

print()
print("=" * 60)
print("FIN TESTS")
print("=" * 60)
