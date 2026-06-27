"""Tkinter GUI (zero extra dependencies).

A dark dashboard with device selection (mic / Discord-output / headphone-monitor),
preset grid, manual trim sliders, live meters and a noise gate.  All audio work
lives in :mod:`voicechanger.engine`; this module is presentation only.
"""
from __future__ import annotations

from . import config
from .engine import AudioEngine
from .presets import PRESETS, PRESET_ORDER

__all__ = ["launch_gui"]

_COLORS = {
    "bg": "#0d0d18", "panel": "#13132a", "card": "#1a1a35", "border": "#2a2a55",
    "accent": "#00d4ff", "purple": "#9b59ff", "pink": "#ff6eb4", "green": "#00ff87",
    "red": "#ff4757", "text": "#dde0ff", "muted": "#6a6a9a", "amber": "#ffb454",
}
_GROUP_COLOR = {"女聲": _COLORS["pink"], "男聲": _COLORS["accent"],
                "特效": _COLORS["purple"], "原聲": _COLORS["muted"]}


def launch_gui(initial_preset: str = "原聲 (Off)") -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    C = _COLORS
    GC = _GROUP_COLOR
    cfg = config.load()
    engine = AudioEngine()

    Fn = ("Segoe UI", 9); Fh = ("Segoe UI", 12, "bold")
    Fm = ("Consolas", 9); Fs = ("Segoe UI", 8)

    root = tk.Tk()
    root.title("🎙️ 即時變聲器 — PSOLA")
    root.geometry("800x690")
    root.resizable(False, False)
    root.configure(bg=C["bg"])

    def lbl(p, t="", f=Fn, fg=None, **k):
        k.setdefault("bg", p.cget("bg"))
        return tk.Label(p, text=t, font=f, fg=fg or C["text"], **k)

    def frm(p, **k):
        k.setdefault("bg", C["card"])
        return tk.Frame(p, **k)

    def sep(p):
        tk.Frame(p, height=1, bg=C["border"]).pack(fill="x", pady=5)

    # header ----------------------------------------------------------------
    hdr = tk.Frame(root, bg=C["bg"]); hdr.pack(fill="x", padx=14, pady=(10, 4))
    lbl(hdr, "🎙️  即時變聲器", ("Segoe UI", 15, "bold"), C["accent"]).pack(side="left")
    status_var = tk.StringVar(value="⬤  已停止")
    status_lbl = tk.Label(hdr, textvariable=status_var, font=Fm, fg=C["red"], bg=C["bg"])
    status_lbl.pack(side="right")

    body = tk.Frame(root, bg=C["bg"]); body.pack(fill="both", expand=True, padx=14)
    left = tk.Frame(body, bg=C["bg"]); left.pack(side="left", fill="y", padx=(0, 8))
    right = tk.Frame(body, bg=C["bg"]); right.pack(side="left", fill="both", expand=True)

    # devices ---------------------------------------------------------------
    dev = frm(left, padx=10, pady=10); dev.pack(fill="x", pady=(0, 8))
    lbl(dev, "🎛️  音訊裝置", Fh, C["accent"]).pack(anchor="w"); sep(dev)
    lbl(dev, "① 麥克風輸入", fg=C["muted"]).pack(anchor="w")
    in_cb = ttk.Combobox(dev, width=30, state="readonly"); in_cb.pack(anchor="w", pady=2)
    lbl(dev, "② 輸出 → Discord（選 CABLE Input）", fg=C["amber"]).pack(anchor="w", pady=(6, 0))
    out_cb = ttk.Combobox(dev, width=30, state="readonly"); out_cb.pack(anchor="w", pady=2)
    lbl(dev, "③ 監聽 → 你的耳機（自己聽）", fg=C["green"]).pack(anchor="w", pady=(6, 0))
    mon_cb = ttk.Combobox(dev, width=30, state="readonly"); mon_cb.pack(anchor="w", pady=2)
    mon_var = tk.BooleanVar(value=True)
    tk.Checkbutton(dev, text="開啟監聽（聽見自己變聲後的聲音）", variable=mon_var, font=Fs,
                   bg=C["card"], fg=C["text"], selectcolor=C["border"],
                   activebackground=C["card"], activeforeground=C["green"],
                   command=lambda: setattr(engine, "monitor_on", mon_var.get())
                   ).pack(anchor="w", pady=(4, 0))

    in_devs: list = []
    out_devs: list = []

    def refresh():
        nonlocal in_devs, out_devs
        ins, outs = engine.list_devices()
        in_devs, out_devs = ins, outs
        in_cb["values"] = [f"[{i}] {n}" for i, n in ins]
        vals = [f"[{i}] {n}" for i, n in outs]
        out_cb["values"] = vals
        mon_cb["values"] = ["（不監聽）"] + vals
        if ins:
            in_cb.current(0)
        if outs:
            ci = next((k for k, (i, n) in enumerate(outs) if "cable" in n.lower()), 0)
            mi = next((k for k, (i, n) in enumerate(outs) if "cable" not in n.lower()), 0)
            out_cb.current(ci)
            mon_cb.current(mi + 1)
        # restore saved selections
        for combo, key in ((in_cb, "in"), (out_cb, "out"), (mon_cb, "monitor")):
            saved = cfg.get(key)
            if saved and saved in combo["values"]:
                combo.set(saved)

    tk.Button(dev, text="🔄 刷新", font=Fs, bg=C["border"], fg=C["text"],
              relief="flat", command=refresh).pack(anchor="w", pady=(4, 0))

    # meters ----------------------------------------------------------------
    mtr = frm(left, padx=10, pady=10); mtr.pack(fill="x", pady=(0, 8))
    lbl(mtr, "📊  音量計", Fh, C["accent"]).pack(anchor="w"); sep(mtr)
    lbl(mtr, "輸入", fg=C["muted"]).pack(anchor="w")
    bin_ = ttk.Progressbar(mtr, length=190, maximum=100); bin_.pack(anchor="w", pady=2)
    lbl(mtr, "輸出", fg=C["muted"]).pack(anchor="w")
    bout = ttk.Progressbar(mtr, length=190, maximum=100); bout.pack(anchor="w", pady=2)
    cpu_var = tk.StringVar(value="CPU: 0.0%")
    lbl(mtr, "", Fm, C["muted"], textvariable=cpu_var).pack(anchor="w", pady=(4, 0))

    # noise gate ------------------------------------------------------------
    gf = frm(left, padx=10, pady=10); gf.pack(fill="x", pady=(0, 8))
    lbl(gf, "🔇  噪音門", Fh, C["accent"]).pack(anchor="w"); sep(gf)
    glbl = lbl(gf, "閾值: 1%", fg=C["muted"]); glbl.pack(anchor="w")

    def on_gate(v):
        engine.noise_gate = float(v) / 100
        glbl.config(text=f"閾值: {float(v):.1f}%")

    gate0 = float(cfg.get("gate", 1.0))
    gscale = tk.Scale(gf, from_=0, to=10, resolution=0.5, orient="horizontal",
                      command=on_gate, bg=C["card"], fg=C["text"], highlightthickness=0,
                      troughcolor=C["border"], length=190)
    gscale.set(gate0); gscale.pack(anchor="w")

    # start/stop ------------------------------------------------------------
    bf = tk.Frame(left, bg=C["bg"]); bf.pack(fill="x")
    start_btn = tk.Button(bf, text="▶  開始變聲", font=("Segoe UI", 11, "bold"),
                          bg=C["green"], fg="#000", relief="flat", pady=9)
    start_btn.pack(fill="x", pady=2)
    stop_btn = tk.Button(bf, text="⏹  停止", font=("Segoe UI", 11, "bold"),
                         bg=C["red"], fg="white", relief="flat", pady=9, state="disabled")
    stop_btn.pack(fill="x", pady=2)

    # presets ---------------------------------------------------------------
    pf = frm(right, padx=10, pady=10); pf.pack(fill="x", pady=(0, 8))
    lbl(pf, "🎭  音效預設", Fh, C["accent"]).pack(anchor="w"); sep(pf)
    pg = tk.Frame(pf, bg=C["card"]); pg.pack(fill="x")
    pbtns: dict = {}
    dvar = tk.StringVar(value=PRESETS[initial_preset].desc)
    lbl(pf, "", Fs, C["muted"], textvariable=dvar, wraplength=420,
        justify="left").pack(anchor="w", pady=(6, 0))

    def select(name):
        engine.set_preset(name)
        dvar.set(PRESETS[name].desc)
        for n, b in pbtns.items():
            gc = GC.get(PRESETS[n].group, C["muted"])
            if n == name:
                b.config(bg=gc, fg="#000" if gc == C["pink"] else "#fff", relief="ridge")
            else:
                b.config(bg=C["border"], fg=C["text"], relief="flat")

    for i, name in enumerate(PRESET_ORDER):
        info = PRESETS[name]
        r, c = divmod(i, 3)
        b = tk.Button(pg, text=f"{info.icon}\n{name}", font=Fs, width=13, height=3,
                      bg=C["border"], fg=C["text"], relief="flat", cursor="hand2",
                      command=lambda n=name: select(n))
        b.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
        pbtns[name] = b
    select(initial_preset)

    # manual trims ----------------------------------------------------------
    tf = frm(right, padx=10, pady=10); tf.pack(fill="x", pady=(0, 8))
    lbl(tf, "🎚️  手動微調（疊加在預設上）", Fh, C["accent"]).pack(anchor="w"); sep(tf)
    sg = tk.Frame(tf, bg=C["card"]); sg.pack(fill="x")
    sliders = [
        ("音調 ±半音", lambda v: setattr(engine, "adj_pitch", float(v))),
        ("低音 EQ dB", lambda v: setattr(engine, "adj_bass", float(v))),
        ("中音 EQ dB", lambda v: setattr(engine, "adj_mid", float(v))),
        ("高音 EQ dB", lambda v: setattr(engine, "adj_treble", float(v))),
        ("音量   dB", lambda v: setattr(engine, "adj_gain", float(v))),
    ]
    for label, cmd in sliders:
        row = tk.Frame(sg, bg=C["card"]); row.pack(fill="x", pady=1)
        tk.Label(row, text=label, font=Fs, fg=C["muted"], bg=C["card"],
                 width=14, anchor="w").pack(side="left")
        vl = tk.Label(row, text="+0", font=Fm, fg=C["accent"], bg=C["card"], width=4)
        vl.pack(side="right")

        def mk(cc, l):
            def h(v):
                cc(v)
                l.config(text=f"{float(v):+.0f}")
            return h

        tk.Scale(row, from_=-12, to=12, resolution=0.5, orient="horizontal",
                 bg=C["card"], fg=C["text"], highlightthickness=0,
                 troughcolor=C["border"], length=300,
                 command=mk(cmd, vl)).pack(side="left", padx=4)

    hf = frm(right, padx=10, pady=8, bg=C["panel"]); hf.pack(fill="x")
    lbl(hf, "💡 Discord：設定→語音與視訊→輸入裝置 選「CABLE Output」\n"
            "   ② 輸出選 CABLE Input、③ 監聽選耳機（記得戴耳機避免回音）\n"
            "   男轉女想更乾淨選「成熟女聲」，要更高選「年輕女聲」",
        Fs, C["muted"], justify="left").pack(anchor="w")

    # control logic ---------------------------------------------------------
    def gidx(cb, devs):
        s = cb.get()
        for i, n in devs:
            if f"[{i}]" in s:
                return i
        return None

    def gmon():
        s = mon_cb.get()
        if s.startswith("（不"):
            return None
        for i, n in out_devs:
            if f"[{i}]" in s:
                return i
        return None

    def do_start():
        try:
            engine.monitor_on = mon_var.get()
            engine.start(gidx(in_cb, in_devs), gidx(out_cb, out_devs), gmon())
            status_var.set("⬤  執行中"); status_lbl.config(fg=C["green"])
            start_btn.config(state="disabled"); stop_btn.config(state="normal")
            config.save({"in": in_cb.get(), "out": out_cb.get(),
                         "monitor": mon_cb.get(), "gate": gscale.get(),
                         "preset": engine.preset_name})
        except Exception as exc:
            messagebox.showerror("啟動失敗", f"{exc}\n\n請確認 sounddevice 已安裝、裝置選擇正確")

    def do_stop():
        engine.stop()
        status_var.set("⬤  已停止"); status_lbl.config(fg=C["red"])
        start_btn.config(state="normal"); stop_btn.config(state="disabled")

    start_btn.config(command=do_start)
    stop_btn.config(command=do_stop)

    def tick():
        if engine.running:
            bin_["value"] = min(100, engine.input_level * 100)
            bout["value"] = min(100, engine.output_level * 100)
            cpu_var.set(f"CPU: {engine.cpu_usage:.1f}%")
        root.after(80, tick)

    style = ttk.Style(); style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=C["border"], background=C["border"],
                    foreground=C["text"], selectbackground=C["purple"])
    style.configure("TProgressbar", troughcolor=C["border"], background=C["accent"],
                    darkcolor=C["accent"], lightcolor=C["accent"])

    refresh()
    if cfg.get("preset") in PRESETS:
        select(cfg["preset"])
    tick()
    root.protocol("WM_DELETE_WINDOW", lambda: (do_stop(), root.destroy()))
    root.mainloop()
