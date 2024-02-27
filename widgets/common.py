import os
import tkinter as tk
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from numpy import random
from PIL import ImageTk, Image

import cfg
from utils import image_fit
from filehandlers import image_files


class VarChecker:
    def __init__(self, var, dtype, from_=None, to=None, step=None):
        self.var = var
        self.memory = var.get()
        self.dtype = dtype
        if from_ is not None and to is not None and from_ > to:
            from_, to = to, from_
        self.from_, self.to = from_, to
        if step is not None:
            if from_ is not None:
                self.base = from_
            elif to is not None:
                self.base = to
            else:
                step = None
        self.step = step

    def input_control(self, val):
        try:
            self.dtype(val)
            return True
        except (ValueError, TypeError):
            return not val

    def final_check(self):
        try:
            curr = self.dtype(self.var.get())
        except (ValueError, TypeError):
            self.var.set(self.memory)
            return
        if self.from_ is not None and curr < self.from_:
            curr = self.from_
            self.var.set(curr)
        elif self.to is not None and curr > self.to:
            curr = self.to
            self.var.set(curr)
        elif self.step:
            curr = self.base + self.dtype(round((curr - self.base)/self.step)*self.step)
            self.var.set(curr)
        self.memory = curr

    def control(self, parent):
        return parent.register(lambda val: self.input_control(val)), '%P'

    def bind(self, widget):
        widget.bind('<FocusOut>', lambda *args: self.final_check())


class CheckBox(ttk.Frame):
    def __init__(self, parent, buttons, orient=HORIZONTAL):
        super(CheckBox, self).__init__(parent)
        self.buttons = {}
        row = col = 0
        for name, (label, init) in buttons.items():
            var = IntVar(value=init)
            chkbtn = ttk.Checkbutton(self, text=label, variable=var)
            chkbtn.grid(column=col, row=row, sticky=tk.W, padx=5, pady=5)
            self.buttons[name] = {
                'var': var,
                'checkbutton': chkbtn
            }
            if orient == HORIZONTAL:
                self.columnconfigure(col, weight=1)
                col += 1
            else:
                self.rowconfigure(row, weight=1)
                row += 1

    def __getitem__(self, item):
        return self.buttons[item]['var']

    def get(self):
        ans = {}
        for name, button in self.buttons:
            ans[name] = bool(button['var'].get())
        return ans

    def set(self, values):
        for name, value in values:
            self.buttons['name']['var'].set(value)


class HistoryCombo(ttk.Frame):
    def __init__(self, parent, label, width, history, max_history=20, is_eq_func=None, validator=None, readonly=False):
        super().__init__(parent)

        self.title = label
        self.columnconfigure(1, weight=1)
        self.history = history
        self.max_history = max_history
        self.is_eq_func = is_eq_func or (lambda s1, s2: s1 == s2)
        self.readonly = readonly

        self.label = ttk.Label(self, text=label)
        self.label.grid(column=0, row=0, sticky=E, padx=5, pady=5)

        self.value = StringVar()
        if validator:
            validate = 'all'
            validatecommand = (self.register(validator), '%P')
        else:
            validate = None
            validatecommand = None

        self.entry = ttk.Combobox(self, width=width, textvariable=self.value, values=self.history,
                                  validate=validate, validatecommand=validatecommand,
                                  state='readonly' if self.readonly else NORMAL)
        self.entry.grid(column=1, row=0, sticky=E + W, padx=5, pady=5)
        if len(self.history) > 0:
            self.entry.current([0])

    def enable(self):
        self.entry.config(state='readonly' if self.readonly else NORMAL)
        self.label.config(state=NORMAL)

    def disable(self):
        self.entry.config(state=DISABLED)
        self.label.config(state=DISABLED)

    def get(self):
        return self.value.get()

    def set(self, value=None, index=None):
        if value is not None or index is None or not(0 <= index < len(self.history)):
            self.value.set(value)
        else:
            self.value.set(self.history[index])

    def update_history(self):
        idx = self.entry.current()
        if idx == -1:
            value = self.value.get()
            for i, old_val in enumerate(self.history):
                if self.is_eq_func(value, old_val):
                    idx = i
                    break
            else:
                self.history.insert(0, value)
                if len(self.history) > self.max_history:
                    self.history = self.history[:self.max_history]

        if idx != -1:
            self.history.insert(0, self.history[idx])
            del self.history[idx+1]

        self.entry.config(values=self.history)
        self.entry.current([0])


