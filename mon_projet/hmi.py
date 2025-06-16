"""
IHM « Poste de Pilotage » – LGN-04
──────────────────────────────────
• Consomme l’API REST : http://10.10.0.23:5000/api
• Écrit l’OF + le rôle utilisateur (0=unknown / 1=opérateur / 2=maintenance)
  dans le PLC via OPC UA (LGN01/02/03)
"""

from __future__ import annotations
import datetime, threading, tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk
from opcua_client import get_states

import rest_client
from opcua_client import (
    push_user, ROLE_OPERATOR, ROLE_MAINT, ROLE_UNKNOWN
)

# ------------------------------------------------------------------ #
# 1)  CONSTANTES
# ------------------------------------------------------------------ #
ASSETS_DIR       = "/home/groupec/Documents/NEE/Assets"
BADGE_OPERATEUR  = '&("(&c&-'          # UID badge opérateur
BADGE_MAINT      = '&(-"écc-'          # UID badge maintenance


TRANSLATIONS = {
    "fr": {
        "title": "Poste de Pilotage LGN-04",
        "dashboard": "Accueil", "of_selection": "Ordres de Fabrication",
        "status": "État des îlots", "logs": "Logs",
        "traceability": "Traçabilité",
        "unauthorized": "Veuillez scanner votre badge RFID.",
        "export_logs": "Exporter les logs",
        "send_of": "Envoyer l’OF sélectionné",
        "badge_wait": "Veuillez scanner votre badge RFID…",
        "no_of_selected": "Sélectionnez un OF dans la liste.",
        "send_success": "OF {numero} envoyé avec succès.",
        "send_error": "Impossible d’envoyer l’OF.",
        "clear_logs": "🧹  Vider les logs",
        "filter_label": "🔎  Filtrer :", "details": "Détails"
    },
    "en": {
        "title": "Production Dashboard LGN-04",
        "dashboard": "Dashboard", "of_selection": "Manufacturing Orders",
        "status": "Station Status", "logs": "Logs",
        "traceability": "Traceability",
        "unauthorized": "Scan your RFID badge first.",
        "export_logs": "Export logs",
        "send_of": "Send selected MO",
        "badge_wait": "Please scan your RFID badge…",
        "no_of_selected": "Select an MO in the list.",
        "send_success": "MO {numero} successfully sent.",
        "send_error": "Unable to send the MO.",
        "clear_logs": "🧹  Clear logs",
        "filter_label": "🔎  Filter :", "details": "Details"
    },
}

