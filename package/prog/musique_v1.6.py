# musique.py — Version 1.6
# v1.6 : bord et sens_texte passes a ajouter_boutons_partition + params_signature
# v1.5 : player YouTube IFrame API (remplace iframe simple bloquee)
# v1.4 : patch chirurgical STRUCTURE.py
"""
v1.3 :
  - Refactorisation majeure : parametres partitions stockes dans STRUCTURE.py
    sous la cle "partitions" (liste de dicts)
  - Plus de fichier .params sur le disque
  - CSV lu UNE SEULE FOIS (ou si plus recent que STRUCTURE.py)
  - doit_regenerer_partition() base sur params_signature dans STRUCTURE.py
  - B) Regles regeneration PDF identiques aux PDF ordinaires (CONFIG)
  - A) Ne jamais ecraser les fichiers existants dans documents/musique/
  - C) Player iframe + fallback "Ouvrir sur YouTube"

  Structure "partitions" dans STRUCTURE.py :
    "partitions": [
        {
            "nom_docx"        : "__partition_L'auvergnat.docx",
            "nom_pdf_source"  : "__partition_l_auvergnat.pdf",
            "nom_html"        : "l_auvergnat.pdf",
            "nom_affiche"     : "L'auvergnat de Brassens",
            "video_id"        : "morcvF-aFsg",
            "orientation"     : "H",
            "fond_opacite_pct": 100.0,
            "x"               : null,
            "y"               : null,
            "params_signature": "morcvF-aFsg|H|100.0|None|None"
        }
    ]
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional

version = ("musique.py", "1.6")
print(f"[Import] {version[0]} - Version {version[1]} charge")

from lib1 import partition_utils as partitions
from lib1 import structure_utils as struct
from settings import DOSSIER_DOCUMENTS, DOSSIER_HTML, BASE_PATH, CONFIG

_pu_ver = getattr(partitions, "version", ("?", "?"))
print(f"  [musique] partition_utils : v{_pu_ver[1]}")

NOM_DOSSIER_MUSIQUE = "musique"


# ============================================================================
# TEMPLATES HTML
# ============================================================================

def _template_entete_player() -> str:
    """Player YouTube via IFrame Player API (pas de cle requise).

    L'API YouTube IFrame Player API est chargee depuis youtube.com/iframe_api.
    Elle gere automatiquement l'autoplay, les restrictions CORS et le fallback.
    Le parametre ?v=VIDEO_ID est lu dans l'URL de la page.
    """
    return """<!-- entete.html — Player YouTube IFrame API -->
<div class="monTitre">&#127925; Lecteur Musical</div>
<div id="player-zone" style="display:flex;flex-direction:column;align-items:center;padding:20px;gap:16px;">

  <!-- Conteneur player API -->
  <div id="yt-player-container" style="
      width:100%; max-width:800px; aspect-ratio:16/9;
      background:#111; border-radius:8px; overflow:hidden;
      box-shadow:0 4px 16px rgba(0,0,0,.3); display:none;">
    <div id="yt-player"></div>
  </div>

  <!-- Fallback lien direct -->
  <div id="fallback-zone" style="display:none; text-align:center; padding:20px;">
    <p style="color:#888; margin-bottom:12px;">
      Le lecteur integre n'est pas disponible ici.
    </p>
    <a id="yt-link" href="#" target="_blank" rel="noopener"
       style="display:inline-block; background:#FF0000; color:#fff;
              padding:12px 28px; border-radius:6px; text-decoration:none;
              font-weight:bold; font-size:1.05em;">
      &#9654; Ouvrir sur YouTube
    </a>
  </div>

  <p id="no-video-msg" style="color:#888; font-style:italic;">
    Aucune video selectionnee. Cliquez sur &#127925; &laquo;Jouer ici&raquo; depuis une partition.
  </p>
</div>

