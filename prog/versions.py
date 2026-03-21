# versions_v1.8.py — Version 1.8
# v1.8 : maj_github 1.17, remplace 21
# v1.7 : fix config.yaml parser, version HTML, escape warnings
# v1.6 : settings 1.1, builder 1.2, tdm minuscules
# v1.5 : installer 1.1
# v1.4 : maj_github 1.16
# v1.3 : maj_github 1.15
# v1.2 : liste dynamique
#        tous les fichiers deployes sont verifies automatiquement
#        ajout conversion_pdf, documents, docx_to_pdf (manquants en v1.1)
# v1.1 : ajout verification config.yaml (champs, token GitHub via API)
#        ajout fichiers maj_github, sync_dossiers, lancer.cmd
# v1.0 : affichage versions modules Python
"""
Usage :
    python versions.py  (depuis prog/)
"""

version = ("versions.py", "1.8")

import ast
import re
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

PROG_DIR = Path(__file__).parent
LIB_DIR  = PROG_DIR / "lib"

# Champs obligatoires dans config.yaml
CONFIG_CHAMPS_OBLIG = [
    "racine_source",
    "racine_site_local",
    "lancer_cmd",
    "url_github",
    "branche",
    "github_token",
    "github_user",
]

# Versions minimales attendues pour les fichiers Python principaux
# (None = existence suffisante, pas de version minimale)
VERSIONS_MIN = {
    "genere_site.py":             "25.6",
    "settings.py":                "1.1",
    "documents.py":               "2.2",
    "musique.py":                 "1.14",
    "builder.py":                 "1.2",
    "docx_to_pdf.py":             "1.3",
    "cree_table_des_matieres.py": "6.33",
    "normalisation_utils.py":     "1.0",
    "place_bouton.py":            "1.1",
    "maj_github.py":              "1.17",
    "installer.py":               "1.1",
    "sync_dossiers.py":           "1.1",
    "conversion_pdf.py":          "1.0",
    # lib/
    "lib/partition_utils.py":     None,
    "lib/structure_utils.py":     None,
    "lib/html_utils.py":          None,
    "lib/fichier_utils.py":       None,
    "lib/pdf_utils.py":           None,
}


# ─────────────────────────────────────────────────────────────────────
# SCAN DYNAMIQUE
# ─────────────────────────────────────────────────────────────────────

def scanner_fichiers() -> list[tuple[str, str | None, str]]:
    """
    Scanne prog/ et prog/lib/ et retourne la liste :
      [(chemin_relatif, version_minimale, description)]
    Le chemin_relatif est relatif a PROG_DIR.
    """
    fichiers = []
    # Fichiers .py dans prog/
    for f in sorted(PROG_DIR.glob("*.py")):
        rel = f.name
        ver_min = VERSIONS_MIN.get(rel)
        desc = _description(f)
        fichiers.append((rel, ver_min, desc))
    # Fichiers .py dans prog/lib/
    if LIB_DIR.exists():
        for f in sorted(LIB_DIR.glob("*.py")):
            rel = f"lib/{f.name}"
            ver_min = VERSIONS_MIN.get(rel)
            desc = _description(f)
            fichiers.append((rel, ver_min, desc))
    return fichiers


def _description(chemin: Path) -> str:
    """Extrait la description depuis le commentaire de la 2e ligne."""
    try:
        lignes = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
        for ligne in lignes[:4]:
            ligne = ligne.strip().lstrip("#").strip()
            if not ligne:
                continue
            # Ignorer la ligne de version/nom
            if re.match(r'[\w\./]+\.py\s*[—-]', ligne):
                continue
            if re.match(r'[Vv]ersion', ligne):
                continue
            if len(ligne) > 10:
                return ligne[:60]
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────────────────────────────
# HELPERS VERSIONS
# ─────────────────────────────────────────────────────────────────────

def lire_version(chemin: Path):
    """Extrait le tuple version d'un fichier .py sans l'importer."""
    if not chemin.exists():
        return None, "ABSENT"
    try:
        src  = chemin.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except Exception as e:
        return None, f"ERREUR LECTURE: {e}"

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id.lower() not in ("version", "__version__"):
                continue
            val = node.value
            if isinstance(val, ast.Tuple) and len(val.elts) == 2:
                try:
                    nom_fich = ast.literal_eval(val.elts[0])
                    ver_str  = ast.literal_eval(val.elts[1])
                    return nom_fich, ver_str
                except Exception:
                    pass
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                return chemin.name, val.value

    # Fallback commentaires
    for line in src.splitlines()[:5]:
        m = re.search(r'[Vv]ersion\s*[:\-]?\s*([\d.]+)', line)
        if m:
            return chemin.name, m.group(1)

    return chemin.name, "?"


def comparer_versions(ver: str, ver_min: str) -> bool:
    def t(v):
        try: return tuple(int(x) for x in str(v).split("."))
        except: return (0,)
    return t(ver) >= t(ver_min)