class ChooseDir(HistoryCombo):
    @staticmethod
    def samedir(dir1, dir2):
        try:
            return os.path.samefile(dir1, dir2)
        except FileNotFoundError:
            return False

    def __init__(self, parent, label, width, history, max_history=20):
        super().__init__(parent, label, width, history, max_history=max_history, is_eq_func=ChooseDir.samedir)
        self.icon = ImageTk.PhotoImage(cfg.ICONS['folder'])

        self.button = ttk.Button(self, image=self.icon, command=lambda *args: self.ask_dir())
        self.button.grid(column=2, row=0, sticky=W, padx=5, pady=5)

        if not self.value.get():
            self.value.set(os.path.abspath(""))

    def ask_dir(self):
        opts = {
            "mustexist": False,
            "title": self.title
        }
        if len(self.history) > 0:
            opts['initialdir'] = self.history[0]
        folder = filedialog.askdirectory(**opts)
        if folder:
            self.value.set(folder)

    def get(self):
        folder = os.path.abspath(self.value.get() or "")
        self.value.set(folder)
        return folder


class SeedEntry(ttk.LabelFrame):
    def __init__(self, parent, label, init=None):
        super().__init__(parent, text=label)
        self.rng = random.default_rng()

        self.checked = IntVar()
        self.checkbutton = ttk.Checkbutton(
            self, text="Manual seed", variable=self.checked, command=lambda *args: self.check()
        )
        self.checkbutton.grid(column=0, row=0, stick=W, padx=5, pady=5)
        self.checked.set(0)

        self.value = StringVar()
        self.var_checker = VarChecker(self.value, int, -9223372036854775808, 9223372036854775807)
        self.entry = ttk.Entry(self, width=21, textvariable=self.value, justify=RIGHT, state="readonly",
                               validate='all', validatecommand=self.var_checker.control(self))
        self.var_checker.bind(self.entry)
        self.entry.grid(column=0, row=1, sticky=E, padx=5, pady=5)
        if init is not None:
            self.set(init)

    def get(self) -> int:
        if not self.checked.get() or self.value.get() == "":
            seed = int(self.rng.integers(-9223372036854775808, 9223372036854775807, endpoint=True))
            self.value.set(seed)
        else:
            seed = int(self.value.get())
        return seed

    def set(self, value):
        if not self.checked.get():
            self.checked.set(1)
        self.value.set(value)

    def check(self):
        if not self.checked.get():
            self.entry.config(state="readonly")
        else:
            self.entry.config(state=NORMAL)


