#!/usr/bin/env python3
# generer_page_musique.py — Version 1.0
"""
Génère la page /musique/index.html pour le lecteur YouTube.

Usage:
    python generer_page_musique.py

Génère automatiquement musique/index.html avec:
- En-tête général du site
- Lecteur YouTube dynamique
- Récupération titre vidéo
- Pied général du site
"""

from pathlib import Path
import sys

# Ajouter lib1 au path
sys.path.insert(0, str(Path(__file__).parent / "lib1"))

from lib1.options import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH
from lib1 import html_utils as html

def generer_page_musique():
    """Génère la page musique/index.html."""
    print("Génération page musique...")
    
    # Chemins
    musique_docs = Path(DOSSIER_DOCUMENTS) / "musique"
    musique_html = Path(DOSSIER_HTML) / "musique"
    
    # Créer dossier
    musique_html.mkdir(parents=True, exist_ok=True)
    
    # Template page
    template = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8"/>
    <title>Lecteur Musical</title>
    <link href="{BASE_PATH}/style.css" rel="stylesheet"/>
    <style>
        .video-container {{
            max-width: 800px;
            margin: 40px auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        
        .video-title {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .video-player {{
            position: relative;
            padding-bottom: 56.25%;
            height: 0;
            overflow: hidden;
            border-radius: 8px;
        }}
        
        .video-player iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
        }}
        
        .error-message {{
            text-align: center;
            padding: 40px;
            color: #e74c3c;
            font-size: 18px;
        }}
    </style>
</head>
<body>

"""
    
    # Entête général
    entete_gen = musique_docs.parent / "entete_general.html"
    if entete_gen.exists():
        template += html.charger_template_html(
            entete_gen,
            {"BASE_PATH": BASE_PATH},
            False
        )
    
    # Entête local
    entete_local = musique_docs / "entete.html"
    if entete_local.exists():
        with open(entete_local, "r", encoding="utf-8") as f:
            template += f.read()
    
    # Lecteur
    template += """
<div class="video-container">
    <div id="video-title" class="video-title">Chargement...</div>
    <div id="video-content">
        <div style="text-align: center; padding: 40px; color: #7f8c8d;">⏳ Chargement...</div>
    </div>
</div>

"""
    
    # Pied général
    pied_gen = musique_docs.parent / "pied_general.html"
    if pied_gen.exists():
        template += html.charger_template_html(
            pied_gen,
            {"BASE_PATH": BASE_PATH},
            False
        )
    
    # JavaScript
    template += """
<script>
function getVideoId() {
    const params = new URLSearchParams(window.location.search);
    return params.get('v');
}

async function getVideoTitle(videoId) {
    try {
        const response = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
        if (!response.ok) throw new Error('Vidéo introuvable');
        const data = await response.json();
        return data.title;
    } catch (error) {
        return null;
    }
}

async function init() {
    const videoId = getVideoId();
    const titleEl = document.getElementById('video-title');
    const contentEl = document.getElementById('video-content');
    
    if (!videoId) {
        titleEl.textContent = 'Aucune vidéo sélectionnée';
        contentEl.innerHTML = '<div class="error-message">Aucun identifiant vidéo fourni.</div>';
        return;
    }
    
    const title = await getVideoTitle(videoId);
    
    if (title === null) {
        titleEl.textContent = 'Vidéo indisponible';
        contentEl.innerHTML = '<div class="error-message">⚠️ Désolé, mais l\\'accès à cette vidéo est impossible actuellement.<br><br>La vidéo a peut-être été supprimée ou rendue privée sur YouTube.</div>';
        return;
    }
    
    titleEl.textContent = title;
    contentEl.innerHTML = `
        <div class="video-player">
            <iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
            </iframe>
        </div>
    `;
}

init();
</script>

</body>
</html>
"""
    
    # Sauvegarder
    output_file = musique_html / "index.html"
    output_file.write_text(template, encoding="utf-8")
    
    print(f"✓ Page générée : {output_file}")

if __name__ == "__main__":
    generer_page_musique()
