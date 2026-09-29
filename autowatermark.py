import os
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

EXTS = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp", "*.tif", "*.tiff")


def apply_watermark(photo, mark, opacity, size_pct, margin_pct):
    """Накладывает mark в правый верхний угол photo."""
    base = ImageOps.exif_transpose(photo).convert("RGBA")
    w = max(1, int(base.width * size_pct / 100))
    h = max(1, int(mark.height * w / mark.width))
    m = mark.resize((w, h), Image.LANCZOS)
    alpha = m.getchannel("A").point(lambda a: int(a * opacity / 100))
    m.putalpha(alpha)
    margin = int(base.width * margin_pct / 100)
    base.alpha_composite(m, (max(0, base.width - w - margin), margin))
    return base


BG, PANEL, FG, MUTED = "#0f0f17", "#181824", "#f2f2f7", "#8b8ba3"
ACCENT, ACCENT_HOVER = "#7c5cff", "#9a80ff"
CHANNEL_URL = "https://t.me/VABUGODE"
FONT = "Segoe UI"


def flat_button(parent, text, cmd, primary=False):
    bg = ACCENT if primary else "#262636"
    hover = ACCENT_HOVER if primary else "#33334a"
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=FG, activebackground=hover,
                  activeforeground=FG, relief="flat", bd=0, cursor="hand2",
                  font=(FONT, 11, "bold" if primary else "normal"), pady=9 if primary else 7)
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VABUGODE • Авто-вотермарка")
        self.geometry("1000x640")
        self.minsize(820, 560)
        self.configure(bg=BG)
        self.mark_path = None
        self.photos = []
        self.out_dir = tk.StringVar()
        self.opacity = tk.IntVar(value=60)
        self.size = tk.IntVar(value=20)
        self.margin = tk.IntVar(value=2)
        self._preview_img = None

        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("TFrame", background=PANEL)
        st.configure("TLabel", background=PANEL, foreground=FG, font=(FONT, 10))
        st.configure("Muted.TLabel", foreground=MUTED, font=(FONT, 9))
        st.configure("TEntry", fieldbackground="#262636", foreground=FG, insertcolor=FG,
                     bordercolor="#262636", lightcolor="#262636", darkcolor="#262636")
        st.configure("Horizontal.TScale", background=PANEL, troughcolor="#262636")
        st.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#262636",
                     bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT)

        # шапка
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=18, pady=(14, 10))
        tk.Label(head, text="VABUGODE", bg=BG, fg=FG, font=(FONT, 20, "bold")).pack(side="left")
        tk.Label(head, text="  авто-вотермарка", bg=BG, fg=ACCENT,
                 font=(FONT, 13)).pack(side="left", pady=(6, 0))
        link = tk.Label(head, text="✈  Наш канал в Telegram", bg=BG, fg=ACCENT,
                        font=(FONT, 10, "underline"), cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: webbrowser.open(CHANNEL_URL))
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=14)
        left = ttk.Frame(body, padding=16, width=310)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self.canvas = tk.Canvas(body, bg="#0a0a10", highlightthickness=0)
        self.canvas.pack(side="right", fill="both", expand=True, padx=(14, 0))
        self.canvas.bind("<Configure>", lambda e: self.preview())

        flat_button(left, "🖼  1. Выбрать вотермарку", self.pick_mark).pack(fill="x")
        self.mark_lbl = ttk.Label(left, text="не выбрана", style="Muted.TLabel", wraplength=270)
        self.mark_lbl.pack(anchor="w", pady=(4, 12))

        flat_button(left, "📁  2. Выбрать фото (много)", self.pick_photos).pack(fill="x")
        self.photos_lbl = ttk.Label(left, text="не выбраны", style="Muted.TLabel", wraplength=270)
        self.photos_lbl.pack(anchor="w", pady=(4, 12))

        for text, var, lo, hi in (("Прозрачность, %", self.opacity, 0, 100),
                                  ("Размер (% ширины фото)", self.size, 1, 100),
                                  ("Отступ, %", self.margin, 0, 20)):
            r = ttk.Frame(left)
            r.pack(fill="x")
            ttk.Label(r, text=text).pack(side="left")
            val = ttk.Label(r, text=str(var.get()), foreground=ACCENT, font=(FONT, 10, "bold"))
            val.pack(side="right")
            var.trace_add("write", lambda *_a, v=var, l=val: l.config(text=str(int(v.get()))))
            ttk.Scale(left, from_=lo, to=hi, variable=var,
                      command=lambda _v: self.preview()).pack(fill="x", pady=(2, 10))

        ttk.Label(left, text="Папка для результата").pack(anchor="w")
        row = ttk.Frame(left)
        row.pack(fill="x", pady=(2, 0))
        ttk.Entry(row, textvariable=self.out_dir).pack(side="left", fill="x", expand=True, ipady=3)
        tk.Button(row, text="…", command=self.pick_out, bg="#262636", fg=FG, relief="flat",
                  bd=0, cursor="hand2", width=3).pack(side="right", padx=(6, 0))
        ttk.Label(left, text="по умолчанию: папка «watermarked» рядом с фото",
                  style="Muted.TLabel", wraplength=270).pack(anchor="w", pady=(2, 0))

        self.btn = flat_button(left, "✨  3. Наложить на все фото", self.run, primary=True)
        self.btn.pack(fill="x", pady=(16, 8), side="bottom")
        self.bar = ttk.Progressbar(left)
        self.bar.pack(fill="x", side="bottom")
        self.status = ttk.Label(left, text="", style="Muted.TLabel")
        self.status.pack(anchor="w", side="bottom")

    def pick_mark(self):
        p = filedialog.askopenfilename(title="Вотермарка", filetypes=[("Изображения", EXTS)])
        if p:
            self.mark_path = p
            self.mark_lbl.config(text=os.path.basename(p))
            self.preview()

    def pick_photos(self):
        ps = filedialog.askopenfilenames(title="Фото", filetypes=[("Изображения", EXTS)])
        if ps:
            self.photos = list(ps)
            self.photos_lbl.config(text=f"выбрано: {len(ps)}")
            self.preview()

    def pick_out(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir.set(d)

    def load_mark(self):
        return Image.open(self.mark_path).convert("RGBA")

    def preview(self):
        self.canvas.delete("all")
        if not self.photos:
            self.canvas.create_text(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                                    fill=MUTED, font=(FONT, 12), justify="center",
                                    text="Выберите фото —\nздесь появится предпросмотр")
            return
        try:
            with Image.open(self.photos[0]) as im:
                im.thumbnail((1200, 1200))
                img = im.copy()
            if self.mark_path:
                img = apply_watermark(img, self.load_mark(), self.opacity.get(),
                                      self.size.get(), self.margin.get())
            cw, ch = max(self.canvas.winfo_width(), 50), max(self.canvas.winfo_height(), 50)
            img = ImageOps.contain(img.convert("RGB"), (cw, ch))
            self._preview_img = ImageTk.PhotoImage(img)
            self.canvas.create_image(cw // 2, ch // 2, image=self._preview_img)
        except Exception as e:
            self.canvas.create_text(20, 20, anchor="nw", fill="white", text=f"Ошибка превью: {e}")


    def run(self):
        if not self.mark_path or not self.photos:
            messagebox.showwarning("Внимание", "Выберите вотермарку и фото.")
            return
        out = self.out_dir.get() or os.path.join(os.path.dirname(self.photos[0]), "watermarked")
        os.makedirs(out, exist_ok=True)
        self.btn.config(state="disabled")
        self.bar.config(maximum=len(self.photos), value=0)
        args = (out, self.opacity.get(), self.size.get(), self.margin.get())
        threading.Thread(target=self.work, args=args, daemon=True).start()

    def work(self, out, opacity, size, margin):
        errors = []
        mark = self.load_mark()
        for i, p in enumerate(self.photos, 1):
            try:
                with Image.open(p) as im:
                    res = apply_watermark(im, mark, opacity, size, margin)
                    ext = os.path.splitext(p)[1].lower()
                    dst = os.path.join(out, os.path.basename(p))
                    if ext in (".jpg", ".jpeg"):
                        res.convert("RGB").save(dst, quality=95, subsampling=0)
                    elif ext in (".png", ".webp", ".tif", ".tiff"):
                        res.save(dst)
                    else:
                        res.convert("RGB").save(dst)
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")
            self.after(0, self.progress, i)
        self.after(0, self.done, out, errors)

    def progress(self, i):
        self.bar.config(value=i)
        self.status.config(text=f"{i} / {len(self.photos)}")

    def done(self, out, errors):
        self.btn.config(state="normal")
        msg = f"Готово! Файлы сохранены в:\n{out}"
        if errors:
            msg += "\n\nОшибки:\n" + "\n".join(errors[:10])
        messagebox.showinfo("Авто-вотермарка", msg)
        if not errors and os.name == "nt":
            os.startfile(out)


if __name__ == "__main__":
    App().mainloop()
