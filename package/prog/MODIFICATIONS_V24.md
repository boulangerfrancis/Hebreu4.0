# MODIFICATIONS genere_site.py → v24.0

Ce guide explique comment intégrer les nouvelles fonctionnalités dans genere_site.py v23.5.

---

## IMPORTS À AJOUTER (après ligne 50)

```python
# Import modules nouveaux v24.0
from lib1 import fichier_utils as fichiers
from lib1 import partition_utils as partitions
```

---

## FONCTION generer_pdf_manquants() - MODIFIER

**Localisation** : Ligne ~220

**Ajouter APRÈS conversion DOCX** :

```python
def generer_pdf_manquants(dossier: Path) -> None:
    """Génère PDF manquants depuis DOCX dans le dossier DOCUMENTS."""
    if not DOCX2PDF_DISPONIBLE:
        return
    
    fichiers_dir = list(dossier.iterdir())
    log(f"Vérification PDF manquants : {dossier}")
    
    # PHASE 1 : Conversions DOCX→PDF normales
    nb_conv = pdf.traiter_conversions_dossier(
        dossier,
        fichiers_dir,
        normaliser_nom,
        convertir_docx_vers_pdf,
        CONFIG,
        log
    )
    
    if nb_conv > 0:
        log(f"{nb_conv} PDF généré(s)")
    
    # === NOUVEAU v24.0 : PHASE 2 - Partitions ===
    if not partitions.HAS_PDF_LIBS:
        return
    
    # Chercher __correspondance.csv
    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return  # Pas de partitions dans ce dossier
    
    log(f"Traitement partitions : {dossier}")
    
    # Charger correspondances
    correspondances = partitions.charger_correspondances(csv_path)
    if not correspondances:
        log("  Aucune correspondance trouvée")
        return
    
    # Player URL (depuis config)
    player_url = CONFIG.get("player_url", f"{BASE_PATH}/musique/index.html")
    
    nb_partitions = 0
    
    # Traiter chaque partition
    for nom_pdf_final, video_id in correspondances.items():
        # Chercher PDF source (avec __partition_)
        # Le PDF a déjà été généré depuis DOCX par phase 1
        pdf_source = None
        
        for f in dossier.iterdir():
            if f.name.startswith("__partition_") and f.suffix == ".pdf":
                # Vérifier si correspond au nom final
                nom_attendu = fichiers.nom_partition_final(f.stem + ".docx")
                if normaliser_nom(nom_attendu) == nom_pdf_final:
                    pdf_source = f
                    break
        
        if not pdf_source:
            log(f"  ⚠ PDF source partition introuvable : {nom_pdf_final}")
            continue
        
        # PDF final (sans __partition_)
        pdf_final = dossier / nom_pdf_final
        
        # Vérifier si regénération nécessaire
        if not partitions.doit_regenerer_partition(pdf_source, pdf_final):
            continue
        
        # Ajouter boutons
        log(f"  Partition : {nom_pdf_final} (YouTube: {video_id})")
        success = partitions.ajouter_boutons_partition(
            pdf_source,
            pdf_final,
            player_url,
            video_id
        )
        
        if success:
            nb_partitions += 1
    
    if nb_partitions > 0:
        log(f"{nb_partitions} partition(s) traitée(s)")
```

---

## FONCTION mettre_a_jour_structure() - MODIFIER

**Localisation** : Ligne ~270

**DANS LA BOUCLE `for entry in entries:`**, AJOUTER FILTRE :

```python
def mettre_a_jour_structure(dossier: Path) -> Dict[str, Any]:
    # ...
    entries = sorted(list(dossier.iterdir()), key=lambda x: x.name.lower())
    
    for entry in entries:
        # === NOUVEAU v24.0 : Filtrage fichiers commentaires ===
        if fichiers.doit_filtrer_fichier(entry.name):
            continue  # Ignorer fichiers __* (commentaires)
        
        # Reste du code inchangé...
        if entry.name in IGNORER or entry.name in FICHIERS_ENTETE_PIED:
            continue
        
        # etc...
```

---

## FONCTION est_fichier_copiable() - REMPLACER

**Dans pdf_utils.py** (déjà fait dans v1.1)

Ou ajouter dans genere_site.py si pas dans module :

```python
def est_fichier_copiable_local(fichier: Path) -> bool:
    """Vérifie si fichier doit être copié vers HTML."""
    # v24.0 : Ignorer fichiers commentaires
    if fichiers.doit_filtrer_fichier(fichier.name):
        return False
    
    # Reste logique existante
    return pdf.est_fichier_copiable(fichier, EXTENSIONS_COPIABLES)
```

---

## FONCTION copier_fichiers_site() - MODIFIER

**Localisation** : Ligne ~440

**DANS LA BOUCLE**, UTILISER FILTRE :

```python
def copier_fichiers_site() -> None:
    """Copie fichiers DOCUMENTS → HTML."""
    log("Copie fichiers vers HTML")
    
    for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
        # Ignorer dossiers __*
        dirs[:] = [d for d in dirs if not d.startswith("__") and d not in IGNORER]
        
        rel_path = Path(racine).relative_to(DOSSIER_DOCUMENTS)
        cible_rel_norm = Path(*(normaliser_nom(part) for part in rel_path.parts))
        cible = Path(DOSSIER_HTML) / cible_rel_norm
        cible.mkdir(parents=True, exist_ok=True)
        
        for fichier in files:
            src_file = Path(racine) / fichier
            
            # === NOUVEAU v24.0 : Filtrer commentaires ===
            if fichiers.doit_filtrer_fichier(fichier):
                continue
            
            if pdf.est_fichier_copiable(src_file, EXTENSIONS_COPIABLES):
                dst_file = cible / normaliser_nom(fichier)
                shutil.copy2(src_file, dst_file)
```

---

## CONFIG.py - AJOUTER

**Fichier** : `lib1/config.py`

```python
CONFIG = {
    # ... existant ...
    
    # v24.0 : Partitions musicales
    "player_url": "/musique/index.html",  # GitHub : "/Hebreu4.0/html/musique/index.html"
}
```

---

## VERSION - METTRE À JOUR

**Ligne 3** :

```python
version = ("genere_site.py", "24.0")
```

**Docstring** :

```python
"""
Générateur de site statique - Version 24.0

Nouveautés v24.0:
- Fichiers commentaires (__*) ignorés
- Partitions musicales avec boutons YouTube
- Lecteur musical /musique/index.html
- Regénération forcée via lancer.cmd regenere_tout

...
"""
```

---

## RÉSUMÉ MODIFICATIONS

| Fonction | Modification | Lignes |
|----------|-------------|---------|
| Imports | Ajouter fichier_utils, partition_utils | ~50 |
| generer_pdf_manquants() | Phase 2 partitions | ~220-280 |
| mettre_a_jour_structure() | Filtre commentaires | ~310 |
| copier_fichiers_site() | Filtre commentaires | ~445 |
| Version | 23.5 → 24.0 | 3 |

---

## TESTS

Après modifications :

```python
# Test imports
python -c "from lib1 import fichier_utils; print('OK')"
python -c "from lib1 import partition_utils; print('OK')"

# Test filtrage
python -c "from lib1.fichier_utils import est_fichier_commentaire; print(est_fichier_commentaire('__notes.txt'))"  # True
python -c "from lib1.fichier_utils import est_fichier_commentaire; print(est_fichier_commentaire('__partition_Ave.docx'))"  # False
```

---

## FICHIER COMPLET

Si trop complexe de modifier, un fichier `genere_site_v24.0.py` complet sera fourni dans le package ZIP.