# ------------------------------------------------------------------ #
# 2)  APPLICATION Tk
# ------------------------------------------------------------------ #
class PilotageApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1280x720")
        self.configure(bg="#10142c")
        self.title("Pilotage LGN-04")

        # État
        self.lang, self.role = "fr", "non_identifié"
        self.logs: list[tuple[str, str]] = []
        self.search_var = tk.StringVar()
        self.traceability_data: list[tuple[str, str, str]] = []

        # 2-1 : Barre haute
        top = tk.Frame(self, bg="#1b1f3b", height=60); top.pack(fill="x")
        self.title_label = tk.Label(top, fg="white", bg="#1b1f3b",
                                    font=("Segoe UI", 18, "bold"),
                                    text=self.tr("title"))
        self.title_label.pack(side="left", padx=20)

        self.rest_status = tk.Label(top, fg="white", bg="#1b1f3b",
                                    font=("Segoe UI", 12), text="REST : ???")
        self.rest_status.pack(side="right", padx=15)

        self.role_label = tk.Label(top, fg="white", bg="#1b1f3b",
                                   font=("Segoe UI", 12),
                                   text=f"Rôle : {self.role}")
        self.role_label.pack(side="right")

        # Drapeaux langue
        flag_frame = tk.Frame(top, bg="#1b1f3b"); flag_frame.pack(side="right")
        self._add_flag(flag_frame, "fr", "autocollant-drapeau-france-rond.jpg")
        self._add_flag(flag_frame, "en", "sticker-drapeau-anglais-rond.jpg")

        # 2-2 : Sidebar & zone contenu
        side = tk.Frame(self, bg="#16193c", width=200); side.pack(side="left", fill="y")
        self.content = tk.Frame(self, bg="#202540"); self.content.pack(expand=True, fill="both")

        self.nav_btns: list[tk.Button] = []
        for key, cb in (
            ("dashboard",      self.show_dashboard),
            ("of_selection",   lambda: self.need_auth(self.show_of)),
            ("status", lambda: self.need_auth(self.show_status, allow="maintenance")),
            ("logs",           lambda: self.need_auth(self.show_logs)),
            ("traceability",   lambda: self.need_auth(self.show_trace)),
        ):
            b = tk.Button(side, text=self.tr(key), font=("Segoe UI", 13),
                          bg="#16193c", fg="white", relief="flat",
                          activebackground="#3047ff", command=cb)
            b.pack(fill="x", padx=10, pady=6); self.nav_btns.append(b)

        # Frames (pages)
        self.frames = {n: tk.Frame(self.content, bg="#202540")
                       for n in ("dash", "of", "status", "logs", "trace")}
        for f in self.frames.values(): f.place(relwidth=1, relheight=1)

        # Zone cachée pour le lecteur RFID (terminée par <CR>)
        self._hidden = tk.Entry(self); self._hidden.place(x=-100, y=-100)
        self._hidden.bind("<Return>", self._on_badge); self._hidden.focus()

        # Logo accueil
        self.logo_img = ImageTk.PhotoImage(
            Image.open(Path(ASSETS_DIR) / "logoENN.PNG").resize((200, 200))
        )

        self.load_traceability()
        self.show_dashboard()

    # ------------------------------------------------------------------ #
    #   UTILITAIRES
    # ------------------------------------------------------------------ #
    def tr(self, k): return TRANSLATIONS[self.lang].get(k, k)

    def _add_flag(self, frame, lang, file):
        img = ImageTk.PhotoImage(Image.open(Path(ASSETS_DIR)/file).resize((32, 32)))
        tk.Button(frame, image=img, bd=0, bg="#1b1f3b",
                  command=lambda l=lang: self.set_lang(l)).pack(side="left", padx=3)
        setattr(self, f"flag_{lang}", img)

    def set_lang(self, lang):
        self.lang = lang
        self.title_label.config(text=self.tr("title"))
        for b, k in zip(self.nav_btns,
                        ("dashboard", "of_selection", "status", "logs", "traceability")):
            b.config(text=self.tr(k))
        self.show_dashboard()

    # ------------------------------------------------------------------ #
    #   AUTH – lecture badge RFID
    # ------------------------------------------------------------------ #
    def _on_badge(self, _evt=None):
        uid = self._hidden.get().strip(); self._hidden.delete(0, "end")

        if uid == BADGE_OPERATEUR:
            self.role, role_code = "opérateur", ROLE_OPERATOR   # 1
        elif uid == BADGE_MAINT:
            self.role, role_code = "maintenance", ROLE_MAINT    # 2
        else:
            self.role, role_code = "non_identifié", ROLE_UNKNOWN # 0
            messagebox.showerror("Badge", "Badge invalide"); return

        self.role_label.config(text=f"Rôle : {self.role}")
        self.log(f"Badge {self.role} OK")

        # Envoi OPC UA (thread pour IHM fluide)
        threading.Thread(target=push_user, args=("LGN01", role_code),
                         daemon=True).start()

    def need_auth(self, callback, allow="any"):
        if self.role == "non_identifié":
            messagebox.showwarning("Accès", self.tr("unauthorized"))
            return

        if allow == "maintenance" and self.role != "maintenance":
            messagebox.showwarning("Accès refusé", "Seul le personnel de maintenance peut accéder à cette page.")
            return

        callback()


    # ------------------------------------------------------------------ #
    #   REST status
    # ------------------------------------------------------------------ #
    def update_rest_status(self):
        ok = rest_client.can_connect_to_rest()
        self.rest_status.config(text=f"REST : {'OK' if ok else 'OFF'}",
                                fg="lightgreen" if ok else "yellow")

    # ------------------------------------------------------------------ #
    #   PAGES
    # ------------------------------------------------------------------ #
    def show_frame(self, tag):  # helper
        for f in self.frames.values(): f.lower()
        self.frames[tag].tkraise()

    def show_dashboard(self):
        self.update_rest_status()
        f = self.frames["dash"]; self._clear(f); self.show_frame("dash")
        tk.Label(f, image=self.logo_img, bg="#202540").pack(pady=20)
        tk.Label(f, text=self.tr("title"), fg="white", bg="#202540",
                 font=("Segoe UI", 20)).pack(pady=10)
        tk.Label(f, text=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                 fg="white", bg="#202540", font=("Segoe UI", 14)).pack()
        if self.role == "non_identifié":
            tk.Label(f, text=self.tr("badge_wait"),
                     fg="lightgray", bg="#202540").pack(pady=30)

    # ----- liste OF
    def show_of(self):
        self.update_rest_status()
        f = self.frames["of"]; self._clear(f); self.show_frame("of")
        tk.Label(f, text=self.tr("of_selection"),
                 fg="white", bg="#202540", font=("Segoe UI", 18, "bold")).pack(pady=8)

        self.tree_of = ttk.Treeview(f, columns=("Num", "Code", "Qté"),
                                    show="headings", height=15)
        for col, w in (("Num", 160), ("Code", 420), ("Qté", 100)):
            self.tree_of.heading(col, text=col); self.tree_of.column(col, width=w)
        self.tree_of.pack(padx=10, pady=12)

        # REST
        try:
            for of in rest_client.get_of_list_cached():
                self.tree_of.insert("", "end",
                                    values=(of["numero"], of["code"], of["quantite"]))
            self.log("Liste OF chargée")
        except Exception as e:
            self.log(f"REST KO : {e}")
            messagebox.showerror("REST", "Impossible de récupérer la liste OF.")

        tk.Button(f, text=self.tr("send_of"), bg="green", fg="white",
                  command=self.send_selected).pack(pady=6)

    def details_of(self, _evt):
        sel = self.tree_of.selection(); self.tree_of.focus()
        if not sel: return
        num = self.tree_of.item(sel[0], "values")[0]
        comps = rest_client.get_of_components(num)
        p = tk.Toplevel(self); p.title(f"{self.tr('details')} – {num}")
        p.configure(bg="#202540"); p.geometry("420x300")
        tk.Label(p, text=f"OF {num}", bg="#202540", fg="white",
                 font=("Arial", 14, "bold")).pack(pady=8)
        for c in comps:
            tk.Label(p, text=c, bg="#202540", fg="white",
                     anchor="w").pack(fill="x", padx=20)

    def send_selected(self):
        sel = self.tree_of.selection()
        if not sel:
            return messagebox.showwarning("!", self.tr("no_of_selected"))
        num, code, qty_str = self.tree_of.item(sel[0], "values")
        try:
            qty = float(qty_str)
        except ValueError:
            return messagebox.showerror("Erreur", "Quantité invalide")

        ilot = "LGN01"

        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ok = rest_client.start(ilot, num, code, qty)
        self.log(f"{num} → {ilot} {'OK' if ok else 'KO'}")
        (messagebox.showinfo if ok else messagebox.showerror)(
            "OF", self.tr("send_success" if ok else "send_error").format(numero=num)
        )

    # ----- status
    def show_status(self):
        self.update_rest_status()        # garde l’indicateur API si tu veux
        f = self.frames["status"]; self._clear(f); self.show_frame("status")

        tk.Label(f, text=self.tr("status"), fg="white", bg="#202540",
                font=("Segoe UI", 18, "bold")).pack(pady=8)

        states = get_states()            # ← interrogation directe OPC UA
        for ilot, etat in states.items():
            couleur = "lightgreen" if etat == "RUN" else ("yellow" if etat else "red")
            tk.Label(f, text=f"{ilot} : {etat}",
                    fg=couleur, bg="#202540",
                    font=("Segoe UI", 14)).pack(pady=4)

    # ----- logs
    def show_logs(self):
        f = self.frames["logs"]; self._clear(f); self.show_frame("logs")
        tk.Label(f, text=self.tr("logs"), fg="white", bg="#202540",
                 font=("Segoe UI", 18)).pack(pady=8)

        search = tk.Entry(f, textvariable=self.search_var)
        search.pack(); search.bind("<KeyRelease>", self.refresh_logs)

        tk.Button(f, text=self.tr("export_logs"),
                  command=self.export_logs).pack(pady=3)
        tk.Button(f, text=self.tr("clear_logs"),
                  command=self.clear_logs).pack()

        self.tree_logs = ttk.Treeview(f, columns=("t", "m"),
                                      show="headings", height=18)
        self.tree_logs.heading("t", text="Heure"); self.tree_logs.column("t", width=160)
        self.tree_logs.heading("m", text="Message"); self.tree_logs.column("m", width=830)
        self.tree_logs.pack(padx=10, pady=10); self.refresh_logs()

    # ----- trace (démo)
    def load_traceability(self):
        self.traceability_data = [
            ("WH/MO/00012", "En cours", "2025-02-27 14:22"),
            ("WH/MO/00011", "OK",       "2025-02-27 11:05"),
        ]

    def show_trace(self):
        f = self.frames["trace"]; self._clear(f); self.show_frame("trace")
        tk.Label(f, text=self.tr("traceability"), fg="white", bg="#202540",
                 font=("Segoe UI", 18, "bold")).pack(pady=10)
        tree = ttk.Treeview(f, columns=("OF", "Etat", "Horodatage"),
                            show="headings", height=16)
        for col, w in (("OF", 160), ("Etat", 220), ("Horodatage", 250)):
            tree.heading(col, text=col); tree.column(col, width=w)
        tree.pack(padx=12, pady=12)
        for row in self.traceability_data: tree.insert("", "end", values=row)

    # ------------------------------------------------------------------ #
    #   LOGS utils
    # ------------------------------------------------------------------ #
    def log(self, msg: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append((ts, msg)); print(ts, msg); self.refresh_logs()

    def refresh_logs(self, *_):
        if not getattr(self, "tree_logs", None): return
        filt = self.search_var.get().lower()
        self.tree_logs.delete(*self.tree_logs.get_children())
        for t, m in self.logs:
            if filt in t.lower() or filt in m.lower():
                self.tree_logs.insert("", "end", values=(t, m))

    def clear_logs(self):
        if messagebox.askyesno("?", self.tr("clear_logs")):
            self.logs.clear(); self.refresh_logs()

    def export_logs(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            f.write("Heure,Message\n")
            for t, m in self.logs:
                f.write(f"{t},{m}\n")
        messagebox.showinfo("Export", f"{len(self.logs)} logs → {path}")

    # ------------------------------------------------------------------ #
    #   Divers
    # ------------------------------------------------------------------ #
    def _clear(self, frame): [w.destroy() for w in frame.winfo_children()]


# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    PilotageApp().mainloop()