class DasScala(ttk.LabelFrame):
    element_locations = {
        N: ((0, 1, (W, E)), (0, 0, (W, E))),
        NW: ((0, 1, (W, E)), (0, 0, W)),
        NE: ((0, 1, (W, E)), (0, 0, E)),
        S: ((0, 0, (W, E)), (0, 1, (W, E))),
        SW: ((0, 0, (W, E)), (0, 1, W)),
        SE: ((0, 0, (W, E)), (0, 1, E)),
        W: ((1, 0, (W, E)), (0, 0, NE)),
        E: ((0, 0, (W, E)), (1, 0, NW))
    }

    def __init__(self, parent, label,
                 from_, to, step, init, tickinterval=None,
                 length=450, width=15, orient=HORIZONTAL, entry_pos=E):
        self.label = ttk.Label(text=label)
        super().__init__(parent, labelwidget=self.label)

        if orient == VERTICAL:
            from_, to = to, from_

        if isinstance(from_, int) and isinstance(to, int) and isinstance(step, int):
            self.val_type = int
        else:
            self.val_type = float

        self.value = StringVar()
        self.value.set(init)

        scale_loc, entry_loc = DasScala.element_locations[entry_pos]

        self.columnconfigure(scale_loc[0], weight=1)
        self.rowconfigure(scale_loc[1], weight=1)

        self.scale = Scale(self,
                           variable=self.value, from_=from_, to=to, resolution=step,
                           orient=orient, showvalue=0, tickinterval=tickinterval,
                           length=length, width=width)
        self.scale.grid(column=scale_loc[0], row=scale_loc[1],
                        sticky=W+E if orient == HORIZONTAL else N+S,
                        padx=5, pady=5)

        self.var_checker = VarChecker(self.value, self.val_type, from_, to, step)
        self.entry = ttk.Entry(self, width=10, textvariable=self.value, justify=RIGHT,
                               validate='all', validatecommand=self.var_checker.control(self))
        self.var_checker.bind(self.entry)
        self.entry.grid(column=entry_loc[0], row=entry_loc[1], sticky=entry_loc[2], padx=5, pady=5)

    def enable(self):
        self.entry.config(state=NORMAL)
        self.scale.config(state=NORMAL)
        self.label.config(state=NORMAL)

    def disable(self):
        self.entry.config(state=DISABLED)
        self.scale.config(state=DISABLED)
        self.label.config(state=DISABLED)

    def get(self):
        return self.val_type(self.value.get())

    def set(self, value):
        return self.value.set(value)


class Size(ttk.LabelFrame):
    def __init__(self, parent, label, range_=None, step=None, defaul=None):
        super().__init__(parent, text=label)

        from_, to = range_ if range_ else (None, None)

        self.checked = IntVar()
        self.checkbutton = ttk.Checkbutton(self, text="Auto", variable=self.checked,
                                           command=lambda *args: self.check())
        self.checkbutton.grid(column=0, row=0, columnspan=4, stick=W, padx=5, pady=5)
        self.checked.set(1)

        self.width, self.height = StringVar(), StringVar()
        self.mem_width = self.mem_height = None
        if defaul is not None:
            self.width.set(defaul[0])
            self.height.set(defaul[1])

        self.wlabel = ttk.Label(self, text="Width:", state=DISABLED)
        self.wlabel.grid(column=0, row=1, sticky=E, padx=5, pady=5)

        self.w_checker = VarChecker(self.width, int, from_, to, step)
        self.w_entry = ttk.Entry(self, width=6, textvariable=self.width, justify=RIGHT, state='readonly',
                                 validate='all', validatecommand=self.w_checker.control(self))
        self.w_checker.bind(self.w_entry)
        self.w_entry.grid(column=1, row=1, sticky=E, padx=5, pady=5)

        self.hlabel = ttk.Label(self, text="Height:", state=DISABLED)
        self.hlabel.grid(column=2, row=1, sticky=E, padx=5, pady=5)

        self.h_checker = VarChecker(self.height, int, from_, to, step)
        self.h_entry = ttk.Entry(self, width=6, textvariable=self.height, justify=RIGHT, state='readonly',
                                 validate='all', validatecommand=self.h_checker.control(self))
        self.h_checker.bind(self.h_entry)
        self.h_entry.grid(column=3, row=1, sticky=E, padx=5, pady=5)

    def check(self):
        if not self.checked.get():
            self.wlabel.config(state=NORMAL)
            self.hlabel.config(state=NORMAL)
            self.w_entry.config(state=NORMAL)
            self.h_entry.config(state=NORMAL)
        else:
            self.wlabel.config(state=DISABLED)
            self.hlabel.config(state=DISABLED)
            self.w_entry.config(state="readonly")
            self.h_entry.config(state="readonly")

    def get(self):
        if self.checked.get():
            return None, None
        return int(self.width.get()), int(self.height.get())

    def set(self, vals):
        self.width.set(vals[0]), self.height.set(vals[1])


