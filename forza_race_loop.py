"""
╔══════════════════════════════════════════════════════════════╗
║   FORZA HORIZON 6 — Race Loop Macro                          ║
║   Boucle automatique de courses                              ║
║                                                              ║
║   INSTALLATION :  pip install pynput                         ║
║   LANCEMENT    :  launch.bat                                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
import threading, queue, time, json, os, sys, random, winsound, math

try:
    from pynput import keyboard as pynput_kb
    from pynput.keyboard import Controller as KbCtrl, KeyCode, Key
except ImportError:
    print("ERREUR : pip install pynput")
    sys.exit(1)

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG_DIR  = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Pestovich")
CONFIG_FILE = os.path.join(CONFIG_DIR, "forza6_config.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "toggle_key":        "F2",
    "opacity":           0.92,
    "overlay_pos":       {"x": 20, "y": 200},
    "press_duration_ms": 80,
    "delay_start_s":     3.0,
    "race_duration_s":   56.0,
    "delay_x_s":         0.3,
    "delay_enter1_s":    2.0,
    "delay_enter2_s":    13.0,
    "hold_z": {
        "enabled":   True,
        "key_label": "Z",
        "vk":        0x5A,
    },
}

VK_MAP = {
    "0":0x30, "1":0x31, "2":0x32, "3":0x33, "4":0x34,
    "5":0x35, "6":0x36, "7":0x37, "8":0x38, "9":0x39,
    "Q":0x51, "W":0x57, "E":0x45, "R":0x52, "T":0x54,
    "Y":0x59, "U":0x55, "I":0x49, "O":0x4F, "P":0x50,
    "A":0x41, "S":0x53, "D":0x44, "F":0x46, "G":0x47,
    "H":0x48, "J":0x4A, "K":0x4B, "L":0x4C, "Z":0x5A,
    "X":0x58, "C":0x43, "V":0x56, "B":0x42, "N":0x4E, "M":0x4D,
}

def load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))

def save_cfg(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ── KEY SENDER (file unique — frappes naturelles sans chevauchement) ──────────
_kb    = KbCtrl()
_key_q = queue.Queue()

def _sender_loop():
    while True:
        item = _key_q.get()
        if item is None:
            break
        key_obj, hold_ms = item
        _kb.press(key_obj)
        time.sleep(hold_ms / 1000.0)
        _kb.release(key_obj)
        time.sleep(0.05)
        _key_q.task_done()

threading.Thread(target=_sender_loop, daemon=True).start()

def enqueue_key(key_obj, hold_ms):
    _key_q.put((key_obj, hold_ms))

def _j(s):
    return s + random.uniform(-0.04, 0.04)

# ── PHASES ────────────────────────────────────────────────────────────────────
PHASE_COLORS = {
    "DEPART":     "#FFB703",
    "COURSE":     "#58CC02",
    "FIN COURSE": "#FFB703",
    "TOUCHE X":   "#FFB703",
    "ATTENTE →↵": "#1CB0F6",
    "ENTREE 1":   "#1CB0F6",
    "CHARGEMENT": "#7B61FF",
    "ENTREE 2":   "#7B61FF",
    "EN ATTENTE": "#334455",
}

# ── ENGINE ────────────────────────────────────────────────────────────────────
class Engine:
    def __init__(self, cfg):
        self.cfg        = cfg
        self.active     = False
        self.phase      = "EN ATTENTE"
        self.phase_pct  = 0.0
        self.phase_rem  = 0.0
        self.z_held     = False
        self.loop_count = 0
        self._z_key     = None
        self._stop_ev   = threading.Event()

    def reload(self, cfg):
        was = self.active
        if was:
            self.stop()
            time.sleep(0.15)
        self.cfg = cfg
        if was:
            self.start()

    def start(self):
        self.active   = True
        self._stop_ev = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.active = False
        self._stop_ev.set()
        self._release_z()
        self.phase     = "EN ATTENTE"
        self.phase_pct = 0.0
        self.phase_rem = 0.0

    def _release_z(self):
        if self.z_held and self._z_key:
            try:
                _kb.release(self._z_key)
            except Exception:
                pass
        self.z_held = False
        self._z_key = None

    def _sleep_phase(self, name, duration):
        self.phase     = name
        self.phase_rem = duration
        self.phase_pct = 0.0
        step    = 0.05
        elapsed = 0.0
        while elapsed < duration:
            if self._stop_ev.is_set():
                return True
            sl = min(step, duration - elapsed)
            time.sleep(sl)
            elapsed += sl
            self.phase_rem = max(0.0, duration - elapsed)
            self.phase_pct = elapsed / duration if duration > 0 else 1.0
        return False

    def _run(self):
        while not self._stop_ev.is_set():
            self.loop_count += 1
            cfg    = self.cfg
            ms     = cfg.get("press_duration_ms", 80)
            z_en   = cfg.get("hold_z", {}).get("enabled", False)
            z_vk   = cfg.get("hold_z", {}).get("vk", 0x5A)
            x_key  = KeyCode.from_vk(0x58)   # touche X
            e_key  = Key.enter                # touche Entrée

            # 1. Entrée de départ — lance la course
            self.phase = "DEPART"
            enqueue_key(e_key, ms)
            time.sleep(0.08)

            # 2. Chrono de départ (3s avant que la course commence vraiment)
            if self._sleep_phase("DEPART", cfg.get("delay_start_s", 3.0)):
                break

            # 3. COURSE — maintien Z pendant toute la durée
            if z_en:
                self._z_key = KeyCode.from_vk(z_vk)
                _kb.press(self._z_key)
                self.z_held = True

            if self._sleep_phase("COURSE", cfg.get("race_duration_s", 56.0)):
                self._release_z()
                break
            self._release_z()

            # 4. Délai fin de course avant X
            d_x = cfg.get("delay_x_s", 0.3)
            if d_x > 0:
                if self._sleep_phase("FIN COURSE", _j(d_x)):
                    break

            # 5. Touche X
            self.phase = "TOUCHE X"
            enqueue_key(x_key, ms)
            time.sleep(0.08)

            # 6. Attente avant Entrée 1
            if self._sleep_phase("ATTENTE →↵", _j(cfg.get("delay_enter1_s", 2.0))):
                break

            # 7. Entrée 1
            self.phase = "ENTREE 1"
            enqueue_key(e_key, ms)
            time.sleep(0.08)

            # 8. Chargement avant Entrée 2
            if self._sleep_phase("CHARGEMENT", _j(cfg.get("delay_enter2_s", 13.0))):
                break

            # 9. Entrée 2 — reboucle sur étape 1
            self.phase = "ENTREE 2"
            enqueue_key(e_key, ms)
            time.sleep(0.1)

        self.active = False

# ── SETTINGS ──────────────────────────────────────────────────────────────────
class Settings:
    BG  = "#0c0c14"
    BG2 = "#13131f"

    def __init__(self, parent, cfg, on_save):
        self.cfg     = json.loads(json.dumps(cfg))
        self.on_save = on_save
        self.win = tk.Toplevel(parent)
        self.win.title("Reglages — Forza Race Loop")
        self.win.configure(bg=self.BG)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.geometry("440x580")
        self._build()

    def _lbl(self, p, t, fg="#aaaaaa", bg=None):
        return tk.Label(p, text=t, bg=bg or self.BG2,
                        font=("Courier", 9), fg=fg)

    def _entry(self, p, var, w=8, fg="#ffffff"):
        return tk.Entry(p, textvariable=var, width=w,
                        font=("Courier", 10), bg="#1a1a2e", fg=fg,
                        insertbackground="white", relief="flat")

    def _row(self, parent, label, var, w=8, fg="#ffffff", lbl_fg="#aaaaaa"):
        f = tk.Frame(parent, bg=self.BG2)
        f.pack(fill="x", padx=10, pady=3)
        self._lbl(f, label, lbl_fg).pack(side="left", padx=6)
        self._entry(f, var, w, fg).pack(side="right", padx=6)

    def _section(self, title, color):
        f = tk.Frame(self.win, bg=self.BG2, pady=4)
        f.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(f, text=title, font=("Courier", 8, "bold"),
                 fg=color, bg=self.BG2).pack(anchor="w", padx=8, pady=(2, 4))
        tk.Frame(f, bg=color, height=1).pack(fill="x", padx=8, pady=(0, 4))
        return f

    def _build(self):
        tk.Label(self.win, text="  REGLAGES — Forza Race Loop",
                 font=("Courier", 11, "bold"), fg="#1CB0F6", bg=self.BG
                 ).pack(pady=(12, 8))

        # Section Général
        s1 = self._section("GENERAL", "#445566")

        self.tv = tk.StringVar(value=self.cfg.get("toggle_key", "F2"))
        self._row(s1, "Touche activation", self.tv)

        self.press_ms = tk.StringVar(value=str(self.cfg.get("press_duration_ms", 80)))
        self._row(s1, "Duree frappe (ms)", self.press_ms)

        op_f = tk.Frame(s1, bg=self.BG2)
        op_f.pack(fill="x", padx=10, pady=3)
        self._lbl(op_f, "Opacite (%)").pack(side="left", padx=6)
        self.op_var = tk.IntVar(value=int(self.cfg.get("opacity", 0.92) * 100))
        tk.Scale(op_f, variable=self.op_var, from_=20, to=100,
                 orient="horizontal", bg=self.BG2, fg="#aaaaaa",
                 troughcolor="#1a1a2e", activebackground="#3a3a5e",
                 highlightthickness=0, length=130, showvalue=True,
                 font=("Courier", 8)).pack(side="right", padx=6)

        # Section Timings
        s2 = self._section("TIMINGS DE COURSE", "#58CC02")

        self.delay_start = tk.StringVar(value=str(self.cfg.get("delay_start_s", 3.0)))
        self._row(s2, "Chrono de depart (s)          ", self.delay_start, fg="#FFB703", lbl_fg="#886600")

        self.race_dur = tk.StringVar(value=str(self.cfg.get("race_duration_s", 56.0)))
        self._row(s2, "Duree course / maintien Z (s) ", self.race_dur, fg="#58CC02", lbl_fg="#447744")

        self.delay_x = tk.StringVar(value=str(self.cfg.get("delay_x_s", 0.3)))
        self._row(s2, "Delai fin de course avant X (s)", self.delay_x, fg="#FFB703", lbl_fg="#886600")

        self.delay_e1 = tk.StringVar(value=str(self.cfg.get("delay_enter1_s", 2.0)))
        self._row(s2, "Delai apres X -> Entree 1 (s) ", self.delay_e1, fg="#1CB0F6", lbl_fg="#116688")

        self.delay_e2 = tk.StringVar(value=str(self.cfg.get("delay_enter2_s", 13.0)))
        self._row(s2, "Delai apres Entree 1 -> 2 (s) ", self.delay_e2, fg="#7B61FF", lbl_fg="#443388")

        # Section Hold Z
        bg3 = "#1a2a1a"
        s3 = tk.Frame(self.win, bg=bg3, pady=4)
        s3.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(s3, text="MAINTIEN ACCELERATEUR (pendant la course)",
                 font=("Courier", 8, "bold"), fg="#58CC02", bg=bg3
                 ).pack(anchor="w", padx=8, pady=(2, 4))
        tk.Frame(s3, bg="#58CC02", height=1).pack(fill="x", padx=8, pady=(0, 4))

        hz  = self.cfg.get("hold_z", DEFAULT_CONFIG["hold_z"])
        fen = tk.Frame(s3, bg=bg3)
        fen.pack(fill="x", padx=10, pady=(2, 4))
        self.z_en = tk.BooleanVar(value=hz.get("enabled", False))
        tk.Checkbutton(fen, text="Maintenir la touche pendant toute la course",
                       variable=self.z_en, font=("Courier", 9),
                       fg="#88cc88", bg=bg3, activebackground=bg3,
                       selectcolor="#0a1a0a").pack(side="left", padx=2)

        fz = tk.Frame(s3, bg=bg3)
        fz.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(fz, text="Touche :", font=("Courier", 9),
                 fg="#446644", bg=bg3).pack(side="left", padx=6)
        self.z_key = tk.StringVar(value=hz.get("key_label", "Z"))
        self._entry(fz, self.z_key, 4, "#aaffaa").pack(side="left", padx=4)
        tk.Label(fz, text="(ex: Z pour AZERTY, W pour QWERTY)",
                 font=("Courier", 7), fg="#336633", bg=bg3).pack(side="left", padx=6)

        # Boutons
        btn = tk.Frame(self.win, bg=self.BG)
        btn.pack(pady=14)
        tk.Button(btn, text="  Sauvegarder", font=("Courier", 10, "bold"),
                  fg="#fff", bg="#10b981", relief="flat", padx=14, pady=7,
                  command=self._save).pack(side="left", padx=8)
        tk.Button(btn, text="  Annuler", font=("Courier", 10),
                  fg="#aaa", bg="#1a1a2e", relief="flat", padx=14, pady=7,
                  command=self.win.destroy).pack(side="left", padx=8)

    def _save(self):
        try:
            z_kl = self.z_key.get().strip().upper()
            self.cfg.update({
                "toggle_key":        self.tv.get().strip(),
                "press_duration_ms": int(self.press_ms.get()),
                "opacity":           round(self.op_var.get() / 100.0, 2),
                "delay_start_s":     float(self.delay_start.get()),
                "race_duration_s":   float(self.race_dur.get()),
                "delay_x_s":         float(self.delay_x.get()),
                "delay_enter1_s":    float(self.delay_e1.get()),
                "delay_enter2_s":    float(self.delay_e2.get()),
                "hold_z": {
                    "enabled":   self.z_en.get(),
                    "key_label": z_kl,
                    "vk":        VK_MAP.get(z_kl, 0x5A),
                },
            })
            save_cfg(self.cfg)
            self.on_save(self.cfg)
            self.win.destroy()
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Erreur", str(e))

# ── MAIN OVERLAY ──────────────────────────────────────────────────────────────
class App:
    W = 260

    def __init__(self):
        self.cfg     = load_cfg()
        self.engine  = Engine(self.cfg)
        self.running = True
        self._dx = self._dy = 0
        self._anim = 0
        self._z_hold_active = False

        pos = self.cfg.get("overlay_pos", {"x": 20, "y": 200})
        self.root = tk.Tk()
        self.root.title("Forza Race Loop")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.cfg.get("opacity", 0.92))
        self.root.geometry(f"{self.W}x252+{pos['x']}+{pos['y']}")
        self.root.configure(bg="#0c0c14")

        self._build()
        self._start_loop()
        self._start_hotkey()

    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg="#13131f", height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="  FORZA RACE LOOP",
                 font=("Courier", 10, "bold"), fg="#1CB0F6", bg="#13131f"
                 ).place(x=10, y=12)

        self.s_dot = tk.Label(hdr, text="●", font=("Courier", 13),
                               fg="#1e1e2e", bg="#13131f")
        self.s_dot.place(x=self.W - 68, y=12)
        self.s_lbl = tk.Label(hdr, text="OFF", font=("Courier", 9, "bold"),
                               fg="#1e1e2e", bg="#13131f")
        self.s_lbl.place(x=self.W - 50, y=16)

        gear = tk.Label(hdr, text="⚙", font=("Courier", 12),
                         fg="#445566", bg="#13131f", cursor="hand2")
        gear.place(x=self.W - 46, y=12)
        gear.bind("<Button-1>", lambda e: self._open_settings())

        close = tk.Label(hdr, text="✕", font=("Courier", 10),
                          fg="#333355", bg="#13131f", cursor="hand2")
        close.place(x=self.W - 20, y=13)
        close.bind("<Button-1>", lambda e: self._quit())

        for w in (hdr, self.root):
            w.bind("<Button-1>", self._ds)
            w.bind("<B1-Motion>", self._dm)

        # Zone principale
        main = tk.Frame(self.root, bg="#0c0c14")
        main.pack(fill="x", padx=8, pady=(6, 0))

        self.phase_lbl = tk.Label(main, text="EN ATTENTE",
                                   font=("Courier", 11, "bold"),
                                   fg="#334455", bg="#0c0c14", anchor="w")
        self.phase_lbl.pack(fill="x")

        tf = tk.Frame(main, bg="#0c0c14")
        tf.pack(fill="x", pady=(0, 4))
        self.timer_lbl = tk.Label(tf, text="--.-s",
                                   font=("Courier", 22, "bold"),
                                   fg="#223344", bg="#0c0c14", anchor="w")
        self.timer_lbl.pack(side="left")
        self.loop_lbl = tk.Label(tf, text="",
                                  font=("Courier", 9), fg="#334455", bg="#0c0c14")
        self.loop_lbl.pack(side="right", anchor="s", pady=(0, 3))

        # Progress bar
        self.bar = tk.Canvas(self.root, width=self.W - 16, height=6,
                              bg="#0c0c14", highlightthickness=0)
        self.bar.pack(padx=8, pady=(0, 4))

        # Séquence visuelle complète
        seq = tk.Frame(self.root, bg="#0c0c14")
        seq.pack(fill="x", padx=8, pady=(0, 2))
        self.seq_ed = tk.Label(seq, text="[↵]", font=("Courier", 8, "bold"),
                                fg="#332200", bg="#0c0c14")
        self.seq_ed.pack(side="left")
        tk.Label(seq, text="3s→", font=("Courier", 7),
                 fg="#223344", bg="#0c0c14").pack(side="left")
        self.seq_z  = tk.Label(seq, text="[Z 56s]", font=("Courier", 8, "bold"),
                                fg="#113300", bg="#0c0c14")
        self.seq_z.pack(side="left")
        tk.Label(seq, text="→", font=("Courier", 7),
                 fg="#223344", bg="#0c0c14").pack(side="left")
        self.seq_x  = tk.Label(seq, text="[X]", font=("Courier", 8, "bold"),
                                fg="#332200", bg="#0c0c14")
        self.seq_x.pack(side="left")
        tk.Label(seq, text="→", font=("Courier", 7),
                 fg="#223344", bg="#0c0c14").pack(side="left")
        self.seq_e1 = tk.Label(seq, text="[↵]", font=("Courier", 8, "bold"),
                                fg="#111133", bg="#0c0c14")
        self.seq_e1.pack(side="left")
        tk.Label(seq, text="→", font=("Courier", 7),
                 fg="#223344", bg="#0c0c14").pack(side="left")
        self.seq_e2 = tk.Label(seq, text="[↵]", font=("Courier", 8, "bold"),
                                fg="#111133", bg="#0c0c14")
        self.seq_e2.pack(side="left")

        # Z hold indicator
        zf = tk.Frame(self.root, bg="#0c0c14", height=26)
        zf.pack(fill="x", padx=8)
        zf.pack_propagate(False)
        self.z_lbl = tk.Label(zf, text="[Z]  maintien desactive",
                               font=("Courier", 8), fg="#223322", bg="#0c0c14",
                               anchor="w")
        self.z_lbl.place(x=0, y=4)

        # F3 Hold Z indicator
        f3f = tk.Frame(self.root, bg="#0c0c14", height=26)
        f3f.pack(fill="x", padx=8)
        f3f.pack_propagate(False)
        self.f3_lbl = tk.Label(f3f, text="[F3]  maintien Z independant : OFF",
                               font=("Courier", 8), fg="#1a2a1a", bg="#0c0c14",
                               anchor="w")
        self.f3_lbl.place(x=0, y=4)

        # Footer
        footer = tk.Frame(self.root, bg="#13131f", height=28)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        key = self.cfg.get("toggle_key", "F2")
        self.f_lbl = tk.Label(footer,
                               text=f"[{key}] Boucle  ·  [F3] Z  ·  [ESC]",
                               font=("Courier", 7), fg="#1e2e3e", bg="#13131f")
        self.f_lbl.pack(side="left", padx=8, pady=7)

    def _start_loop(self):
        def loop():
            while self.running:
                self._anim = (self._anim + 1) % 60
                try:
                    self.root.after(0, self._refresh)
                except Exception:
                    break
                time.sleep(0.05)
        threading.Thread(target=loop, daemon=True).start()

    def _refresh(self):
        self._refresh_f3()
        active = self.engine.active
        phase  = self.engine.phase
        color  = PHASE_COLORS.get(phase, "#334455")

        # Highlights séquence visuelle
        self.seq_ed.config(fg="#FFB703" if phase == "DEPART"                      else "#332200")
        self.seq_z.config( fg="#58CC02" if phase == "COURSE"                      else "#113300")
        self.seq_x.config( fg="#FFB703" if phase in ("FIN COURSE","TOUCHE X")     else "#332200")
        self.seq_e1.config(fg="#1CB0F6" if phase in ("ATTENTE →↵","ENTREE 1")    else "#111133")
        self.seq_e2.config(fg="#7B61FF" if phase in ("CHARGEMENT","ENTREE 2")     else "#111133")

        if active:
            self.phase_lbl.config(text=phase, fg=color)
            rem = self.engine.phase_rem
            self.timer_lbl.config(text=f"{rem:5.1f}s", fg=color)
            self.loop_lbl.config(text=f"#{self.engine.loop_count}", fg="#445566")
            self.s_dot.config(fg="#58CC02")
            self.s_lbl.config(text="ON", fg="#58CC02")

            pct = self.engine.phase_pct
            bw  = int((self.W - 16) * pct)
            self.bar.delete("all")
            self.bar.create_rectangle(0, 0, self.W - 16, 6, fill="#1a1a2e", outline="")
            if bw > 1:
                self.bar.create_rectangle(0, 0, bw, 6, fill=color, outline="")

            z_en = self.cfg.get("hold_z", {}).get("enabled", False)
            z_kl = self.cfg.get("hold_z", {}).get("key_label", "Z")
            if z_en and self.engine.z_held:
                dots = "▮" * ((self._anim // 10) % 4 + 1)
                self.z_lbl.config(text=f"[{z_kl}]  MAINTENU {dots}", fg="#58CC02")
            elif z_en:
                self.z_lbl.config(text=f"[{z_kl}]  relache", fg="#447744")
            else:
                self.z_lbl.config(text=f"[{z_kl}]  maintien desactive", fg="#223322")

            self.f_lbl.config(text=f"[ESC] Stopper  ·  #{self.engine.loop_count} tours",
                               fg="#334455")
        else:
            self.phase_lbl.config(text="EN ATTENTE", fg="#334455")
            self.timer_lbl.config(text="--.-s", fg="#223344")
            self.loop_lbl.config(text="")
            self.s_dot.config(fg="#1e1e2e")
            self.s_lbl.config(text="OFF", fg="#1e1e2e")
            self.bar.delete("all")
            self.bar.create_rectangle(0, 0, self.W - 16, 6, fill="#1a1a2e", outline="")
            z_en = self.cfg.get("hold_z", {}).get("enabled", False)
            z_kl = self.cfg.get("hold_z", {}).get("key_label", "Z")
            self.z_lbl.config(
                text=f"[{z_kl}]  active (inactif)" if z_en else f"[{z_kl}]  maintien desactive",
                fg="#447744" if z_en else "#223322"
            )
            key = self.cfg.get("toggle_key", "F2")
            self.f_lbl.config(text=f"[{key}] Boucle  ·  [F3] Z  ·  [ESC]", fg="#1e2e3e")

    def _start_hotkey(self):
        ks  = self.cfg.get("toggle_key", "F2").lower()
        tok = getattr(Key, ks, None)

        def on_press(key):
            if key == tok:
                self.root.after(0, self._toggle)
            elif key == Key.f3:
                self.root.after(0, self._toggle_z_hold)
            elif key == Key.esc:
                if self.engine.active:
                    self.root.after(0, self._do_stop)
                if self._z_hold_active:
                    self.root.after(0, self._stop_z_hold_mode)

        l = pynput_kb.Listener(on_press=on_press)
        l.daemon = True
        l.start()

    def _toggle(self):
        if self.engine.active:
            self._do_stop()
        else:
            self.engine.start()
            threading.Thread(target=lambda: winsound.Beep(880, 80), daemon=True).start()

    def _do_stop(self):
        self.engine.stop()
        threading.Thread(target=lambda: winsound.Beep(440, 120), daemon=True).start()

    def _open_settings(self):
        def on_save(cfg):
            self.cfg = cfg
            self.root.attributes("-alpha", cfg.get("opacity", 0.92))
            self.engine.reload(cfg)
            key = cfg.get("toggle_key", "F2")
            if not self.engine.active:
                self.f_lbl.config(text=f"[{key}] Activer  ·  [ESC] Stopper")
        Settings(self.root, self.cfg, on_save)

    def _refresh_f3(self):
        z_kl = self.cfg.get("hold_z", {}).get("key_label", "Z")
        if self._z_hold_active:
            dots = "▮" * ((self._anim // 10) % 4 + 1)
            self.f3_lbl.config(text=f"[F3]  [{z_kl}] MAINTENU {dots}", fg="#58CC02")
        else:
            self.f3_lbl.config(text=f"[F3]  maintien Z independant : OFF", fg="#1a2a1a")

    def _ds(self, e): self._dx, self._dy = e.x, e.y
    def _dm(self, e):
        nx = self.root.winfo_x() + e.x - self._dx
        ny = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{nx}+{ny}")
        self.cfg["overlay_pos"] = {"x": nx, "y": ny}

    def _get_z_vk(self):
        return self.cfg.get("hold_z", {}).get("vk", 0x5A)

    def _toggle_z_hold(self):
        if self._z_hold_active:
            self._stop_z_hold_mode()
        else:
            self._start_z_hold_mode()
            threading.Thread(target=lambda: winsound.Beep(660, 80), daemon=True).start()

    def _start_z_hold_mode(self):
        self._z_hold_active = True
        threading.Thread(target=self._run_z_hold, daemon=True).start()

    def _stop_z_hold_mode(self):
        self._z_hold_active = False
        try:
            _kb.release(KeyCode.from_vk(self._get_z_vk()))
        except Exception:
            pass
        threading.Thread(target=lambda: winsound.Beep(330, 120), daemon=True).start()

    def _run_z_hold(self):
        z_key = KeyCode.from_vk(self._get_z_vk())
        try:
            _kb.press(z_key)
            while self._z_hold_active:
                # Maintien : 1.5 à 4.5s (≈90% du temps)
                hold_t  = random.uniform(1.5, 4.5)
                elapsed = 0.0
                while elapsed < hold_t and self._z_hold_active:
                    time.sleep(0.02)
                    elapsed += 0.02
                if not self._z_hold_active:
                    break
                # Micro-relâchement : 50–180ms (≈10%)
                _kb.release(z_key)
                rel_t   = random.uniform(0.05, 0.18)
                elapsed = 0.0
                while elapsed < rel_t and self._z_hold_active:
                    time.sleep(0.01)
                    elapsed += 0.01
                if self._z_hold_active:
                    _kb.press(z_key)
        finally:
            try:
                _kb.release(z_key)
            except Exception:
                pass
        self._z_hold_active = False

    def _quit(self):
        self.running = False
        self.engine.stop()
        self._z_hold_active = False
        try:
            _kb.release(KeyCode.from_vk(self._get_z_vk()))
        except Exception:
            pass
        self.cfg["overlay_pos"] = {
            "x": self.root.winfo_x(),
            "y": self.root.winfo_y(),
        }
        save_cfg(self.cfg)
        _key_q.put(None)
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("  Forza Horizon 6 — Race Loop Macro")
    print(f"   Config : {CONFIG_FILE}")
    print("   [F2]  Activer / desactiver la boucle")
    print("   [ESC] Stopper d'urgence")
    print("   Clique l'engrenage pour configurer les timings\n")
    App().run()
