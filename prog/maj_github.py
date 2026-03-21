# maj_github_v1.17.py — Version 1.17
# Mise a jour automatique du site GitHub :
#   1) Synchronisation des fichiers sources modifies (sync_dossiers.py)
#   2) Generation du site statique (lancer.cmd nolocal — sans serveur node)
#   3) Commit + Push vers GitHub
# v1.17 : fix SyntaxWarning backslash dans docstring _trouver_git_ghd
# v1.16 : utilise le git de GitHub Desktop pour le push
#         git systeme bloque par Windows Firewall en sous-process Python
#         git GHD a les bons credentials + reseau + permissions
# v1.15 : Popen streaming
# v1.14 : git push nu, zero interference credential
#         GCM (GitHub Desktop) gere le renouvellement automatique
#         fallback http.extraheader si config.yaml a un token valide
# v1.12 : verification token GitHub via API avant push
# v1.11 : URL avec token passee directement a git push
#         du credential manager (core.askpass/GCM ouvrait /dev/tty)
# v1.10 : http.extraheader (insuffisant, core.askpass non neutralise)
# v1.9 : http.extraheader + credential.helper vide = contourne Credential Manager
#         (le manager ouvrait un browser OAuth et bloquait)
#         si pas de token : credential.helper laisse en place (GitHub Desktop)
# v1.8 : GIT_ASKPASS Python (obsolete - contourne pas le credential manager)
# v1.7 : authentification via GIT_ASKPASS + token dans config.yaml
#        evite le conflit Credential Manager entre plusieurs utilisateurs
#        le token n'apparait jamais dans les URLs ni dans les logs
# v1.6 : suppression token dans URL git
# v1.5 : etape 2 streaming Popen evite blocage buffer
# v1.4 : lancer.cmd appele avec argument 'nolocal'
# v1.3 : fermeture propre par croix ; confirmation optionnelle
# v1.2 : authentification GitHub via token PAT
# v1.1 : lancer.cmd remplace genere_site.py
# Usage : double-clic sur MAJ_GITHUB.cmd (qui active virpy13 puis lance ce script)

version = ("maj_github.py", "1.17")
print(f"[Import] {version[0]} - Version {version[1]} charge")

import sys
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime

# ── PyYAML optionnel ──────────────────────────────────────────────
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════
CONFIG_DEFAUT = {
    "racine_source":    "",   # dossier des fichiers editables (docx...)
    "racine_site_local": "",  # dossier racine du site local (depot git)
    "lancer_cmd":       "",   # chemin vers lancer.cmd
    "url_github":       "",   # ex: https://github.com/GuyTitt/Hebreu4.0
    "message_commit":   "auto",  # "auto" = date+heure, sinon texte fixe
    "filtre":           "",   # filtre pour sync_dossiers (vide = tout)
    "branche":          "main",
    "confirmation_git": "true",  # demander confirmation avant push
    "github_token":     "",   # Personal Access Token (ghp_...)
    "github_user":      "",   # nom utilisateur GitHub
}

def _parser_simple(texte: str) -> dict:
    result = {}
    for ligne in texte.splitlines():
        ligne = ligne.split("#")[0].strip()
        if "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        result[cle.strip()] = valeur.strip()
    return result

def lire_config(chemin: Path) -> dict:
    texte = chemin.read_text(encoding="utf-8", errors="replace")
    if HAS_YAML:
        try:
            raw = yaml.safe_load(texte) or {}
        except Exception:
            raw = _parser_simple(texte)
    else:
        raw = _parser_simple(texte)
    if not isinstance(raw, dict):
        raw = _parser_simple(texte)

    cfg = CONFIG_DEFAUT.copy()
    for cle in ("racine_source", "racine_site_local", "lancer_cmd",
                "url_github", "message_commit", "filtre", "branche",
                "confirmation_git",
                "github_token", "github_user"):
        if cle in raw and raw[cle] is not None:
            cfg[cle] = str(raw[cle]).strip()
    return cfg

def charger_config() -> tuple:
    """Cherche config.yaml dans le dossier du script."""
    dossier_script = Path(__file__).parent
    config_path = dossier_script / "config.yaml"
    if config_path.exists():
        print(f"[Config] {config_path}")
        return lire_config(config_path), str(config_path)
    print("[Config] Aucun config.yaml trouve — configuration par defaut")
    return CONFIG_DEFAUT.copy(), "(defaut interne)"