class ImageBox(Canvas):
    def __init__(self, parent, width, height):
        super().__init__(parent, width=width, height=height)
        self.width, self.height = width, height
        self.original_image = self.image = None
        self.img_id = None

        self.veil = ImageTk.PhotoImage(Image.new('RGBA', (width, height), (240, 240, 240, 192)))
        self.veil_id = None

        self.default_image = ImageTk.PhotoImage(cfg.PLACEHOLDER_IMAGE.resize((width, height)))
        self.clear()

    def enable(self):
        if self.veil_id is not None:
            self.delete(self.veil_id)
            self.veil_id = None

    def disable(self):
        if self.veil_id is None:
            self.veil_id = self.create_image(0, 0, anchor=NW, image=self.veil)

    def clear(self):
        if self.img_id is not None:
            self.delete(self.img_id)
        self.img_id = self.create_image(0, 0, anchor=NW, image=self.default_image)

    def load(self, image_file):
        self.set(image_files.load(image_file))

    def set(self, image):
        self.original_image = image
        w, h = image.size
        if w > self.width or h > self.height:
            image = image_fit(image, self.width, self.height)
        self.image = ImageTk.PhotoImage(image)
        if self.img_id:
            self.delete(self.img_id)
        self.img_id = self.create_image(self.width // 2, self.height // 2, anchor=CENTER, image=self.image)

    def get(self):
        return self.original_image


class InitImageBox(ttk.LabelFrame):
    image_file_exts = \
        "png?jpg?jpeg?jfif?jpe?pcx?tif?tiff?j2c?j2k?jp2?jpc?jpf?jpx?ico?bmp".replace("?", "?*.").split("?")

    def __init__(self, parent, label, width, history, max_history=20):
        self.checked_var = IntVar(value=0)
        self.chk_button = ttk.Checkbutton(text=label, variable=self.checked_var, command=lambda *args: self.check())

        super().__init__(parent, labelwidget=self.chk_button)
        self.history = history
        self.active = False

        self.columnconfigure(1, weight=1)

        self.image_box = ImageBox(self, 150, 150)
        self.image_box.disable()
        self.image_box.grid(column=0, row=0, rowspan=3, sticky=W, padx=5, pady=5)

        self.open_icon = ImageTk.PhotoImage(cfg.ICONS['open_file'])
        self.open_button = ttk.Button(self, image=self.open_icon, command=lambda *args: self.open(), state=DISABLED)
        self.open_button.grid(column=1, row=0, sticky=E, padx=5, pady=5)

        self.file_combo = HistoryCombo(self, "Image file", width=width,
                                       history=history, max_history=max_history, readonly=True)
        self.file_combo.set("")
        self.file_combo.disable()
        self.file_combo.entry.bind('<<ComboboxSelected>>', lambda *args: self.set(self.file_combo.get()))
        self.file_combo.grid(column=1, row=1, sticky=W+E, padx=5, pady=5)

        self.slider = DasScala(
            self, "Strength",
            from_=0.0, to=1.0, step=0.01, init=0.8, tickinterval=0.2,
            length=300, width=15, orient=HORIZONTAL, entry_pos=E
        )
        self.slider.disable()
        self.slider.grid(column=1, row=2, sticky=W+E, padx=5, pady=5)

    def enable(self):
        self.image_box.enable()
        self.open_button.config(state=NORMAL)
        self.file_combo.enable()
        self.slider.enable()
        self.active = True

    def disable(self):
        self.image_box.disable()
        self.open_button.config(state=DISABLED)
        self.file_combo.disable()
        self.slider.disable()
        self.active = False

    def check(self):
        if self.checked_var.get():
            self.enable()
        else:
            self.disable()

    def get(self):
        return (self.file_combo.get(), self.slider.get()) if self.active else (None, None)

    def set(self, fname):
        if fname:
            try:
                self.image_box.load(fname)
            except Exception as error:
                messagebox.showerror(
                    title="Open file ERROR",
                    message=f"{type(error).__name__} ERROR:\n\n{str(error)}"
                )
                return
            self.file_combo.set(value=fname)

    def open(self):
        opts = {
            'title': "Choose initial image",
            'filetypes': [("Image file", InitImageBox.image_file_exts)],
            'multiple': False
        }
        if len(self.history) > 0:
            opts['initialfile'] = self.history[0]
        self.set(filedialog.askopenfilename(**opts))

    def add_history(self):
        self.file_combo.update_history()
