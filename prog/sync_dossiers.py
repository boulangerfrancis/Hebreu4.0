# sync_dossiers_v1.1.py — Version 1.1
# Synchronisation de dossiers avec sélection visuelle (Tkinter)
# Usage : sync_dossiers.py [fichier.yaml]
#         ou drag&drop d'un .yaml sur l'icone du programme
# v1.1 : suppression messagebox 'Termine' (succes) ; conserve erreurs seulement

version = ("sync_dossiers.py", "1.1")
print(f"[Import] {version[0]} - Version {version[1]} charge")

import sys
import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

# ── PyYAML optionnel (fallback parser simple si absent) ───────────
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ══════════════════════════════════════════════════════════════════
#  CONFIG PAR DÉFAUT
# ══════════════════════════════════════════════════════════════════
CONFIG_DEFAUT = {
    "source":      "",
    "destination": "",
    "recent":      True,
    "filtre":      "",      # vide = tout accepter
    "nouveau":     True,    # copier les fichiers absents de destination
}

CONFIG_YAML_DEFAUT = """\
# sync_dossiers.py — fichier de configuration
# source      : dossier source (obligatoire)
# destination : dossier destination (obligatoire)
# recent      : true  = copier seulement si source plus récent que destination
#               false = copier tous les fichiers correspondant au filtre
# filtre      : expressions régulières séparées par des virgules
#               ex: .*\\.docx$,^p.*\\.pdf$
#               laisser vide pour tout accepter
# nouveau     : true = signaler et proposer la copie des fichiers
#               absents de destination

source      = C:\\chemin\\source
destination = C:\\chemin\\destination
recent      = true
filtre      =
nouveau     = true
"""

# ══════════════════════════════════════════════════════════════════
#  LECTURE CONFIG
# ══════════════════════════════════════════════════════════════════
def _parser_simple(texte: str) -> dict:
    """Parse clé = valeur (avec commentaires #), sans PyYAML."""
    result = {}
    for ligne in texte.splitlines():
        ligne = ligne.split("#")[0].strip()
        if "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        result[cle.strip()] = valeur.strip()
    return result


def lire_config(chemin: Path) -> dict:
    """Lit un fichier .yaml et retourne un dict normalisé."""
    texte = chemin.read_text(encoding="utf-8", errors="replace")

    if HAS_YAML:
        try:
            raw = yaml.safe_load(texte) or {}
            # yaml peut retourner None si fichier vide
        except Exception:
            raw = _parser_simple(texte)
    else:
        raw = _parser_simple(texte)

    # Si yaml a retourné None ou pas un dict, fallback
    if not isinstance(raw, dict):
        raw = _parser_simple(texte)

    cfg = CONFIG_DEFAUT.copy()
    for cle in ("source", "destination", "filtre"):
        if cle in raw and raw[cle] is not None:
            cfg[cle] = str(raw[cle]).strip()
    for cle in ("recent", "nouveau"):
        if cle in raw:
            v = raw[cle]
            if isinstance(v, bool):
                cfg[cle] = v
            else:
                cfg[cle] = str(v).strip().lower() in ("true", "oui", "1", "yes")
    return cfg


def charger_config(args: list) -> tuple[dict, str]:
    """
    Priorité :
      1. argument ligne de commande (.yaml)
      2. config.yaml dans le dossier courant
      3. config par défaut interne
    Retourne (config_dict, source_description)
    """
    # 1. Argument
    for arg in args:
        p = Path(arg)
        if p.suffix.lower() == ".yaml" and p.exists():
            print(f"[Config] Fichier yaml : {p}")
            return lire_config(p), str(p)

    # 2. config.yaml courant
    courant = Path(os.getcwd()) / "config.yaml"
    if courant.exists():
        print(f"[Config] config.yaml courant : {courant}")
        return lire_config(courant), str(courant)

    # 3. Défaut interne
    print("[Config] Aucun fichier yaml trouvé — configuration par défaut")
    return CONFIG_DEFAUT.copy(), "(défaut interne)"


# ══════════════════════════════════════════════════════════════════
#  FILTRES
# ══════════════════════════════════════════════════════════════════
def compiler_filtres(filtre_str: str) -> list:
    """Compile les expressions régulières du filtre."""
    if not filtre_str or not filtre_str.strip():
        return []          # liste vide = tout accepter
    patterns = []
    for expr in filtre_str.split(","):
        expr = expr.strip()
        if expr:
            try:
                patterns.append(re.compile(expr, re.IGNORECASE))
            except re.error as e:
                print(f"[Filtre] Expression invalide {expr!r} : {e}")
    return patterns