def message_commit_auto() -> str:
    return f"Mise a jour site - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

# ══════════════════════════════════════════════════════════════════
#  ETAPES DE LA MISE A JOUR
# ══════════════════════════════════════════════════════════════════
ETAPES = [
    ("sync",    "Synchronisation des fichiers sources"),
    ("genere",  "Génération du site statique"),
    ("confirm", "Confirmation avant envoi GitHub"),
    ("git",     "Commit et Push vers GitHub"),
]

def run_cmd(commande: list, cwd: str = None) -> tuple:
    """
    Execute une commande externe.
    Retourne (code_retour, stdout+stderr).
    """
    try:
        proc = subprocess.run(
            commande,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        sortie = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, sortie
    except FileNotFoundError as e:
        return -1, f"Commande introuvable : {e}"
    except Exception as e:
        return -1, f"Erreur : {e}"

# ══════════════════════════════════════════════════════════════════
#  INTERFACE TKINTER
# ══════════════════════════════════════════════════════════════════
class FenetreMaj(tk.Tk):

    COULEUR_OK      = "#1E8449"
    COULEUR_ERR     = "#C0392B"
    COULEUR_ATTENTE = "#7F8C8D"
    COULEUR_ENCOURS = "#D4AC0D"
    COULEUR_BG      = "#EAF4F4"
    COULEUR_TITRE   = "#154360"

    def __init__(self, cfg: dict, source_cfg: str):
        super().__init__()
        self.cfg = cfg
        self.source_cfg = source_cfg
        self.etape_actuelle = 0
        self.annuler = False
        self.fichiers_synchronises = []  # rempli apres sync

        self.title("Mise à jour du site GitHub")
        self.resizable(False, False)
        self.configure(bg=self.COULEUR_BG)
        self._construire_ui()
        self._centrer()

        # Lancer les etapes au demarrage dans un thread
        self.after(400, self._demarrer)

    # ── Construction UI ───────────────────────────────────────────
    def _construire_ui(self):
        PAD = dict(padx=14, pady=6)

        # Titre
        tk.Label(self, text="Mise à jour du site GitHub",
                 font=("Segoe UI", 16, "bold"),
                 fg=self.COULEUR_TITRE, bg=self.COULEUR_BG).pack(**PAD)

        # Info config
        tk.Label(self,
                 text=f"Source : {self.cfg['racine_source']}\n"
                      f"Site   : {self.cfg['racine_site_local']}\n"
                      f"GitHub : {self.cfg['url_github']}",
                 font=("Segoe UI", 9), fg="#555",
                 bg=self.COULEUR_BG, justify="left").pack(
            fill="x", padx=14, pady=2)

        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=14, pady=6)

        # Indicateurs d'étapes
        self.frm_etapes = tk.Frame(self, bg=self.COULEUR_BG)
        self.frm_etapes.pack(fill="x", padx=14, pady=4)

        self.lbl_etapes = []
        self.lbl_icones = []
        for i, (_, libelle) in enumerate(ETAPES):
            frm = tk.Frame(self.frm_etapes, bg=self.COULEUR_BG)
            frm.pack(fill="x", pady=2)
            lbl_icone = tk.Label(frm, text="○", width=2,
                                 font=("Segoe UI", 13),
                                 fg=self.COULEUR_ATTENTE, bg=self.COULEUR_BG)
            lbl_icone.pack(side="left", padx=(0, 6))
            lbl_txt = tk.Label(frm, text=libelle,
                               font=("Segoe UI", 10),
                               fg=self.COULEUR_ATTENTE, bg=self.COULEUR_BG,
                               anchor="w")
            lbl_txt.pack(side="left", fill="x", expand=True)
            self.lbl_icones.append(lbl_icone)
            self.lbl_etapes.append(lbl_txt)

        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=14, pady=6)

        # Log
        tk.Label(self, text="Journal :", font=("Segoe UI", 9, "bold"),
                 bg=self.COULEUR_BG, anchor="w").pack(
            fill="x", padx=14)
        self.log_widget = scrolledtext.ScrolledText(
            self, height=14, width=72,
            font=("Courier New", 9), bg="#1C1C1C", fg="#DDDDDD",
            state="disabled", wrap="word")
        self.log_widget.pack(padx=14, pady=4)

        # Barre de progression
        self.progressbar = ttk.Progressbar(
            self, mode="indeterminate", length=500)
        self.progressbar.pack(padx=14, pady=4)

        # Bouton fermer (désactivé pendant l'exécution)
        self.btn_fermer = tk.Button(
            self, text="Fermer",
            font=("Segoe UI", 10), padx=20, pady=6,
            bg="#BDC3C7", fg="#2C3E50",
            state="disabled",
            command=self.destroy)
        self.btn_fermer.pack(pady=8)

        self.minsize(540, 500)
        # Fermeture propre : arrêter le thread en cours
        self.protocol("WM_DELETE_WINDOW", self._on_fermer)

    # ── Fermeture propre ─────────────────────────────────────────
    def _on_fermer(self):
        """Fermeture par la croix : signaler au thread d'arrêter."""
        self.annuler = True
        self.after(200, self.destroy)

    # ── Helpers UI ────────────────────────────────────────────────
    def _log(self, msg: str, couleur: str = "#DDDDDD"):
        """Ajoute une ligne dans le log (thread-safe via after)."""
        def _do():
            self.log_widget.config(state="normal")
            self.log_widget.insert("end", msg + "\n", couleur)
            self.log_widget.tag_config(couleur, foreground=couleur)
            self.log_widget.see("end")
            self.log_widget.config(state="disabled")
        self.after(0, _do)

    def _trouver_git_ghd(self) -> str:
        """
        Cherche le git.exe bundlé par GitHub Desktop.
        Retourne le chemin complet si trouvé, sinon "git" (git système).

        GitHub Desktop installe son propre git dans :
          %LOCALAPPDATA%/GitHubDesktop/app-X.X.X/resources/app/git/cmd/git.exe
        Ce git hérite des credentials et de la config réseau de GitHub Desktop,
        ce qui évite les blocages pare-feu et les problèmes de credential manager.
        """
        import glob
        local_app = os.environ.get("LOCALAPPDATA", "")
        if not local_app:
            return "git"

        patterns = [
            os.path.join(local_app,
                "GitHubDesktop", "app-*", "resources", "app",
                "git", "cmd", "git.exe"),
            os.path.join(local_app,
                "GitHubDesktop", "app-*", "resources", "app",
                "git", "mingw64", "bin", "git.exe"),
        ]
        candidats = []
        for pattern in patterns:
            candidats.extend(glob.glob(pattern))

        if not candidats:
            return "git"

        # Prendre la version la plus recente (tri sur le chemin = tri sur app-X.X.X)
        candidats.sort(reverse=True)
        return candidats[0]

    def _lire_credential_manager(self, site: str) -> tuple:
        """
        Lit les credentials GitHub depuis le Credential Manager Windows
        via "git credential fill". Retourne (user, token) ou ("", "").
        Compatible avec GitHub Desktop qui stocke ses credentials via GCM.
        """
        try:
            proc = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=site,
                timeout=5,
            )
            if proc.returncode != 0 or not proc.stdout:
                return "", ""
            user = token = ""
            for line in proc.stdout.splitlines():
                if line.startswith("username="):
                    user = line[len("username="):].strip()
                elif line.startswith("password="):
                    token = line[len("password="):].strip()
            return user, token
        except Exception:
            return "", ""

    def _verifier_token(self, user: str, token: str) -> tuple:
        """
        Verifie le token PAT via l'API GitHub.
        Retourne (ok: bool, message: str, login: str)
        """
        import urllib.request, urllib.error, json
        url = "https://api.github.com/user"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "maj_github/1.12")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data  = json.loads(resp.read().decode("utf-8"))
                login = data.get("login", "")
                if login.lower() == user.lower():
                    return True, "OK", login
                else:
                    return False, (
                        f"Token valide mais login={login!r} != github_user={user!r} dans config.yaml"
                    ), login
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Token invalide ou expire (HTTP 401)", ""
            if e.code == 403:
                return False, "Token sans permission repo (HTTP 403) — cocher repo", ""
            return False, f"Erreur HTTP {e.code}", ""
        except Exception as e:
            return False, f"Pas de connexion : {e}", ""

    def _set_etape(self, idx: int, statut: str):
        """
        statut : 'encours' | 'ok' | 'erreur' | 'attente' | 'ignore'
        """
        icones = {
            "encours": ("➤", self.COULEUR_ENCOURS),
            "ok":      ("✔", self.COULEUR_OK),
            "erreur":  ("✘", self.COULEUR_ERR),
            "attente": ("○", self.COULEUR_ATTENTE),
            "ignore":  ("—", self.COULEUR_ATTENTE),
        }
        icone, couleur = icones.get(statut, ("○", self.COULEUR_ATTENTE))
        def _do():
            self.lbl_icones[idx].config(text=icone, fg=couleur)
            self.lbl_etapes[idx].config(fg=couleur)
        self.after(0, _do)

    def _terminer(self, succes: bool):
        def _do():
            self.progressbar.stop()
            self.progressbar.config(mode="determinate",
                                    value=100 if succes else 0)
            self.btn_fermer.config(
                state="normal",
                bg=self.COULEUR_OK if succes else self.COULEUR_ERR,
                fg="white")
        self.after(0, _do)

    def _centrer(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    # ── Orchestration ─────────────────────────────────────────────
    def _demarrer(self):
        self.progressbar.start(12)
        t = threading.Thread(target=self._run_etapes, daemon=True)
        t.start()

    def _run_etapes(self):
        try:
            ok = self._etape_sync()
            if not ok: return

            ok = self._etape_genere()
            if not ok: return

            ok = self._etape_confirmer()
            if not ok: return

            ok = self._etape_git()
            if ok:
                self._log("", "")
                self._log("╔══════════════════════════════════════╗", "#1ABC9C")
                self._log("║   Site GitHub mis à jour avec succès ║", "#1ABC9C")
                self._log("╚══════════════════════════════════════╝", "#1ABC9C")
                self._terminer(True)
        except Exception as e:
            self._log(f"Erreur inattendue : {e}", "#FF6B6B")
            self._terminer(False)

    # ── Étape 1 : Synchronisation ─────────────────────────────────
    def _etape_sync(self) -> bool:
        idx = 0
        self._set_etape(idx, "encours")
        self._log("═" * 50, "#1ABC9C")
        self._log("ÉTAPE 1 — Synchronisation des fichiers sources", "#1ABC9C")
        self._log("═" * 50, "#1ABC9C")

        # Construire le config yaml temporaire pour sync_dossiers
        dossier_script = Path(__file__).parent
        sync_script = dossier_script / "sync_dossiers.py"
        config_sync = dossier_script / "_sync_temp.yaml"

        config_sync.write_text(
            f"source      = {self.cfg['racine_source']}\n"
            f"destination = {self.cfg['racine_site_local']}\n"
            f"recent      = true\n"
            f"filtre      = {self.cfg['filtre']}\n"
            f"nouveau     = true\n",
            encoding="utf-8"
        )

        # Lancer sync_dossiers avec le yaml temporaire
        # sync_dossiers a sa propre fenetre Tkinter — on l'appelle
        # via subprocess pour eviter les conflits de mainloop
        code, sortie = run_cmd(
            [sys.executable, str(sync_script), str(config_sync)]
        )
        try:
            config_sync.unlink()
        except Exception:
            pass

        if sortie:
            for ligne in sortie.strip().split("\n"):
                couleur = "#FF6B6B" if "ERREUR" in ligne.upper() else "#DDDDDD"
                self._log(f"  {ligne}", couleur)

        # sync_dossiers retourne 0 meme si l'utilisateur annule
        # on considere l'etape OK dans tous les cas (l'utilisateur
        # a pu choisir de ne rien copier = pas de modif, site deja a jour)
        self._set_etape(idx, "ok")
        self._log("  Synchronisation terminée.", "#90EE90")
        return True

    # ── Étape 2 : Génération du site (lancer.cmd nolocal) ──────
    # Utilise Popen + readline (streaming) pour :
    #   - afficher la progression en temps réel dans le log
    #   - éviter le blocage du buffer stdout (problème avec capture_output
    #     quand genere_site.py produit beaucoup de sortie)
    def _etape_genere(self) -> bool:
        idx = 1
        self._set_etape(idx, "encours")
        self._log("", "")
        self._log("═" * 50, "#1ABC9C")
        self._log("ÉTAPE 2 — Génération du site statique", "#1ABC9C")
        self._log("═" * 50, "#1ABC9C")

        lancer = Path(self.cfg["lancer_cmd"])
        if not lancer.exists():
            self._log(f"  ERREUR : lancer.cmd introuvable : {lancer}", "#FF6B6B")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        self._log(f"  Lancement de {lancer.name} nolocal...", "#DDDDDD")

        try:
            proc = subprocess.Popen(
                ["cmd", "/c", str(lancer), "nolocal"],
                cwd=str(lancer.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # fusionner stderr dans stdout
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,                  # ligne par ligne
            )
        except Exception as e:
            self._log(f"  ERREUR lancement : {e}", "#FF6B6B")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        # Lire la sortie ligne par ligne sans bloquer le buffer
        for ligne in proc.stdout:
            if self.annuler:
                proc.terminate()
                return False
            ligne = ligne.rstrip("\n\r")
            if ligne.strip():
                couleur = "#FF6B6B" if "ERREUR" in ligne.upper() else "#DDDDDD"
                self._log(f"  {ligne}", couleur)

        proc.wait()
        code = proc.returncode

        if code != 0:
            self._log(f"  ERREUR : lancer.cmd a retourné le code {code}", "#FF6B6B")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        self._set_etape(idx, "ok")
        self._log("  Site généré avec succès.", "#90EE90")
        return True


    # ── Étape 3 : Confirmation ────────────────────────────────────
    def _etape_confirmer(self) -> bool:
        idx = 2
        self._set_etape(idx, "encours")
        self._log("", "")
        self._log("═" * 50, "#1ABC9C")
        self._log("ÉTAPE 3 — Confirmation avant envoi GitHub", "#1ABC9C")
        self._log("═" * 50, "#1ABC9C")

        # Lister les fichiers modifiés dans le depot git
        site = self.cfg["racine_site_local"]
        code, sortie = run_cmd(["git", "status", "--short"], cwd=site)
        if code != 0:
            self._log(f"  ERREUR git status : {sortie}", "#FF6B6B")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        if not sortie.strip():
            self._log("  Aucune modification détectée dans le dépôt git.", "#FFD700")
            self._log("  Le site GitHub est déjà à jour — aucun commit nécessaire.", "#FFD700")
            self._set_etape(idx, "ignore")
            self._set_etape(3, "ignore")  # etape git aussi
            self._terminer(True)
            # Fermer automatiquement apres 3s
            self.after(3000, self.destroy)
            return False   # arreter la sequence (pas une erreur)

        # Afficher la liste des fichiers
        lignes = sortie.strip().split("\n")
        self._log(f"  {len(lignes)} fichier(s) modifié(s) :", "#FFD700")
        for l in lignes:
            self._log(f"    {l}", "#DDDDDD")

        msg_commit = (message_commit_auto()
                      if self.cfg["message_commit"].lower() == "auto"
                      else self.cfg["message_commit"])

        self._log(f"\n  Message du commit : « {msg_commit} »", "#AED6F1")

        # Confirmation optionnelle (selon config)
        demander = self.cfg.get("confirmation_git", "true").lower()                    not in ("false", "non", "0", "no")

        if demander:
            resultat = {"ok": None}

            def _ask():
                rep = messagebox.askyesno(
                    "Confirmer l'envoi vers GitHub",
                    f"{len(lignes)} fichier(s) seront envoyés vers GitHub.\n\n"
                    f"Message du commit :\n« {msg_commit} »\n\n"
                    f"Dépôt : {self.cfg['url_github']}\n"
                    f"Branche : {self.cfg['branche']}\n\n"
                    "Confirmer l'envoi ?"
                )
                resultat["ok"] = rep

            self.after(0, _ask)

            import time
            while resultat["ok"] is None:
                time.sleep(0.1)

            if not resultat["ok"]:
                self._log("  Envoi annulé par l'utilisateur.", "#FFD700")
                self._set_etape(idx, "ignore")
                self._set_etape(3, "ignore")
                self._terminer(True)
                return False
        else:
            self._log("  Confirmation automatique (confirmation_git=false).", "#AED6F1")

        self._set_etape(idx, "ok")
        self._msg_commit = msg_commit
        return True

    # ── Étape 4 : Git commit + push ───────────────────────────────
    def _etape_git(self) -> bool:
        idx = 3
        self._set_etape(idx, "encours")
        self._log("", "")
        self._log("═" * 50, "#1ABC9C")
        self._log("ÉTAPE 4 — Commit et Push vers GitHub", "#1ABC9C")
        self._log("═" * 50, "#1ABC9C")

        site = self.cfg["racine_site_local"]
        branche = self.cfg["branche"]

        # git add
        self._log("  git add -A ...", "#DDDDDD")
        code, sortie = run_cmd(["git", "add", "-A"], cwd=site)
        if sortie.strip():
            self._log(f"  {sortie.strip()}", "#DDDDDD")
        if code != 0:
            self._log(f"  ERREUR git add (code {code})", "#FF6B6B")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        # git commit
        self._log(f"  git commit ...", "#DDDDDD")
        code, sortie = run_cmd(
            ["git", "commit", "-m", self._msg_commit],
            cwd=site
        )
        if sortie.strip():
            for ligne in sortie.strip().split("\n"):
                self._log(f"  {ligne}", "#DDDDDD")
        if code != 0:
            self._log(f"  ERREUR git commit (code {code})", "#FF6B6B")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        # Vérifier le remote configuré (informatif)
        code_r, remote_txt = run_cmd(["git", "remote", "-v"], cwd=site)
        if remote_txt.strip():
            self._log(f"  Remote : {remote_txt.splitlines()[0]}", "#AED6F1")

        # ── Authentification ─────────────────────────────────────────
        # Strategie : git push nu, sans aucune interference credential.
        #
        # GCM (Git Credential Manager, installe par GitHub Desktop) gere tout :
        #   - Token valide en cache  → push silencieux, aucune action
        #   - Token expire           → GCM ouvre le browser UNE fois, se renouvelle,
        #                              les prochains pushes sont silencieux
        #
        # NE PAS toucher a credential.helper ni core.askpass :
        #   les neutraliser empeche GCM de fonctionner et provoque /dev/tty ou 401.
        #
        # Fallback : si config.yaml contient un token valide, on l'utilise via
        #   http.extraheader (sans toucher au credential system).

        token = self.cfg.get("github_token", "").strip()
        user  = self.cfg.get("github_user",  "").strip()

        env = os.environ.copy()
        extra_git_args = []

        # Verifier si le token config.yaml est valide (ne pas bloquer si absent)
        if token and user:
            self._log("  Verification token config.yaml...", "#DDDDDD")
            api_ok, api_msg, api_login = self._verifier_token(user, token)
            if api_ok:
                import base64
                b64 = base64.b64encode(f"{user}:{token}".encode()).decode()
                extra_git_args = [
                    "-c", f"http.extraheader=Authorization: Basic {b64}",
                ]
                self._log(f"  Token config.yaml OK ({api_login}) — utilise.", "#2ECC71")
            else:
                self._log(f"  Token config.yaml invalide ({api_msg}).", "#FFD700")
                self._log("  → GCM (GitHub Desktop) utilise en fallback.", "#AED6F1")
        else:
            self._log("  Pas de token dans config.yaml — GCM utilise.", "#AED6F1")
            self._log("  (Si le navigateur s'ouvre : c'est normal, une seule fois)", "#888888")

        # git push — utilise le git de GitHub Desktop si disponible.
        # Le git systeme est souvent bloque par Windows Firewall quand lance
        # depuis un sous-process Python. Le git GHD a les bons droits reseau
        # et les bons credential helpers configures par GitHub Desktop.
        git_exe = self._trouver_git_ghd()
        if git_exe != "git":
            self._log(f"  Git GitHub Desktop detecte.", "#2ECC71")
        else:
            self._log(f"  Git systeme utilise (GitHub Desktop non detecte).", "#FFD700")

        self._log(f"  git push origin {branche} ...", "#DDDDDD")
        sortie = ""
        code   = -1
        try:
            proc_git = subprocess.Popen(
                [git_exe] + extra_git_args + ["push", "origin", branche],
                cwd=site,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            lines = []
            for ligne in proc_git.stdout:
                ligne = ligne.rstrip()
                if ligne:
                    lines.append(ligne)
            proc_git.wait()
            code   = proc_git.returncode
            sortie = "\n".join(lines)
        except Exception as e:
            code, sortie = -1, str(e)

        # Masquer le token dans les logs
        if token and sortie:
            sortie = sortie.replace(token, "***")
        if sortie.strip():
            for ligne in sortie.strip().split("\n"):
                couleur = "#FF6B6B" if "error" in ligne.lower() else "#DDDDDD"
                self._log(f"  {ligne}", couleur)

        if code != 0:
            self._log(f"  ERREUR git push (code {code})", "#FF6B6B")
            self._log("  Si l'erreur persiste :", "#FFD700")
            self._log("  → Ouvrir GitHub Desktop → File → Options → Sign out / Sign in", "#FFD700")
            self._log("    Cela renouvelle le token dans le Credential Manager", "#FFD700")
            self._log("  → Ou ajouter un token PAT valide dans prog\\config.yaml", "#FFD700")
            self._set_etape(idx, "erreur")
            self._terminer(False)
            return False

        self._set_etape(idx, "ok")
        self._log("  Push effectué avec succès.", "#90EE90")
        return True


# ══════════════════════════════════════════════════════════════════
#  FENÊTRE ERREUR CONFIG
# ══════════════════════════════════════════════════════════════════
MODELE_CONFIG = """\
# config.yaml — maj_github.py

# Dossier contenant les fichiers source editables (docx, etc.)
racine_source     = C:\\Travail\\MonProjet

# Dossier racine du site local (depot git)
racine_site_local = C:\\SiteGITHUB\\Hebreu4.0

# Chemin complet vers lancer.cmd
lancer_cmd        = C:\\SiteGITHUB\\Hebreu4.0\\lancer.cmd

# URL du depot GitHub
url_github        = https://github.com/francisboulanger/Hebreu4.0

# Message du commit : "auto" = date+heure automatique
message_commit    = auto

# Branche git cible
branche           = main

# Filtre fichiers (vide = tout accepter)
# ex: .*\\.docx$,.*\\.pdf$
filtre            =
"""

def afficher_erreur_config(cfg: dict, source_cfg: str):
    root = tk.Tk()
    root.title("Configuration manquante — maj_github.py")
    root.geometry("640x480")
    root.configure(bg="#EAF4F4")

    tk.Label(root, text="⚠  Configuration incomplète",
             font=("Segoe UI", 13, "bold"), fg="#C0392B",
             bg="#EAF4F4").pack(pady=14)

    manquants = []
    for cle in ("racine_source", "racine_site_local", "lancer_cmd", "url_github"):
        if not cfg[cle]:
            manquants.append(f"  • {cle} non défini")
    if manquants:
        tk.Label(root, text="\n".join(manquants),
                 font=("Segoe UI", 10), fg="#C0392B",
                 bg="#EAF4F4", justify="left").pack(padx=20)

    tk.Label(root, text=f"\nFichier config utilisé : {source_cfg}",
             font=("Segoe UI", 9), fg="#555",
             bg="#EAF4F4").pack()

    tk.Label(root, text="\nCréer un fichier config.yaml à côté du programme avec ce contenu :",
             font=("Segoe UI", 10, "bold"),
             bg="#EAF4F4").pack(anchor="w", padx=20)

    txt = tk.Text(root, height=16, font=("Courier New", 9),
                  bg="#F8F8F8", wrap="none")
    txt.insert("1.0", MODELE_CONFIG)
    txt.config(state="disabled")
    txt.pack(fill="both", expand=True, padx=20, pady=8)

    tk.Button(root, text="Fermer", command=root.destroy,
              bg="#C0392B", fg="white", padx=12).pack(pady=6)
    root.mainloop()


# ══════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════
def main():
    print(f"[Démarrage] {version[0]} v{version[1]}")

    cfg, source_cfg = charger_config()

    # Vérifier les champs obligatoires
    manquants = [c for c in ("racine_source", "racine_site_local",
                              "lancer_cmd", "url_github")
                 if not cfg[c]]
    if manquants:
        afficher_erreur_config(cfg, source_cfg)
        return

    app = FenetreMaj(cfg, source_cfg)
    app.mainloop()


if __name__ == "__main__":
    main()

# fin de maj_github_v1.7.py - Version 1.7
