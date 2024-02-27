import os.path
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror, askokcancel
from PIL import Image, ImageTk
from PIL.Image import Resampling

import cfg
from widgets.common import ChooseDir, HistoryCombo
from utils import not_include, get_available_filename, load_yaml, save_yaml
from filehandlers import image_files


def clip(x, lower, upper):
    return max(min(x, upper), lower)


class ScalableImage(tk.Canvas):
    def __init__(self, parent, image: Image.Image = None, zoom_shift=(0.8, 1.25), scale_limits=(0.03125, 32)):
        self.image = image
        self.zoom_shift = zoom_shift
        self.scale_limits = scale_limits

        self.default_photoimage = ImageTk.PhotoImage(cfg.PLACEHOLDER_IMAGE)

        self.x = self.y = None
        self.scale = None

        self.fragment = None
        self.fragment_center = None
        self.fragment_pos = None
        self.img_id = None
        self.photoimage = None
        self.motion_base = None

        super(ScalableImage, self).__init__(parent)
        self.bind('<Configure>', lambda status: self.draw())
        self.bind('<Visibility>', lambda *args: self.draw())

        if image is not None:
            self.set_image(self.image)
        else:
            self.clear()

    def set_image(self, image):
        self.image = image
        self.scale = min(
            clip(self.image.size[0], 128, 1024) / self.image.size[0],
            clip(self.image.size[1], 128, 1024) / self.image.size[1]
        )
        width = int(self.image.size[0] * self.scale)
        height = int(self.image.size[1] * self.scale)

        self.config(width=width, height=height)

        self.x, self.y = image.size[0] / 2, image.size[1] / 2

        self.bind('<MouseWheel>', lambda status: self.zoom(status))
        self.bind('<ButtonPress>', lambda status: self.grab(status))
        self.bind('<ButtonRelease>', lambda status: self.release(status))
        self.bind('<Motion>', lambda status: self.drag(status))

        self.draw()

    def clear(self):
        self.image = None

        self.config(width=cfg.PLACEHOLDER_IMAGE.size[0], height=cfg.PLACEHOLDER_IMAGE.size[1])

        self.unbind('<MouseWheel>')
        self.unbind('<ButtonPress>')
        self.unbind('<ButtonRelease>')
        self.unbind('<Motion>')

        self.draw()

    def grab(self, status):
        if status.num == 1:
            self.motion_base = self.fragment_pos[0] - status.x, self.fragment_pos[1] - status.y

    def release(self, status):
        if status.num == 1:
            self.update_idletasks()
            width, height = self.winfo_width(), self.winfo_height()
            self.x = self.fragment_center[0] - (self.fragment_pos[0] - width / 2) / self.scale
            self.y = self.fragment_center[1] - (self.fragment_pos[1] - height / 2) / self.scale
            self.motion_base = None
            self.draw()

    def drag(self, status):
        if self.motion_base is not None:
            self.fragment_pos[0] = self.motion_base[0] + status.x
            self.fragment_pos[1] = self.motion_base[1] + status.y
            if self.img_id is not None:
                self.delete(self.img_id)
            self.img_id = self.create_image(self.fragment_pos[0], self.fragment_pos[1],
                                            anchor=tk.CENTER, image=self.photoimage)

    def zoom(self, status):
        delta, mouse_x, mouse_y = status.delta, status.x, status.y
        if not delta: return
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()
        new_scale = self.scale * self.zoom_shift[delta > 0]
        if self.scale_limits[0] <= new_scale <= self.scale_limits[1]:
            factor = (1 / self.scale - 1 / new_scale)
            self.x = self.x + (mouse_x - width / 2) * factor
            self.y = self.y + (mouse_y - height / 2) * factor
            self.scale = new_scale
            self.draw()

    def draw(self):
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()

        if self.image is None:
            if self.img_id is not None:
                self.delete(self.img_id)
            self.img_id = self.create_image(width / 2, height / 2, anchor=tk.CENTER, image=self.default_photoimage)
            return

        bsw = width / self.scale
        bsh = height / self.scale

        fragment_box = (
                  max(self.x - bsw, 0),
                  max(self.y - bsh, 0),
                  min(self.x + bsw, self.image.size[0]),
                  min(self.y + bsw, self.image.size[1])
        )
        self.fragment_center = (
            (fragment_box[2] + fragment_box[0]) / 2,
            (fragment_box[3] + fragment_box[1]) / 2,
        )

        size = (
                   int((fragment_box[2] - fragment_box[0]) * self.scale),
                   int((fragment_box[3] - fragment_box[1]) * self.scale)
        )
        self.fragment = self.image.resize(size, box=fragment_box, resample=Resampling.BOX)

        self.fragment_pos = [
            int((self.fragment_center[0] - self.x) * self.scale) + width // 2,
            int((self.fragment_center[1] - self.y) * self.scale) + height // 2
        ]

        if self.img_id is not None:
            self.delete(self.img_id)
        self.config(scrollregion=(width // 2, height // 2, width // 2, height // 2))
        self.photoimage = ImageTk.PhotoImage(self.fragment)
        self.img_id = self.create_image(
            self.fragment_pos[0], self.fragment_pos[1], anchor=tk.CENTER, image=self.photoimage
        )


class ImageBox(ttk.Frame):
    def __init__(self, parent, on_save=None, on_cancel=None):
        super(ImageBox, self).__init__(parent)
        self.rowconfigure(1, weight=1, minsize=100)
        self.columnconfigure(1, weight=1, minsize=100)
        self.columnconfigure(2, weight=1, minsize=50)

        self.on_save = on_save
        self.on_cancel = on_cancel

        self.image = None
        self.params = None
        self.mask = None

        self.canvas = ScalableImage(self, None, zoom_shift=(0.8, 1.25), scale_limits=(0.03125, 32))
        self.canvas.grid(row=1, column=1, columnspan=3, sticky=tk.N+tk.S+tk.E+tk.W)

        self.outdir = ChooseDir(self, "Path: ", width=80, history=cfg.config['outdir_history'])
        self.outdir.grid(column=1, row=2, sticky=tk.W + tk.E, padx=5, pady=5)

        self.prefix = HistoryCombo(
            self, "Filename: ", width=20,
            history=cfg.config['filename_prefix_history'],
            validator=not_include('\\/:*?»<>|')
        )
        self.prefix.entry.config(justify=tk.RIGHT)
        self.prefix.grid(column=2, row=2, sticky=tk.E, pady=5)

        self.ext = HistoryCombo(
            self, "", width=5,
            history=cfg.config['filename_ext_history'],
            readonly=True
        )
        self.ext.entry.config(justify=tk.LEFT)
        self.ext.grid(column=3, row=2, sticky=tk.W, pady=5)

        self.button_frame = ttk.Frame(self)
        self.save_button = ttk.Button(self.button_frame, text="Save", command=lambda *args: self.save())
        self.save_button.grid(row=0, column=0, padx=5, pady=5)
        self.cancel_button = ttk.Button(self.button_frame, text="Cancel", command=lambda *args: self.cancel())
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5)
        self.button_frame.grid(row=3, column=2, columnspan=2, sticky=tk.E)

    def set(self, image: Image.Image, params: dict = None, mask: Image.Image = None):
        self.image = image
        self.params = params
        self.mask = mask

        self.canvas.set_image(self.image)

        if not cfg.config['outdir_history']:
            self.outdir.set(os.path.abspath("ai_images"))
        else:
            self.outdir.set(index=0)
        self.prefix.set(get_available_filename(self.outdir.get(), "ai_painting_????.png").removesuffix(".png"))
        self.ext.set(".png")

    def load(self, path: str):
        path = os.path.abspath(path)
        directory = os.path.dirname(path)
        filename, ext = os.path.splitext(os.path.basename(path))

        try:
            self.image = image_files.load(path)
        except FileNotFoundError:
            self.image = None
        try:
            self.params = load_yaml(path + ".prm")
        except FileNotFoundError:
            self.params = None
        try:
            self.mask = image_files.load(path + "_mask.png")
        except FileNotFoundError:
            self.mask = None

        self.canvas.set_image(self.image)
        self.outdir.set(directory)
        self.prefix.set(filename)
        self.ext.set(ext)

    def clear(self):
        self.image = None
        self.params = None

        self.canvas.clear()
        self.outdir.set("")
        self.prefix.set("")
        self.ext.set("")

    def save(self):
        try:
            path = self.outdir.get()
            os.makedirs(path, exist_ok=True)
            filepath = os.path.join(path, self.prefix.get() + self.ext.get())
            yml_path = filepath + ".prm"
            mask_path = filepath + "_mask.png"

            if self.image is not None:
                if os.path.exists(filepath):
                    if not askokcancel(
                        "File exists",
                        f"File {filepath} already exists. Overwrite?"
                    ):
                        return
            if self.params is not None:
                if os.path.exists(yml_path):
                    if not askokcancel(
                        "File exists",
                        f"File {yml_path} already exists. Overwrite?"
                    ):
                        return
            if self.mask is not None:
                if os.path.exists(mask_path):
                    if not askokcancel(
                        "File exists",
                        f"File {mask_path} already exists. Overwrite?"
                    ):
                        return

            if self.image is not None: image_files.save(filepath, self.image)
            else: filepath = None
            if self.params is not None: save_yaml(yml_path, self.params)
            else: yml_path = None
            if self.mask is not None: image_files.save(mask_path, self.mask)
            else: mask_path = None

            self.outdir.update_history()
            self.prefix.update_history()
            self.ext.update_history()

            if self.on_save:
                self.on_save(filepath, yml_path, mask_path)

        except Exception as error:
            showerror("Save ERROR", str(error))

    def cancel(self):
        if self.on_cancel:
            self.on_cancel(self)


class SaveImage(tk.Toplevel):
    def __init__(self, root, image, params):
        super(SaveImage, self).__init__(root)
        self.title("Generated image")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self.image_box = ImageBox(self, on_save=lambda *args: self.destroy(), on_cancel=lambda *args: self.destroy())
        self.image_box.set(image, params)
        self.image_box.grid(row=0, column=0, sticky=tk.N+tk.S+tk.W+tk.E)