def accepte(nom_fichier: str, patterns: list) -> bool:
    """True si le fichier passe le filtre (ou si pas de filtre)."""
    if not patterns:
        return True
    return any(p.search(nom_fichier) for p in patterns)


# ══════════════════════════════════════════════════════════════════
#  SCAN
# ══════════════════════════════════════════════════════════════════
def scanner(cfg: dict) -> list:
    """
    Parcourt source et retourne la liste des fichiers à proposer.
    Chaque entrée : dict avec clés
      - src      : Path source
      - dst      : Path destination
      - statut   : 'maj' | 'nouveau'
      - date_src : datetime
      - date_dst : datetime | None
    """
    source = Path(cfg["source"])
    destination = Path(cfg["destination"])
    recent = cfg["recent"]
    nouveau = cfg["nouveau"]
    patterns = compiler_filtres(cfg["filtre"])

    if not source.exists():
        raise FileNotFoundError(f"Dossier source introuvable : {source}")

    resultats = []

    for racine, dossiers, fichiers in os.walk(source):
        racine_p = Path(racine)
        sous_chemin = racine_p.relative_to(source)

        for nom in fichiers:
            if not accepte(nom, patterns):
                continue

            src = racine_p / nom
            dst = destination / sous_chemin / nom

            try:
                date_src = datetime.fromtimestamp(src.stat().st_mtime)
            except OSError:
                continue

            if dst.exists():
                try:
                    date_dst = datetime.fromtimestamp(dst.stat().st_mtime)
                except OSError:
                    date_dst = None

                if recent and date_dst and date_src <= date_dst:
                    continue   # pas plus récent, on ignore

                resultats.append({
                    "src":      src,
                    "dst":      dst,
                    "statut":   "maj",
                    "date_src": date_src,
                    "date_dst": date_dst,
                })
            else:
                if not nouveau:
                    continue   # fichier nouveau ignoré si option désactivée

                resultats.append({
                    "src":      src,
                    "dst":      dst,
                    "statut":   "nouveau",
                    "date_src": date_src,
                    "date_dst": None,
                })

    return resultats


# ══════════════════════════════════════════════════════════════════
#  COPIE
# ══════════════════════════════════════════════════════════════════
def prochain_bak(dst: Path) -> Path:
    """Retourne le prochain nom .bakN disponible."""
    i = 1
    while True:
        bak = dst.with_suffix(f".bak{i}")
        if not bak.exists():
            return bak
        i += 1


def copier_fichier(entree: dict) -> str:
    """
    Copie src → dst avec sauvegarde .bakN si dst existe.
    Retourne un message de résultat.
    """
    src: Path = entree["src"]
    dst: Path = entree["dst"]

    # Créer le dossier destination si nécessaire
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Sauvegarde si le fichier destination existe
    if dst.exists():
        bak = prochain_bak(dst)
        dst.rename(bak)
        print(f"  [BAK]  {dst.name} → {bak.name}")

    shutil.copy2(str(src), str(dst))
    print(f"  [COPIE] {src} → {dst}")
    return f"OK : {dst.name}"


