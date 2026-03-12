# INSTALLATION VERSION 24.0 - PACKAGE COMPLET

**Date** : Février 2026  
**Version** : 24.0  
**Auteur** : Assistant Claude + Votre nom

---

## 🎯 NOUVEAUTÉS VERSION 24.0

### Fonctionnalités ajoutées

1. **Regénération forcée PDF** : `lancer.cmd regenere_tout`
2. **Fichiers commentaires** : `__*.xxx` ignorés (sauf partitions)
3. **Partitions musicales** : Boutons YouTube intégrés
4. **Lecteur musical** : Page `/musique/index.html` avec titre vidéo
5. **Bulles d'aide** : Tooltips CSS dans style.css

---

## 📦 CONTENU DU PACKAGE

### Scripts principaux (prog/)

```
prog/
├── genere_site.py (v24.0)              # Génération site
├── cree_table_des_matieres.py (v6.29)  # TDM
├── docx_to_pdf.py                      # Conversion PDFCreator
├── conversion_pdf.py                   # Wrapper conversion
├── regenerer_tous_pdf.py               # Utilitaire regénération
├── corriger_structures.py (v2.0)       # Utilitaire maintenance
└── lancer.cmd (v2.0)                   # Script lancement
```

### Modules lib1/

```
prog/lib1/
├── config.py (v3.0)
├── options.py (v1.1)
├── html_utils.py (v1.0)
├── structure_utils.py (v2.0)
├── pdf_utils.py (v1.1)
├── fichier_utils.py (v1.0)            # NOUVEAU - Filtrage fichiers
├── partition_utils.py (v1.0)          # NOUVEAU - Partitions YouTube
└── style.css (v4.2)                    # Mis à jour - Bulles
```

### Templates

```
documents/
├── entete_general.html
├── pied_general.html
├── TDM/
│   └── entete_general.html
└── musique/
    ├── entete.html                     # NOUVEAU
    └── STRUCTURE.py                    # NOUVEAU
```

---

## 🚀 INSTALLATION COMPLÈTE

### Étape 1 : Sauvegarde

```batch
cd C:\SiteGITHUB\Hebreu4.0

REM Créer sauvegarde
mkdir backup_v23
xcopy /E /I prog backup_v23\prog
xcopy /E /I documents backup_v23\documents
```

### Étape 2 : Extraction package

```batch
REM Extraire site-hebreu-v24.0.zip dans un dossier temporaire
cd C:\Temp
unzip site-hebreu-v24.0.zip

REM Copier fichiers
xcopy /E /Y site-hebreu-v24.0\* C:\SiteGITHUB\Hebreu4.0\
```

### Étape 3 : Structure manuelle

**Placer les fichiers selon cette structure** :

#### Scripts prog/

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog

REM Scripts principaux
copy package\prog\genere_site_v24.0.py genere_site.py
copy package\prog\cree_table_des_matieres_v6.29.py cree_table_des_matieres.py
copy package\prog\docx_to_pdf.py docx_to_pdf.py
copy package\prog\conversion_pdf.py conversion_pdf.py
copy package\prog\regenerer_tous_pdf.py regenerer_tous_pdf.py
copy package\prog\corriger_structures_v2.0.py corriger_structures.py
copy package\prog\lancer_v2.0.cmd lancer.cmd
```

#### Modules lib1/

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog\lib1

copy package\lib1\config_v3.0.py config.py
copy package\lib1\options_v1.1.py options.py
copy package\lib1\html_utils.py html_utils.py
copy package\lib1\structure_utils_v2.0.py structure_utils.py
copy package\lib1\pdf_utils_v1.1.py pdf_utils.py
copy package\lib1\fichier_utils.py fichier_utils.py
copy package\lib1\partition_utils.py partition_utils.py
copy package\lib1\style_v4.2.css style.css
```

#### Templates documents/

```batch
cd C:\SiteGITHUB\Hebreu4.0\documents

REM Créer dossier musique
mkdir musique
copy package\documents\musique\entete.html musique\entete.html
copy package\documents\musique\STRUCTURE.py musique\STRUCTURE.py
```

---

## 🔧 CONFIGURATION

### 1. Vérifier options.py

**Fichier** : `prog/lib1/options.py`

```python
# Pour local
BASE_PATH = ""
DOSSIER_DOCUMENTS = r"C:\SiteGITHUB\Hebreu4.0\documents"
DOSSIER_HTML = r"C:\SiteGITHUB\Hebreu4.0\html"

# Pour GitHub Pages
BASE_PATH = "/Hebreu4.0/html"
DOSSIER_DOCUMENTS = r"C:\SiteGITHUB\Hebreu4.0\documents"
DOSSIER_HTML = r"C:\SiteGITHUB\Hebreu4.0\html"
```

### 2. Vérifier config.py

**Fichier** : `prog/lib1/config.py`

