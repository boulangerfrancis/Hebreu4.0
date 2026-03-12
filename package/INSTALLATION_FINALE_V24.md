# INSTALLATION FINALE v24.0

## ✅ FICHIERS INSTALLÉS

Vous avez déjà installé :
- ✅ Tous scripts prog/ (sauf genere_site.py)
- ✅ Tous modules lib1/
- ✅ Dossier documents/musique/

---

## 📥 FICHIER MANQUANT

**genere_site_v24.0.py** → Copier vers `prog/genere_site.py`

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog
copy genere_site_v24.0.py genere_site.py
```

---

## 🗂️ DOSSIERS IMBRIQUÉS

### Structure typique

```
documents/
├── Grammaire/
│   ├── Lecons/              ← Imbriqué niveau 2
│   │   ├── __partition_*.docx
│   │   ├── __correspondance.csv
│   │   └── Leçon01.docx
│   └── Exercices/
│       └── Exercice01.docx
├── Chants/                  ← Ou à la racine
│   ├── __partition_Ave.docx
│   └── __correspondance.csv
└── musique/
    ├── entete.html
    └── STRUCTURE.py
```

### ✅ Fonctionnement automatique

Le générateur **parcourt récursivement** tous les sous-dossiers :

```python
# Dans main()
for racine, dirs, files in os.walk(DOSSIER_DOCUMENTS):
    # Traite TOUS les dossiers, y compris imbriqués
```

**Donc** :
- `documents/Lecons/` → ✅ Traité
- `documents/Grammaire/Lecons/` → ✅ Traité
- `documents/Niveau1/Grammaire/Lecons/` → ✅ Traité

**Aucune configuration nécessaire !**

---

## 🎵 EXEMPLE PARTITION IMBRIQUÉE

### documents/Grammaire/Chants/__correspondance.csv

```csv
pdf_name,youtube_url
ave_maria.pdf,https://youtube.com/watch?v=dQw4w9WgXcQ
```

### documents/Grammaire/Chants/__partition_Ave Maria.docx

Source partition

### Résultat

```
html/grammaire/chants/
└── ave_maria.pdf  ← Avec boutons YouTube
```

---

## ⚙️ CONFIGURATION PLAYER_URL

### Si dossiers imbriqués

**Le player URL reste ABSOLU** :

```python
# lib1/config.py

# Local
"player_url": "/musique/index.html"

# GitHub
"player_url": "/Hebreu4.0/html/musique/index.html"
```

**Même si la partition est dans** `documents/Niveau1/Grammaire/Chants/`, le bouton "Jouer ici" pointera vers `/musique/index.html` (racine du site).

---

## 🚀 TEST COMPLET

### 1. Vérifier fichiers

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog

REM Vérifier genere_site.py v24.0
findstr "Version 24.0" genere_site.py
REM Doit afficher : # genere_site.py — Version 24.0

REM Vérifier imports
findstr "fichier_utils" genere_site.py
findstr "partition_utils" genere_site.py
```

### 2. Test imports Python

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog
python -c "from lib1.fichier_utils import est_fichier_commentaire; print('OK')"
python -c "from lib1.partition_utils import HAS_PDF_LIBS; print('OK' if HAS_PDF_LIBS else 'MANQUANT')"
```

**Si "MANQUANT"** :
```batch
pip install pypdf reportlab
```

### 3. Génération test

```batch
cd C:\SiteGITHUB\Hebreu4.0
prog\lancer.cmd
```

**Vérifier dans generation.log** :
```
=== GÉNÉRATION SITE STATIQUE v24.0 ===
✓ Conversion PDF disponible (PDFCreator)
✓ Modules partitions disponibles (pypdf + reportlab)
PHASE 1 : GÉNÉRATION PDF + PARTITIONS + STRUCTURE.py
```

### 4. Test partition (si applicable)

Si vous avez des `__partition_*.docx` :

1. Créer `__correspondance.csv` dans le même dossier
2. Regénérer : `prog\lancer.cmd`
3. Vérifier PDF final a 2 boutons en bas

---

## 🐛 DÉPANNAGE

### Problème : "fichier_utils non trouvé"

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog\lib1
dir fichier_utils.py
```

Si absent → Copier depuis package

### Problème : "partition_utils non trouvé"

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog\lib1
dir partition_utils.py
```

Si absent → Copier depuis package

### Problème : Partitions pas traitées

**Vérifier** :
1. `__correspondance.csv` existe dans le dossier
2. Format CSV correct (voir exemple ci-dessus)
3. `pip install pypdf reportlab` exécuté

### Problème : Fichiers `__*` copiés dans html/

**Symptôme** : Fichiers comme `__notes.txt` présents dans `html/`

**Cause** : Ancien `genere_site.py`

**Solution** : Vérifier version :
```batch
findstr "Version 24.0" prog\genere_site.py
```

---

## 📊 VÉRIFICATION FINALE

### Fichiers prog/

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog
dir *.py *.cmd
```

**Doit contenir** :
- genere_site.py (v24.0)
- cree_table_des_matieres.py
- docx_to_pdf.py
- conversion_pdf.py
- regenerer_tous_pdf.py
- corriger_structures.py
- generer_page_musique.py
- lancer.cmd

### Fichiers lib1/

```batch
cd lib1
dir *.py *.css
```

**Doit contenir** :
- config.py
- options.py
- html_utils.py
- structure_utils.py
- pdf_utils.py
- fichier_utils.py ⭐
- partition_utils.py ⭐
- style.css

### Dossier musique

```batch
cd ..\..\ documents\musique
dir
```

**Doit contenir** :
- entete.html
- STRUCTURE.py

---

## 🎉 CONCLUSION

**Installation complète v24.0** :

✅ genere_site.py v24.0
✅ Tous modules installés
✅ Dossiers imbriqués supportés
✅ Partitions musicales fonctionnelles
✅ Lecteur musical opérationnel

**Vous êtes prêt !** 🚀

---

## 📞 PROCHAINES ÉTAPES

1. Tester génération : `prog\lancer.cmd`
2. Vérifier log pas d'erreurs
3. Si partitions : Créer `__correspondance.csv`
4. Tester boutons YouTube
5. Déployer sur GitHub Pages

---

**Version** : 24.0 finale  
**Date** : Février 2026  
**Statut** : Production Ready

Bon développement ! 🎵
