import os
import threading
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Авто-вотермарка")
        self.geometry("900x560")
        self.mark_path = None
        self.photos = []
        self.out_dir = tk.StringVar()
        self.opacity = tk.IntVar(value=60)
        self.size = tk.IntVar(value=20)
        self.margin = tk.IntVar(value=2)
        self._preview_img = None

        left = ttk.Frame(self, padding=10)
        left.pack(side="left", fill="y")
        self.canvas = tk.Canvas(self, bg="#333")
        self.canvas.pack(side="right", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.preview())

        ttk.Button(left, text="1. Выбрать вотермарку", command=self.pick_mark).pack(fill="x")
        self.mark_lbl = ttk.Label(left, text="не выбрана", wraplength=260)
        self.mark_lbl.pack(anchor="w", pady=(0, 10))

        ttk.Button(left, text="2. Выбрать фото (можно много)", command=self.pick_photos).pack(fill="x")
        self.photos_lbl = ttk.Label(left, text="не выбраны", wraplength=260)
        self.photos_lbl.pack(anchor="w", pady=(0, 10))

        for text, var, lo, hi in (("Прозрачность, %", self.opacity, 0, 100),
                                  ("Размер (% ширины фото)", self.size, 1, 100),
                                  ("Отступ, %", self.margin, 0, 20)):
            ttk.Label(left, text=text).pack(anchor="w")
            row = ttk.Frame(left)
            row.pack(fill="x", pady=(0, 6))
            ttk.Scale(row, from_=lo, to=hi, variable=var, command=lambda _v: self.preview()
                      ).pack(side="left", fill="x", expand=True)
            val = ttk.Label(row, width=4)
            val.pack(side="right")
            var.trace_add("write", lambda *_a, v=var, l=val: l.config(text=str(int(v.get()))))
            val.config(text=str(var.get()))

        ttk.Label(left, text="Папка для результата").pack(anchor="w", pady=(6, 0))
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.out_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="...", width=3, command=self.pick_out).pack(side="right")
        ttk.Label(left, text="(по умолчанию: папка «watermarked» рядом с фото)",
                  foreground="gray", wraplength=260).pack(anchor="w")

        self.btn = ttk.Button(left, text="3. Наложить на все фото", command=self.run)
        self.btn.pack(fill="x", pady=14)
        self.bar = ttk.Progressbar(left)
        self.bar.pack(fill="x")
        self.status = ttk.Label(left, text="")
        self.status.pack(anchor="w")

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
        self.btn.state(["disabled"])
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
        self.btn.state(["!disabled"])
        msg = f"Готово! Файлы сохранены в:\n{out}"
        if errors:
            msg += "\n\nОшибки:\n" + "\n".join(errors[:10])
        messagebox.showinfo("Авто-вотермарка", msg)
        if not errors and os.name == "nt":
            os.startfile(out)


if __name__ == "__main__":
    App().mainloop()
