# remplace_v21.py — Version 21
# v21 : suppression docx de prog\ (remplacés par HTML dans manuels\)
#        fix extraire_version pour HTML (cherche meta version)
# v20 : correction banner, fix backslashes
# v19 : scan package\manuels\ → manuels\
# v18 : tiebreaker date (src plus recent = copie forcee)
# v17 : decouvrir() garde la version MAX (tri numerique)
# v16 : creation html\Hebreu4.0\html\ + copie style.css
# v15 : scan recursif de package/prog (sous-dossiers = modules reutilisables)
#        dossiers 'archive' et 'ancien' ignores
#        cree prog/ et prog/lib/ s'ils n'existent pas (1er deploiement)
# v14 : liste auto-generee (plus de liste codee en dur), lib1 -> lib
# v13 : cree_table_des_matieres v6.32, genere_site v25.5
#
# CONVENTION DE NOMMAGE (source -> cible) :
#   package/prog/fichier_vX.Y.ext          -> prog/fichier.ext
#   package/prog/lib/fichier_vX.Y.ext      -> prog/lib/fichier.ext
#   package/prog/utils/fichier_vX.Y.ext    -> prog/utils/fichier.ext
#   package/prog/lib_xxx_vX.Y.py           -> prog/lib/xxx.py  (compat. ancienne conv.)
#   package/prog/archive/...               -> IGNORE
#   package/prog/ancien/...                -> IGNORE
#
# Usage : python remplace.py  (depuis n'importe quel dossier)

import shutil
import sys
import re
from pathlib import Path

version = ("remplace.py", "21")

# ─────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────
RACINE = Path("C:/SiteGITHUB/Hebreu4.0")
SRC    = RACINE / "package" / "prog"
DST    = RACINE / "prog"
LIB    = DST / "lib"

# Fichiers a exclure du deploiement (docs remplacees par HTML dans manuels\)
EXCLURE_DEST = {
    DST / "guide_maj_github.docx",
    DST / "sync_dossiers_doc.docx",
}

# Noms de dossiers ignores lors du scan recursif
DOSSIERS_IGNORES = {"archive", "ancien", "__pycache__"}

# Fichiers cibles optionnels (absence non bloquante)
OPTIONNELS = {"remplace.py", "versions.py"}

# Anciens fichiers/dossiers a supprimer a la 1ere execution
SUPPRIMER = [
    DST / "Place_Bouton_PDF.py",
    DST / "place_bouton_v01.py",
    DST / "lib1",                  # ancien dossier renomme en lib
    LIB / "config.py",             # ancien shim elimine
    LIB / "options.py",            # ancien shim elimine
    RACINE / "manuel",             # ancien nom renomme en manuels
    DST / "guide_maj_github.docx", # remplace par manuels\maj_github\guide_utilisateur.html
    DST / "sync_dossiers_doc.docx",# remplace par manuels\sync_dossiers\guide.html
]

# Extensions deployees
EXT_GEREES = {".py", ".cmd", ".css", ".yaml", ".docx", ".md", ".txt"}

# Ignorés dans prog/ pour le rapport "non repertories"
IGNORER_EXT = {".pyc", ".pyo", ".log"}
IGNORER_NOM = {"__pycache__", "__init__.py"}