<!-- YouTube IFrame Player API — gratuite, sans cle -->
<script>
(function() {
  var params  = new URLSearchParams(window.location.search);
  var videoId = params.get('v');
  var noMsg   = document.getElementById('no-video-msg');
  var container = document.getElementById('yt-player-container');
  var fallback  = document.getElementById('fallback-zone');
  var ytLink    = document.getElementById('yt-link');

  if (!videoId) return;

  noMsg.style.display = 'none';
  ytLink.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(videoId);

  // Charger l'API YouTube IFrame Player
  var tag = document.createElement('script');
  tag.src = 'https://www.youtube.com/iframe_api';
  var firstScript = document.getElementsByTagName('script')[0];
  firstScript.parentNode.insertBefore(tag, firstScript);

  var playerReady = false;
  var timeoutId   = null;

  // Callback appele par l'API quand elle est chargee
  window.onYouTubeIframeAPIReady = function() {
    clearTimeout(timeoutId);
    container.style.display = 'block';

    new YT.Player('yt-player', {
      width: '100%',
      height: '100%',
      videoId: videoId,
      playerVars: {
        autoplay: 1,
        rel: 0,
        modestbranding: 1
      },
      events: {
        onReady: function(e) {
          playerReady = true;
          e.target.playVideo();
        },
        onError: function() {
          container.style.display  = 'none';
          fallback.style.display   = 'block';
        }
      }
    });
  };

  // Fallback si l'API ne se charge pas en 5s (mode hors-ligne / bloque)
  timeoutId = setTimeout(function() {
    if (!playerReady) {
      container.style.display = 'none';
      fallback.style.display  = 'block';
    }
  }, 5000);

})();
</script>
"""


def _template_entete_general() -> str:
    return """<!-- entete_general.html musique -->
<div style="text-align:center; color:#7f8c8d; font-size:.95em; padding:8px 0 0 0;">
  Cliquez sur &#127925; &ldquo;Jouer ici&rdquo; depuis une partition pour lancer la musique
</div>
"""


def _template_structure_musique() -> str:
    return """# STRUCTURE.py — Dossier musique
# Cree automatiquement si absent. Modifiable manuellement.
# La cle "partitions" est geree par musique.py — ne pas modifier a la main.