```python
CONFIG = {
    "titre_site": "Hébreu biblique",
    "regeneration": False,  # True pour forcer regénération
    "regenerer_pdf_aujourd_hui": False,  # Évite boucle
    # ...
}
```

---

## 🎵 UTILISATION PARTITIONS

### Structure dossier partition

```
documents/MonDossier/
├── __partition_Ave Maria.docx      # Source partition
├── __correspondance.csv            # Mapping YouTube
└── autres_fichiers.docx
```

### Format __correspondance.csv

```csv
pdf_name,youtube_url
ave_maria.pdf,https://youtube.com/watch?v=dQw4w9WgXcQ
cantique.pdf,https://youtube.com/watch?v=ABC123XYZ
```

**Notes** :
- `pdf_name` : Nom final PDF (normalisé, sans `__partition_`)
- `youtube_url` : Lien YouTube complet

### Workflow génération

```
1. __partition_Ave Maria.docx
   ↓ Conversion DOCX→PDF
2. __partition_ave_maria.pdf (temporaire)
   ↓ Ajout boutons YouTube
3. ave_maria.pdf (final dans html/)
   ✓ Avec boutons YouTube + Jouer ici
```

---

## 📝 UTILISATION

### Génération normale

```batch
cd C:\SiteGITHUB\Hebreu4.0
prog\lancer.cmd
```

### Regénération forcée tous PDF

```batch
cd C:\SiteGITHUB\Hebreu4.0
prog\lancer.cmd regenere_tout
```

**Confirmation demandée** : Supprime TOUS les PDF existants

---

## ✅ TESTS POST-INSTALLATION

### Test 1 : Import modules

```batch
cd C:\SiteGITHUB\Hebreu4.0\prog
python -c "from fichier_utils import est_fichier_commentaire; print('OK')"
python -c "from partition_utils import HAS_PDF_LIBS; print('OK' if HAS_PDF_LIBS else 'INSTALL LIBS')"
```

### Test 2 : Génération

```batch
prog\lancer.cmd
```

**Vérifier dans generation.log** :
```
✓ Conversion PDF disponible (PDFCreator)
✓ Modules partitions disponibles
Fichiers commentaires ignorés : 5
Partitions traitées : 3
```

### Test 3 : Page musique

1. Créer partition avec correspondance
2. Générer site
3. Ouvrir PDF partition → Cliquer "Jouer ici"
4. Vérifier page `/musique/index.html` :
   - Titre vidéo affiché
   - Lecteur YouTube fonctionnel

---

## 🐛 DÉPANNAGE

### Problème : "pypdf manquant"

```batch
pip install pypdf reportlab
```

### Problème : Partitions pas générées

**Vérifier** :
1. `__correspondance.csv` existe
2. Format CSV correct
3. PDF source existe (converti depuis DOCX)

### Problème : Lecteur musique vide

**Vérifier** :
1. URL : `/musique/index.html?v=VIDEO_ID`
2. Vidéo YouTube publique
3. Console navigateur (F12) pour erreurs

---

## 📊 FICHIERS COMMENTAIRES

### Règles

| Fichier | Traité ? | Raison |
|---------|----------|--------|
| `Leçon.docx` | ✅ Oui | Normal |
| `__notes.txt` | ❌ Non | Commentaire |
| `__todo.md` | ❌ Non | Commentaire |
| `__partition_Ave.docx` | ✅ Oui | Exception partition |
| `__correspondance.csv` | ✅ Oui | Exception mapping |

### Dans STRUCTURE.py

Les fichiers commentaires **n'apparaissent jamais** dans STRUCTURE.py.

---

## 🎨 BULLES D'AIDE (Tooltips)

### Syntaxe HTML

```html
<span class="tooltip">Texte survolable
    <span class="tooltiptext">Texte de la bulle</span>
</span>
```

### Exemple

```html
<p>Le mot <span class="tooltip">שָׁלוֹם
    <span class="tooltiptext">Paix, tranquillité</span>
</span> signifie paix.</p>
```

**Styling** : Déjà dans `style.css` v4.2

---

## 📖 DOCUMENTATION COMPLÈTE

Voir fichiers :
- `METHODOLOGIE_SITE.md` : Documentation projet complète
- `MIGRATION_PDFCREATOR.md` : Migration vers PDFCreator
- `GUIDE_V24.0.md` : Guide utilisateur v24.0

---

## 🎉 CONCLUSION

**Version 24.0** est une **mise à jour majeure** :

✅ Partitions musicales avec YouTube
✅ Lecteur musical intégré
✅ Filtrage fichiers commentaires
✅ Regénération forcée
✅ Bulles d'aide CSS

**Le générateur est maintenant complet et production-ready !** 🚀

---

**Support** : [Votre email/contact]  
**Dernière mise à jour** : Février 2026