def lire_version_cmd(chemin: Path) -> str:
    if not chemin.exists():
        return "ABSENT"
    try:
        src = chemin.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'[Vv]ersion\s+([\d.]+)', src)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "?"


def lire_version_html(chemin: Path) -> str:
    """Extrait la version depuis un fichier HTML manuel.
    Cherche <td>X.Y</td> apres une cellule 'Version'.
    """
    if not chemin.exists():
        return "ABSENT"
    try:
        src = chemin.read_text(encoding="utf-8", errors="replace")
        # Format : <td>Version</td><td>X.Y</td>
        m = re.search(r'[Vv]ersion</td>\s*<td>([\d.]+)</td>', src)
        if m:
            return m.group(1)
        # Format dans l'info-table: <td>Version</td><td>X.Y</td>
        m = re.search(r'<td>Version</td><td>([\d.]+)</td>', src)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "?"


# ─────────────────────────────────────────────────────────────────────
# VERIFICATION CONFIG.YAML
# ─────────────────────────────────────────────────────────────────────

def lire_config_yaml(chemin: Path) -> dict:
    """
    Parse config.yaml au format 'cle = valeur' (pas du YAML standard).
    PyYAML echoue sur ce format car il utilise = au lieu de :.
    On utilise directement le parser simple.
    """
    if not chemin.exists():
        return {}
    cfg = {}
    try:
        for ligne in chemin.read_text(encoding="utf-8", errors="replace").splitlines():
            ligne = ligne.split("#")[0].strip()
            if "=" not in ligne:
                continue
            cle, _, val = ligne.partition("=")
            cle = cle.strip()
            val = val.strip()
            if cle:
                cfg[cle] = val
    except Exception:
        pass
    return cfg


def verifier_config(cfg: dict) -> list:
    resultats = []
    for champ in CONFIG_CHAMPS_OBLIG:
        val = cfg.get(champ, "")
        if not val:
            resultats.append(("MANQUANT", champ, "champ absent de config.yaml"))
        elif val.startswith("ghp_VOTRE") or val in (
                "VOTRE_NOM_UTILISATEUR_GITHUB", "ghp_VOTRE_TOKEN_ICI",
                "C:\\chemin\\source", "C:\\chemin\\destination"):
            resultats.append(("MODELE", champ, f"valeur modele non remplacee : {val!r}"))
        else:
            display = val[:8] + "***" if champ == "github_token" else val
            resultats.append(("OK", champ, display))
    return resultats


# ─────────────────────────────────────────────────────────────────────
# TEST TOKEN GITHUB
# ─────────────────────────────────────────────────────────────────────