# ══════════════════════════════════════════════════════════════════
#  INTERFACE TKINTER
# ══════════════════════════════════════════════════════════════════
class FenetreSync(tk.Tk):
    def __init__(self, resultats: list, cfg: dict, source_cfg: str):
        super().__init__()
        self.resultats = resultats
        self.cfg = cfg
        self.vars_coches = []       # BooleanVar pour chaque ligne
        self.title("Synchronisation de dossiers")
        self.resizable(True, True)
        self._construire_ui(source_cfg)
        self._centrer()

    # ── Construction ──────────────────────────────────────────────
    def _construire_ui(self, source_cfg: str):
        PAD = dict(padx=10, pady=5)

        # ─ En-tête info ─
        info = (
            f"Source      : {self.cfg['source']}\n"
            f"Destination : {self.cfg['destination']}\n"
            f"Config      : {source_cfg}\n"
            f"Mode        : {'récent uniquement' if self.cfg['recent'] else 'tous les fichiers'}"
        )
        tk.Label(self, text=info, justify="left",
                 bg="#e8f4f8", font=("Segoe UI", 9),
                 relief="groove", anchor="w").pack(
            fill="x", **PAD)

        # ─ Résumé ─
        nb = len(self.resultats)
        nb_maj = sum(1 for r in self.resultats if r["statut"] == "maj")
        nb_new = nb - nb_maj
        resume = f"{nb} fichier(s) trouvé(s)  —  {nb_maj} mise(s) à jour  /  {nb_new} nouveau(x)"
        tk.Label(self, text=resume, font=("Segoe UI", 10, "bold"),
                 fg="#16a085").pack(**PAD)

        # ─ Boutons Tout / Rien ─
        frm_btn_top = tk.Frame(self)
        frm_btn_top.pack(fill="x", padx=10)
        tk.Button(frm_btn_top, text="✔ Tout sélectionner",
                  command=self._tout_selectionner).pack(side="left", padx=4)
        tk.Button(frm_btn_top, text="✘ Tout désélectionner",
                  command=self._tout_deselectionner).pack(side="left", padx=4)
        tk.Button(frm_btn_top, text="↕ Inverser",
                  command=self._inverser).pack(side="left", padx=4)

        # ─ Liste avec scrollbar ─
        frm_liste = tk.Frame(self)
        frm_liste.pack(fill="both", expand=True, padx=10, pady=5)

        canvas = tk.Canvas(frm_liste, borderwidth=0, bg="white")
        scrollbar = ttk.Scrollbar(frm_liste, orient="vertical",
                                  command=canvas.yview)
        self.frm_items = tk.Frame(canvas, bg="white")

        self.frm_items.bind("<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.frm_items, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # En-têtes colonnes
        hdrs = [("", 3), ("Statut", 8), ("Fichier", 45),
                ("Date source", 17), ("Date destination", 17)]
        for col, (txt, w) in enumerate(hdrs):
            tk.Label(self.frm_items, text=txt, width=w,
                     font=("Segoe UI", 9, "bold"),
                     bg="#d0ece7", relief="groove",
                     anchor="w").grid(row=0, column=col,
                                      sticky="ew", padx=1, pady=1)

        # Lignes
        for i, entree in enumerate(self.resultats):
            var = tk.BooleanVar(value=True)
            self.vars_coches.append(var)

            bg = "#fff8e8" if entree["statut"] == "nouveau" else "white"
            bg_hover = "#e8f4f8"

            # Chemin relatif pour affichage
            try:
                src_rel = entree["src"].relative_to(self.cfg["source"])
            except ValueError:
                src_rel = entree["src"]

            statut_txt = "🆕 Nouveau" if entree["statut"] == "nouveau" \
                         else "🔄 M.à.j"
            date_src_txt = entree["date_src"].strftime("%d/%m/%Y %H:%M") \
                           if entree["date_src"] else ""
            date_dst_txt = entree["date_dst"].strftime("%d/%m/%Y %H:%M") \
                           if entree["date_dst"] else "—"

            widgets = []
            row_num = i + 1

            cb = tk.Checkbutton(self.frm_items, variable=var, bg=bg)
            cb.grid(row=row_num, column=0, sticky="w", padx=2)
            widgets.append(cb)

            for col, (txt, w) in enumerate([
                (statut_txt,   8),
                (str(src_rel), 45),
                (date_src_txt, 17),
                (date_dst_txt, 17),
            ], start=1):
                lbl = tk.Label(self.frm_items, text=txt, width=w,
                               font=("Segoe UI", 9), bg=bg,
                               anchor="w", cursor="hand2")
                lbl.grid(row=row_num, column=col,
                         sticky="ew", padx=1, pady=1)
                widgets.append(lbl)

            # Clic sur la ligne pour cocher/décocher
            def _toggle(event, v=var): v.set(not v.get())
            for w in widgets:
                w.bind("<Button-1>", _toggle)

            # Survol
            def _enter(e, ws=widgets, c=bg_hover):
                for w in ws: w.config(bg=c)
            def _leave(e, ws=widgets, c=bg):
                for w in ws: w.config(bg=c)
            for w in widgets:
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)

        # ─ Boutons action ─
        frm_btn_bas = tk.Frame(self, bg="#e8f4f8")
        frm_btn_bas.pack(fill="x", padx=10, pady=8)

        tk.Button(frm_btn_bas, text="✔ Copier les fichiers sélectionnés",
                  bg="#16a085", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  padx=16, pady=6,
                  command=self._copier).pack(side="left", padx=6)

        tk.Button(frm_btn_bas, text="✘ Annuler",
                  bg="#e74c3c", fg="white",
                  font=("Segoe UI", 10),
                  padx=12, pady=6,
                  command=self.destroy).pack(side="left", padx=4)

        self.lbl_statut = tk.Label(frm_btn_bas, text="",
                                   font=("Segoe UI", 9), bg="#e8f4f8",
                                   fg="#16a085")
        self.lbl_statut.pack(side="left", padx=10)

        # Taille minimale raisonnable
        self.minsize(750, 300)
        self.geometry("950x550")

    # ── Sélection ─────────────────────────────────────────────────
    def _tout_selectionner(self):
        for v in self.vars_coches: v.set(True)

    def _tout_deselectionner(self):
        for v in self.vars_coches: v.set(False)

    def _inverser(self):
        for v in self.vars_coches: v.set(not v.get())

    # ── Copie ──────────────────────────────────────────────────────
    def _copier(self):
        selectionnes = [
            self.resultats[i]
            for i, v in enumerate(self.vars_coches)
            if v.get()
        ]

        if not selectionnes:
            messagebox.showinfo("Aucune sélection",
                                "Aucun fichier sélectionné.")
            return

        # Confirmation
        nb = len(selectionnes)
        nb_new = sum(1 for r in selectionnes if r["statut"] == "nouveau")
        nb_maj = nb - nb_new
        msg = (f"{nb} fichier(s) seront copiés :\n"
               f"  • {nb_maj} mise(s) à jour  (ancien → .bakN)\n"
               f"  • {nb_new} nouveau(x)  (créé dans destination)\n\n"
               f"Confirmer ?")
        if not messagebox.askyesno("Confirmation", msg):
            return

        # Copie
        ok = 0
        erreurs = []
        for entree in selectionnes:
            try:
                copier_fichier(entree)
                ok += 1
            except Exception as e:
                msg_err = f"{entree['src'].name} : {e}"
                erreurs.append(msg_err)
                print(f"  [ERREUR] {msg_err}")

        # Résultat
        if erreurs:
            messagebox.showerror(
                "Erreurs lors de la copie",
                f"{ok} fichier(s) copiés avec succès.\n\n"
                f"Erreurs ({len(erreurs)}) :\n" + "\n".join(erreurs)
            )
        else:
            self.lbl_statut.config(
                text=f"✔ {ok} fichier(s) copiés avec succès.")
            # Pas de messagebox si tout va bien — retour immédiat

        self.destroy()

    # ── Centrage ──────────────────────────────────────────────────
    def _centrer(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")


# ══════════════════════════════════════════════════════════════════
#  FENÊTRE D'ERREUR CONFIG
# ══════════════════════════════════════════════════════════════════
def afficher_erreur_config(cfg: dict, source_cfg: str):
    """Affiche une fenêtre d'aide si source/destination manquants."""
    root = tk.Tk()
    root.title("Configuration manquante")
    root.geometry("620x420")

    tk.Label(root, text="⚠ Configuration incomplète",
             font=("Segoe UI", 13, "bold"), fg="#e74c3c").pack(pady=16)

    manquants = []
    if not cfg["source"]:
        manquants.append("  • source      : dossier source non défini")
    if not cfg["destination"]:
        manquants.append("  • destination : dossier destination non défini")

    tk.Label(root, text="\n".join(manquants),
             font=("Segoe UI", 10), fg="#c0392b",
             justify="left").pack(padx=20)

    tk.Label(root,
             text=f"\nFichier config utilisé : {source_cfg}",
             font=("Segoe UI", 9), fg="#555").pack()

    tk.Label(root, text="\nExemple de fichier config.yaml :",
             font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)

    txt = tk.Text(root, height=12, font=("Courier New", 9),
                  bg="#f8f8f8", wrap="none")
    txt.insert("1.0", CONFIG_YAML_DEFAUT)
    txt.config(state="disabled")
    txt.pack(fill="both", expand=True, padx=20, pady=8)

    tk.Button(root, text="Fermer", command=root.destroy,
              bg="#e74c3c", fg="white", padx=12).pack(pady=6)

    root.mainloop()


# ══════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════
def main():

    # Charger config
    cfg, source_cfg = charger_config(sys.argv[1:])
    print(f"[Config] source={cfg['source']!r}  "
          f"destination={cfg['destination']!r}  "
          f"recent={cfg['recent']}  filtre={cfg['filtre']!r}")

    # Vérifier source et destination
    if not cfg["source"] or not cfg["destination"]:
        afficher_erreur_config(cfg, source_cfg)
        return

    # Scanner
    print("[Scan] Analyse en cours...")
    try:
        resultats = scanner(cfg)
    except FileNotFoundError as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Dossier introuvable", str(e))
        root.destroy()
        return
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erreur", f"Erreur lors du scan :\n{e}")
        root.destroy()
        return

    print(f"[Scan] {len(resultats)} fichier(s) trouvé(s)")

    if not resultats:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Aucun fichier",
            "Aucun fichier à synchroniser.\n\n"
            f"Source      : {cfg['source']}\n"
            f"Destination : {cfg['destination']}\n"
            f"Mode        : {'récent uniquement' if cfg['recent'] else 'tous'}\n"
            f"Filtre      : {cfg['filtre'] or '(aucun)'}"
        )
        root.destroy()
        return

    # Afficher fenêtre de sélection
    app = FenetreSync(resultats, cfg, source_cfg)
    app.mainloop()


if __name__ == "__main__":
    main()

# fin de sync_dossiers_v1.1.py - Version 1.1