STRUCTURE = {
    "titre_dossier"   : "Lecteur Musical",
    "nom_navigation"  : "Musique",
    "titre_table"     : "",
    "entete_general"  : True,
    "pied_general"    : True,
    "entete"          : True,
    "pied"            : False,
    "navigation"      : False,
    "haut_page"       : False,
    "bas_page"        : False,
    "ajout_affichage" : False,
    "affiche_index"   : False,
    "affiche_TDM"     : False,
    "dossiers"        : [],
    "fichiers"        : [],
    "partitions"      : []
}
"""


# ============================================================================
# INIT DOSSIER MUSIQUE
# ============================================================================

def initialiser_dossier_musique(log_func) -> Path:
    """Cree le dossier musique/ et ses fichiers UNIQUEMENT s'ils sont absents.

    Ne touche jamais aux fichiers existants (modifications manuelles preservees).
    """
    dossier = Path(DOSSIER_DOCUMENTS) / NOM_DOSSIER_MUSIQUE
    crees   = []

    if not dossier.exists():
        dossier.mkdir(parents=True)
        crees.append("dossier musique/")

    for nom, contenu in [
        ("entete.html",          _template_entete_player()),
        ("entete_general.html",  _template_entete_general()),
        ("STRUCTURE.py",         _template_structure_musique()),
    ]:
        dest = dossier / nom
        if not dest.exists():
            dest.write_text(contenu, encoding="utf-8")
            crees.append(nom)

    if crees:
        log_func(f"  Musique : crees -> {', '.join(crees)}")
    else:
        log_func(f"  Musique : dossier existant conserve")

    return dossier


# ============================================================================
# NORMALISATION NOM PARTITION
# ============================================================================

def _normaliser(texte: str) -> str:
    """Minusc. sans accents, espaces et apostrophes -> underscore."""
    t = unicodedata.normalize('NFD', texte)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = t.replace("'", "_").replace("\u2019", "_").replace(" ", "_").lower()
    return t


def nom_partition_depuis_docx(nom_docx: str):
    """Calcule (nom_lisible, nom_html) depuis __partition_*.docx."""
    sans_prefix = nom_docx
    for prefix in ("__partition_", "__partition _"):
        if nom_docx.lower().startswith(prefix.lower()):
            sans_prefix = nom_docx[len(prefix):]
            break
    stem        = Path(sans_prefix).stem
    nom_lisible = stem
    nom_html    = _normaliser(stem) + ".pdf"
    return (nom_lisible, nom_html)


# ============================================================================
# GESTION CLE "partitions" DANS STRUCTURE.py
# ============================================================================

def lire_partitions_structure(dossier: Path) -> List[dict]:
    """Lit la liste 'partitions' du STRUCTURE.py du dossier.
    Retourne [] si absente ou erreur.
    """
    s = struct.charger_structure(dossier)
    return s.get("partitions", [])


def sauvegarder_partitions_structure(dossier: Path, liste: List[dict],
                                      log_func) -> None:
    """Patche UNIQUEMENT la cle 'partitions' dans STRUCTURE.py.

    Toutes les autres cles et valeurs manuelles sont preservees.
    Si la cle 'partitions' n'existe pas, elle est ajoutee A LA FIN
    du dict STRUCTURE, avant le } fermant.

    Strategie : lecture texte + remplacement regex de la valeur de 'partitions'.
    Si absent : injection avant la derniere ligne de fermeture.
    """
    fichier = dossier / "STRUCTURE.py"
    if not fichier.exists():
        log_func("  ⚠ STRUCTURE.py absent, impossible de patcher")
        return

    import json, re

    # Serialiser la liste en Python valide
    val_json = json.dumps(liste, ensure_ascii=False, indent=4)
    val_py   = val_json.replace("true",  "True") \
                       .replace("false", "False") \
                       .replace("null",  "None")
    # Indenter pour s'integrer dans le dict STRUCTURE (4 espaces)
    val_indente = val_py.replace("\n", "\n    ")

    contenu = fichier.read_text(encoding="utf-8")

    # Cas 1 : cle 'partitions' deja presente -> remplacer sa valeur
    # Pattern : "partitions" : [...] ou "partitions": [...]
    pattern = r'("partitions"\s*:\s*)\[.*?\]'
    remplacement = r'\g<1>' + val_indente

    nouveau, nb = re.subn(pattern, remplacement, contenu, flags=re.DOTALL)
    if nb > 0:
        fichier.write_text(nouveau, encoding="utf-8")
        log_func(f"  STRUCTURE.py : cle 'partitions' mise a jour ({len(liste)} entree(s))")
        return

    # Cas 2 : cle absente -> injecter avant la derniere accolade fermante
    # Trouver la derniere ligne contenant "}" ou "})" du dict STRUCTURE
    lignes = contenu.splitlines()
    idx_insertion = None
    for i in range(len(lignes) - 1, -1, -1):
        stripped = lignes[i].strip()
        if stripped in ("}", "})"):
            idx_insertion = i
            break

    if idx_insertion is None:
        log_func("  ⚠ Structure STRUCTURE.py non reconnue, partition non sauvegardee")
        return

    ligne_partition = f'    "partitions"      : {val_indente}'
    # Ajouter une virgule a la ligne precedente si elle n'en a pas
    if idx_insertion > 0:
        prev = lignes[idx_insertion - 1].rstrip()
        if prev and not prev.endswith(","):
            lignes[idx_insertion - 1] = prev + ","

    lignes.insert(idx_insertion, ligne_partition)
    fichier.write_text("\n".join(lignes), encoding="utf-8")
    log_func(f"  STRUCTURE.py : cle 'partitions' ajoutee ({len(liste)} entree(s))")


def _signature_depuis_params(p: dict) -> str:
    return partitions.params_signature(
        p["video_id"], p["orientation"], p["fond_opacite_pct"],
        p.get("x"), p.get("y")
    )


def _csv_plus_recent_que_structure(dossier: Path) -> bool:
    """Vrai si __correspondance.csv est plus recent que STRUCTURE.py."""
    csv_p = dossier / "__correspondance.csv"
    str_p = dossier / "STRUCTURE.py"
    if not csv_p.exists():
        return False
    if not str_p.exists():
        return True
    return csv_p.stat().st_mtime > str_p.stat().st_mtime


def synchroniser_partitions_csv(dossier: Path, log_func) -> List[dict]:
    """Lit le CSV et met a jour la cle 'partitions' dans STRUCTURE.py.

    Appele seulement si CSV plus recent que STRUCTURE.py ou si
    une partition du dossier n'est pas encore dans STRUCTURE.py.

    Conserve les params_signature existantes pour les partitions inchangees.
    Retourne la liste mise a jour.
    """
    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return lire_partitions_structure(dossier)

    corresp = partitions.charger_correspondances(csv_path)
    if not corresp:
        return lire_partitions_structure(dossier)

    # Charger partitions existantes (indexees par nom_html)
    existantes = {p["nom_html"]: p for p in lire_partitions_structure(dossier)}

    nouvelle_liste = []
    for nom_html, params in corresp.items():
        video_id         = params["video_id"]
        orientation      = params.get("orientation", "V")
        fond_opacite_pct = params.get("fond_opacite_pct", 0.0)
        pos_x            = params.get("x")
        pos_y            = params.get("y")

        # Chercher le DOCX source dans le dossier
        nom_docx    = None
        nom_affiche = Path(nom_html).stem  # fallback
        for f in dossier.iterdir():
            if not f.is_file() or f.suffix.lower() not in ('.doc', '.docx'):
                continue
            nl = f.name.lower()
            if not (nl.startswith("__partition_") or nl.startswith("__partition _")):
                continue
            lisible, html_calcule = nom_partition_depuis_docx(f.name)
            if html_calcule == nom_html:
                nom_docx    = f.name
                nom_affiche = lisible
                break

        nom_pdf_source = None
        if nom_docx:
            # Le PDF source porte le meme nom normalise que le DOCX
            nom_pdf_source = "__partition_" + _normaliser(
                Path(nom_docx[len("__partition_"):] if
                     nom_docx.lower().startswith("__partition_") else nom_docx).stem
            ) + ".pdf"

        bord_val       = params.get("bord", 0)
        sens_texte_val = params.get("sens_texte", 0)
        sig = partitions.params_signature(
            video_id, orientation, fond_opacite_pct, pos_x, pos_y,
            bord_val, sens_texte_val)

        entree = {
            "nom_docx"        : nom_docx or "",
            "nom_pdf_source"  : nom_pdf_source or "",
            "nom_html"        : nom_html,
            "nom_affiche"     : nom_affiche,
            "video_id"        : video_id,
            "orientation"     : orientation,
            "fond_opacite_pct": fond_opacite_pct,
            "x"               : pos_x,
            "y"               : pos_y,
            "bord"            : bord_val,
            "sens_texte"      : sens_texte_val,
            "params_signature": sig,
        }
        nouvelle_liste.append(entree)

    sauvegarder_partitions_structure(dossier, nouvelle_liste, log_func)
    return nouvelle_liste


# ============================================================================
# TRAITEMENT PARTITIONS
# ============================================================================

def traiter_partitions_du_dossier(dossier: Path, log_func) -> int:
    """Ajoute boutons YouTube aux partitions PDF du dossier.

    Workflow :
    1. Si CSV plus recent que STRUCTURE.py -> synchroniser_partitions_csv()
    2. Lire liste "partitions" depuis STRUCTURE.py
    3. Pour chaque partition : regenerer si params_signature a change
       OU si __partition_*.pdf source est plus recent que PDF final (regle B)

    Args:
        dossier : Dossier a traiter
        log_func: Fonction de log
    Returns:
        Nombre de partitions traitees
    """
    if not getattr(partitions, "HAS_PDF_LIBS", False):
        return 0

    csv_path = dossier / "__correspondance.csv"
    if not csv_path.exists():
        return 0

    # Synchroniser si CSV plus recent ou partitions absentes de STRUCTURE
    liste_partitions = lire_partitions_structure(dossier)
    if _csv_plus_recent_que_structure(dossier) or not liste_partitions:
        log_func(f"  Lecture CSV partitions : {dossier.name}")
        liste_partitions = synchroniser_partitions_csv(dossier, log_func)

    if not liste_partitions:
        log_func("  ⚠ Aucune partition trouvee")
        return 0

    player_url = CONFIG.get("player_url",
                            f"{BASE_PATH}/{NOM_DOSSIER_MUSIQUE}/index.html")
    force = CONFIG.get("regeneration", False)
    nb    = 0

    for p in liste_partitions:
        nom_html        = p["nom_html"]
        nom_pdf_source  = p.get("nom_pdf_source", "")
        video_id        = p["video_id"]
        orientation     = p.get("orientation", "V")
        fond_opacite    = p.get("fond_opacite_pct", 0.0)
        pos_x           = p.get("x")
        pos_y           = p.get("y")
        bord            = p.get("bord", 0)
        sens_texte      = p.get("sens_texte", 0)
        sig_stockee     = p.get("params_signature", "")
        sig_actuelle    = partitions.params_signature(
                            video_id, orientation, fond_opacite, pos_x, pos_y,
                            bord, sens_texte)

        pdf_source = dossier / nom_pdf_source if nom_pdf_source else None
        # Fallback : chercher __partition_*.pdf correspondant
        if not pdf_source or not pdf_source.exists():
            pdf_source = None
            for f in dossier.iterdir():
                if not f.is_file() or f.suffix.lower() != ".pdf":
                    continue
                nl = f.name.lower()
                if not (nl.startswith("__partition_") or nl.startswith("__partition _")):
                    continue
                _, html_calcule = nom_partition_depuis_docx(f.stem + ".docx")
                if html_calcule == nom_html:
                    pdf_source = f
                    break

        if not pdf_source:
            log_func(f"  ⚠ Source PDF introuvable : {nom_html}")
            continue

        pdf_final = dossier / nom_html

        # Determiner si regeneration necessaire (Regle B)
        regenerer = force
        if not regenerer:
            if not pdf_final.exists():
                regenerer = True
            elif pdf_source.stat().st_mtime > pdf_final.stat().st_mtime:
                regenerer = True
            elif sig_actuelle != sig_stockee:
                regenerer = True

        if not regenerer:
            log_func(f"  ✓ Partition a jour : {nom_html}")
            continue

        raison = "force" if force else \
                 "absente" if not pdf_final.exists() else \
                 "source modifie" if pdf_source.stat().st_mtime > pdf_final.stat().st_mtime \
                 else "params changes"
        log_func(f"  🎵 {pdf_source.name} -> {nom_html}  ({raison})")

        ok = partitions.ajouter_boutons_partition(
            pdf_source, pdf_final, player_url, video_id,
            orientation=orientation, fond_opacite_pct=fond_opacite,
            pos_x=pos_x, pos_y=pos_y,
            bord=bord, sens_texte=sens_texte,
        )
        if ok:
            # Mettre a jour la signature dans STRUCTURE.py
            p["params_signature"] = sig_actuelle
            nb += 1
        else:
            log_func(f"  ✗ Echec : {nom_html}")

    # Sauvegarder les signatures mises a jour
    if nb > 0:
        sauvegarder_partitions_structure(dossier, liste_partitions, log_func)

    return nb

# Fin musique.py v1.6