def tester_token_github(user: str, token: str) -> tuple:
    if not token or token.startswith("ghp_VOTRE"):
        return False, "Token non renseigne dans config.yaml"
    if not user:
        return False, "github_user non renseigne dans config.yaml"

    url = "https://api.github.com/user"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "versions.py/1.2")

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data  = json.loads(resp.read().decode("utf-8"))
            login = data.get("login", "")
            repos = data.get("public_repos", "?")
            if login.lower() == user.lower():
                return True, f"Token valide — utilisateur={login}, repos publics={repos}"
            return False, (f"Token valide MAIS login GitHub={login!r} "
                           f"!= github_user config={user!r}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Token invalide ou expire (HTTP 401)"
        if e.code == 403:
            return False, "Permissions insuffisantes (HTTP 403) — cocher 'repo'"
        return False, f"Erreur HTTP {e.code} : {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Pas de connexion internet : {e.reason}"
    except Exception as e:
        return False, f"Erreur inattendue : {e}"


# ─────────────────────────────────────────────────────────────────────
# AFFICHAGE ANSI
# ─────────────────────────────────────────────────────────────────────

VERT  = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
BLEU  = "\033[94m"
RESET = "\033[0m"
GRAS  = "\033[1m"

def C(t, c): return f"{c}{t}{RESET}"

def ic(statut):
    return {
        "OK":       C("✓", VERT),
        "ABSENT":   C("✗", ROUGE),
        "ERREUR":   C("✗", ROUGE),
        "ATTENTION": C("△", JAUNE),
        "?":        C("?", JAUNE),
    }.get(statut, statut)


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def main():
    nb_ok = nb_att = nb_err = 0

    print()
    print(C("=" * 68, BLEU))
    print(C(f"  VERIFICATION DU PROJET — {PROG_DIR}", GRAS))
    print(C("=" * 68, BLEU))

    # ── 1. Modules Python (scan dynamique) ───────────────────────────
    fichiers_py = scanner_fichiers()
    print()
    print(C(f"  {'MODULE':<38} {'VERSION':<10} {'MIN':<8} STATUT", GRAS))
    print(f"  {'-'*38} {'-'*10} {'-'*8} {'-'*14}")

    for rel, ver_min, desc in fichiers_py:
        chemin = PROG_DIR / rel
        _, ver = lire_version(chemin)

        if ver == "ABSENT":
            statut = "ABSENT"
            nb_err += 1
        elif ver_min and ver not in ("?", None):
            if comparer_versions(ver, ver_min):
                statut = "OK";  nb_ok += 1
            else:
                statut = "ATTENTION"; nb_att += 1
        else:
            if chemin.exists():
                statut = "OK";  nb_ok += 1
            else:
                statut = "ABSENT"; nb_err += 1

        i = ic(statut)
        vm = ver_min or ""
        attn = C(f" ← attendu >={ver_min}", JAUNE) if statut == "ATTENTION" else ""
        print(f"  {i} {rel:<36} {str(ver):<10} {vm:<8}{attn}")

    # ── 2. Autres fichiers ────────────────────────────────────────────
    print()
    print(C(f"  {'AUTRES FICHIERS':<38} {'VERSION':<10} STATUT", GRAS))
    print(f"  {'-'*38} {'-'*10} {'-'*12}")

    autres = [
        ("lancer.cmd",         "Lanceur site local / generation", True),
        ("config.yaml",        "Configuration personnelle",       True),
        ("style.css",          "Feuille de style",                True),
        ("remplace.py",        "Deploiement package->prog",       False),
        ("MAJ_GITHUB.cmd",     "Lancement mise a jour GitHub",    False),
        ("guide_maj_github.docx",    "Guide maj GitHub",          False),
        ("sync_dossiers_doc.docx",   "Guide sync dossiers",       False),
    ]

    for rel, desc, oblig in autres:
        chemin = PROG_DIR / rel
        ext = Path(rel).suffix
        if ext in (".cmd", ".css"):
            ver = lire_version_cmd(chemin)
        elif ext == ".yaml":
            ver = "—"
        elif ext in (".docx", ".md"):
            ver = "—"
        elif ext == ".html":
            ver = lire_version_html(chemin)
        else:
            _, ver = lire_version(chemin)

        if not chemin.exists():
            statut = "ABSENT" if oblig else "?"
            nb_err += 1 if oblig else 0
        else:
            statut = "OK"; nb_ok += 1

        note = desc if statut != "OK" else ""
        print(f"  {ic(statut)} {rel:<36} {str(ver):<10} {note}")

    # ── 3. Config.yaml ────────────────────────────────────────────────
    config_path = PROG_DIR / "config.yaml"
    print()
    print(C("  CONFIG.YAML", GRAS))
    print(f"  {'-'*60}")

    token_ok = user_ok = False

    if not config_path.exists():
        print(f"  {ic('ABSENT')} config.yaml — ABSENT")
        nb_err += 1
    else:
        cfg = lire_config_yaml(config_path)
        for statut, champ, detail in verifier_config(cfg):
            if statut == "OK":
                i = ic("OK"); nb_ok += 1
                if champ == "github_token": token_ok = True
                if champ == "github_user":  user_ok  = True
            elif statut == "MODELE":
                i = C("△", JAUNE); nb_att += 1
            else:
                i = ic("ABSENT"); nb_err += 1
            print(f"  {i} {champ:<28} {detail}")

    # ── 4. Token GitHub ───────────────────────────────────────────────
    print()
    print(C("  TOKEN GITHUB", GRAS))
    print(f"  {'-'*60}")

    if not config_path.exists():
        print(f"  {ic('ABSENT')} config.yaml absent — test impossible")
        nb_err += 1
    elif not token_ok or not user_ok:
        print(f"  {C('△', JAUNE)} Token ou utilisateur non configure — test ignore")
        nb_att += 1
    else:
        cfg = lire_config_yaml(config_path)
        print("  Test de connexion a GitHub...", end=" ", flush=True)
        ok, msg = tester_token_github(cfg.get("github_user", ""),
                                      cfg.get("github_token", ""))
        if ok:
            print(f"\n  {ic('OK')} {msg}"); nb_ok += 1
        else:
            print(f"\n  {ic('ABSENT')} {msg}"); nb_err += 1

    # ── 5. Bilan ──────────────────────────────────────────────────────
    print()
    print(C("=" * 68, BLEU))
    total = nb_ok + nb_att + nb_err
    if nb_err == 0 and nb_att == 0:
        bilan = C(f"  TOUT EST OK  ({nb_ok}/{total})", VERT + GRAS)
    elif nb_err == 0:
        bilan = C(f"  ATTENTION  ({nb_ok} OK, {nb_att} a verifier, 0 erreur)",
                  JAUNE + GRAS)
    else:
        bilan = C(f"  PROBLEMES DETECTES  ({nb_err} erreur(s), {nb_att} attention(s), {nb_ok} OK)",
                  ROUGE + GRAS)
    print(bilan)
    print(C("=" * 68, BLEU))
    print()

    return 0 if nb_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# fin de versions_v1.8.py — Version 1.8