# Regex : suffixe de version en fin de stem (_vX, _vX.Y, _vX_Y)
_RE_VER = re.compile(r'_v(\d+(?:[._]\d+)*)$', re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────
# MANUELS (meme convention que prog)
# ─────────────────────────────────────────────────────────────────────
MANUELS_SRC = RACINE / "package" / "manuels"
MANUELS_DST = RACINE / "manuels"

# Extensions HTML uniquement pour les manuels
EXT_MANUELS = {".html", ".css", ".js"}

# Fichiers racine des manuels (pas de prefixe lib_)
OPTIONNELS_MANUELS = {"index.html", "serveur_manuels.py", "serveur_manuels.cmd"}


# ─────────────────────────────────────────────────────────────────────
# AUTO-DECOUVERTE (recursive)
# ─────────────────────────────────────────────────────────────────────

def _cible(fichier: Path) -> tuple | None:
    """
    Deduit (chemin_cible, obligatoire) depuis le chemin source.

    Cas 1 — fichier a la RACINE de SRC avec prefixe lib_ :
        SRC/lib_xxx_vX.Y.py  ->  DST/lib/xxx.py    (compat. ancienne convention)

    Cas 2 — fichier dans un SOUS-DOSSIER de SRC :
        SRC/subdir/fichier_vX.Y.ext  ->  DST/subdir/fichier.ext  (miroir)

    Cas 3 — fichier a la RACINE de SRC sans prefixe lib_ :
        SRC/fichier_vX.Y.ext  ->  DST/fichier.ext
    """
    if fichier.suffix not in EXT_GEREES:
        return None
    m = _RE_VER.search(fichier.stem)
    if not m:
        return None

    base = fichier.stem[:m.start()]   # nom sans _vX.Y
    ext  = fichier.suffix
    rel  = fichier.relative_to(SRC)   # chemin relatif depuis SRC

    depth = len(rel.parts) - 1        # 0 = racine, 1 = sous-dossier, ...

    if depth == 0:
        # Fichier direct dans SRC
        if base.lower().startswith("lib_"):
            cible = LIB / (base[4:] + ext)    # lib_xxx -> lib/xxx
        else:
            cible = DST / (base + ext)
    else:
        # Sous-dossier : miroir de la structure
        sous_chemin = rel.parent      # ex: lib/ ou utils/
        cible = DST / sous_chemin / (base + ext)

    oblig = cible.name not in OPTIONNELS
    # Exclure les docx de documentation (deployes dans manuels\ en HTML)
    if cible in EXCLURE_DEST:
        return None
    return cible, oblig


def _ver_tuple(ver_str: str) -> tuple:
    """Convertit '1.11' -> (1,11), '4.2' -> (4,2) pour comparaison numerique."""
    try:
        return tuple(int(x) for x in re.split(r'[._]', ver_str))
    except Exception:
        return (0,)


def decouvrir() -> list:
    """
    Scan recursif de SRC.
    - Ignore les dossiers dans DOSSIERS_IGNORES.
    - Par nom de base cible, ne garde que le fichier a la VERSION MAX.
      (evite que v1.11 < v1.9 en tri alphabetique)
    - Retourne [(nom_src_relatif, chemin_cible, obligatoire)] tries par cible.
    """
    # dict : chemin_cible -> (nom_src_relatif, ver_str, obligatoire)
    meilleurs: dict[Path, tuple] = {}

    def _walk(dossier: Path):
        for item in sorted(dossier.iterdir()):
            if item.is_dir():
                if item.name.lower() not in DOSSIERS_IGNORES:
                    _walk(item)
                continue
            r = _cible(item)
            if r is None:
                continue
            cible, oblig = r
            m = _RE_VER.search(item.stem)
            ver = m.group(1) if m else "0"
            src_rel = str(item.relative_to(SRC))

            if cible not in meilleurs:
                meilleurs[cible] = (src_rel, ver, oblig)
            else:
                _, ver_actuel, _ = meilleurs[cible]
                if _ver_tuple(ver) > _ver_tuple(ver_actuel):
                    meilleurs[cible] = (src_rel, ver, oblig)

    _walk(SRC)
    return sorted(
        [(src, cible, oblig) for cible, (src, _, oblig) in meilleurs.items()],
        key=lambda x: str(x[1])
    )

def decouvrir_manuels() -> list:
    """
    Scan recursif de MANUELS_SRC.
    Convention : sous-dossier/_general/fichier_vX.Y.html
                  → MANUELS_DST/sous-dossier/_general/fichier.html
    Meme logique que decouvrir() : version MAX par nom de base.
    Fichiers sans suffixe _vX.Y (index.html, serveur*) deployés tels quels.
    """
    meilleurs: dict = {}

    def _walk_m(dossier: Path):
        for item in sorted(dossier.iterdir()):
            if item.is_dir():
                if item.name.lower() not in DOSSIERS_IGNORES:
                    _walk_m(item)
                continue
            if item.suffix not in EXT_MANUELS:
                continue

            rel  = item.relative_to(MANUELS_SRC)
            m    = _RE_VER.search(item.stem)

            if m:
                # fichier versionne → retire le suffixe de version
                base = item.stem[:m.start()]
                ver  = m.group(1)
                cible = MANUELS_DST / rel.parent / (base + item.suffix)
                oblig = cible.name not in OPTIONNELS_MANUELS
            else:
                # fichier sans version (index.html, serveur*) → copie directe
                base  = item.stem
                ver   = "0"
                cible = MANUELS_DST / rel
                oblig = cible.name not in OPTIONNELS_MANUELS

            src_rel = str(item.relative_to(MANUELS_SRC))
            if cible not in meilleurs:
                meilleurs[cible] = (src_rel, ver, oblig)
            else:
                _, ver_actuel, _ = meilleurs[cible]
                if _ver_tuple(ver) > _ver_tuple(ver_actuel):
                    meilleurs[cible] = (src_rel, ver, oblig)

    if MANUELS_SRC.exists():
        _walk_m(MANUELS_SRC)

    return sorted(
        [(src, cible, oblig) for cible, (src, _, oblig) in meilleurs.items()],
        key=lambda x: str(x[1])
    )


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def extraire_version(chemin: Path) -> str:
    try:
        txt = chemin.read_text(encoding="utf-8", errors="ignore")
        if chemin.suffix == ".html":
            import re as _re
            m = _re.search(r"<td>Version</td>\s*<td>([0-9.]+)</td>", txt)
            if m:
                return m.group(1)
            return "?"
        idx = txt.find("version = (")
        if idx >= 0:
            sub = txt[idx:idx+80]
            m = re.search(r"['\"]([0-9][0-9.]*)['\"]", sub[sub.find(","):])
            if m:
                return m.group(1)
        m = re.search(r"[Vv]ersion +([0-9][0-9.]*)", txt[:400])
        if m:
            return m.group(1)
    except Exception:
        pass
    return "?"


def afficher(statut, src_r, dst_r, vs="", vd="", note=""):
    cs  = str(src_r)[:42].ljust(42)
    cd  = str(dst_r)[:30].ljust(30)
    ver = f"  v{vs} -> v{vd}" if (vs or vd) else ""
    nt  = f"  [{note}]" if note else ""
    print(f"  {statut:<8} {cs} -> {cd}{ver}{nt}")


def rel(p: Path) -> Path:
    try:    return p.relative_to(RACINE)
    except: return p


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 76)
    print(f"  remplace.py v{version[1]}  —  deploiement automatique (scan recursif)")
    print(f"  Source : {SRC}")
    print(f"  Cible  : {DST}")
    print("=" * 76)

    erreurs = copies = a_jour = 0

    # Verifier SRC
    if not SRC.exists():
        print(f"  ERREUR : dossier source introuvable : {SRC}")
        sys.exit(1)

    # Creer DST et LIB si absent (1er deploiement)
    for d in (DST, LIB):
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"  CREE    {rel(d)}\\")

    # ── Auto-decouverte ───────────────────────────────────────────────
    FICHIERS = decouvrir()
    print()
    print(f"  {len(FICHIERS)} fichier(s) decouvert(s) dans {rel(SRC)}")
    print()
    print("  DEPLOIEMENT")
    print()

    # Index des cibles connues par dossier (pour rapport "non repertories")
    cibles_par_dossier: dict[Path, set] = {}

    for nom_src, chemin_dst, obligatoire in FICHIERS:
        chemin_src = SRC / nom_src
        parent = chemin_dst.parent
        cibles_par_dossier.setdefault(parent, set()).add(chemin_dst.name)

        if not chemin_src.exists():
            note = "OBLIGATOIRE" if obligatoire else "optionnel"
            afficher("ABSENT", rel(chemin_src), rel(chemin_dst), note=note)
            if obligatoire:
                erreurs += 1
            continue

        vs = extraire_version(chemin_src)
        vd = extraire_version(chemin_dst) if chemin_dst.exists() else "—"

        # Copier si : version differente OU source plus recente que cible
        # (cas d'un fichier modifie sans changement de version)
        src_mtime = chemin_src.stat().st_mtime
        dst_mtime = chemin_dst.stat().st_mtime if chemin_dst.exists() else 0
        src_plus_recent = src_mtime > dst_mtime + 2   # tolerance 2s

        if vs != vd:
            raison = ""
        elif src_plus_recent:
            raison = "src plus recent"
        else:
            raison = None   # a jour

        if raison is None:
            afficher("OK",    rel(chemin_src), rel(chemin_dst), vs, vd, "a jour")
            a_jour += 1
        else:
            chemin_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(chemin_src), str(chemin_dst))
            afficher("COPIE", rel(chemin_src), rel(chemin_dst), vs, vd,
                     raison if raison else "")
            copies += 1

    # ── Suppressions ─────────────────────────────────────────────────
    print()
    print("  SUPPRESSIONS (anciens fichiers)")
    print()
    for chemin in SUPPRIMER:
        chemin = Path(chemin)
        if chemin.is_dir():
            shutil.rmtree(str(chemin))
            print(f"  SUPPRIME {rel(chemin)}\\  (dossier)")
        elif chemin.exists():
            chemin.unlink()
            print(f"  SUPPRIME {rel(chemin)}")
        else:
            print(f"  ABSENT   {rel(chemin)}  (deja supprime)")

    # ── Rapport fichiers non repertories ─────────────────────────────
    def inconnus_dans(dossier: Path, connus: set) -> list:
        if not dossier.exists():
            return []
        res = []
        for f in dossier.iterdir():
            if f.is_dir() or f.suffix in IGNORER_EXT or f.name in IGNORER_NOM:
                continue
            if f.name not in connus:
                res.append(f)
        return sorted(res)

    total_inconnus = 0
    premiere_ligne = True
    for dossier, connus in sorted(cibles_par_dossier.items()):
        inc = inconnus_dans(dossier, connus)
        if inc:
            if premiere_ligne:
                print()
                print("  FICHIERS NON REPERTORIES (a verifier / supprimer manuellement)")
                print()
                premiere_ligne = False
            prefix = str(rel(dossier)) + "\\"
            for f in inc:
                print(f"  ?? {prefix}{f.name:<44}  v{extraire_version(f)}")
            total_inconnus += len(inc)

    if premiere_ligne:
        print()
        print("  Aucun fichier non repertorie dans prog\\ et sous-dossiers")

    # ── Deploiement manuels\ ─────────────────────────────────────────
    if MANUELS_SRC.exists():
        FICHIERS_MANUELS = decouvrir_manuels()
        print()
        print(f"  {len(FICHIERS_MANUELS)} manuel(s) decouvert(s) dans {rel(MANUELS_SRC)}")
        print()
        print("  DEPLOIEMENT MANUELS")
        print()

        for nom_src, chemin_dst, obligatoire in FICHIERS_MANUELS:
            chemin_src = MANUELS_SRC / nom_src
            if not chemin_src.exists():
                afficher("ABSENT", rel(chemin_src), rel(chemin_dst),
                         note="OBLIGATOIRE" if obligatoire else "optionnel")
                if obligatoire:
                    erreurs += 1
                continue

            vs = extraire_version(chemin_src)
            vd = extraire_version(chemin_dst) if chemin_dst.exists() else "—"
            src_mtime = chemin_src.stat().st_mtime
            dst_mtime = chemin_dst.stat().st_mtime if chemin_dst.exists() else 0
            src_plus_recent = src_mtime > dst_mtime + 2

            if vs != vd:
                raison = ""
            elif src_plus_recent:
                raison = "src plus recent"
            else:
                raison = None

            if raison is None:
                afficher("OK",    rel(chemin_src), rel(chemin_dst), vs, vd, "a jour")
                a_jour += 1
            else:
                chemin_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(chemin_src), str(chemin_dst))
                afficher("COPIE", rel(chemin_src), rel(chemin_dst), vs, vd,
                         raison if raison else "")
                copies += 1
    else:
        print()
        print(f"  INFO : {rel(MANUELS_SRC)} absent — manuels non deployes")

    # ── Structure html\ pour node.js local ──────────────────────────
    # html\Hebreu4.0\html\style.css est requis pour la consultation locale
    # (node.js sert html\ mais le CSS est genere dans prog\ par genere_site)
    style_src = DST / "style.css"
    style_dst_dir = RACINE / "html" / "Hebreu4.0" / "html"
    style_dst = style_dst_dir / "style.css"

    print()
    print("  STRUCTURE HTML (consultation locale node.js)")
    print()
    if not style_src.exists():
        print("  ABSENT   prog" + chr(92) + "style.css — copie impossible (lancer remplace.py apres le 1er deploiement)")
    else:
        style_dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(style_src), str(style_dst))
        print("  OK       html" + chr(92) + "Hebreu4.0" + chr(92) + "html" + chr(92) + "style.css cree/mis a jour")

    # ── Bilan ─────────────────────────────────────────────────────────
    print()
    print("=" * 76)
    if erreurs:
        print(f"  ATTENTION : {erreurs} erreur(s) — voir ABSENT OBLIGATOIRE ci-dessus")
    else:
        extra = f"   {total_inconnus} non repertorie(s)" if total_inconnus else ""
        print(f"  OK : {copies} copie(s)   {a_jour} deja a jour{extra}")
    print("=" * 76)
    print()

    sys.exit(1 if erreurs else 0)


if __name__ == "__main__":
    main()

# fin remplace.py — Version 15
