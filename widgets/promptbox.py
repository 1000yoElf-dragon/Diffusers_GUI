import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import ImageTk

import cfg
from utils import not_include, normalize_space_commas, append_non_zero, strip_quotes
from filehandlers import text_files
from .common import HistoryCombo


def load_text_file(filename, missed):
    try:
        if os.path.getsize(filename) > cfg.ADPROMPT_MAXLEN:
            missed[filename] = "File is too big"
            return None
        return text_files.load(filename).strip()
    except Exception as error:
        missed[filename] = str(error)
        return ""


def find_adprompt(adprompt_path, token: str, missed: dict):
    adprompt_path = os.path.realpath(adprompt_path)
    filename = strip_quotes(token)
    if not filename: return None
    if not os.path.dirname(filename):
        if not filename.lower().endswith(".txt"): filename += ".txt"
        filename = os.path.realpath(os.path.join(adprompt_path, filename))
        external = False
    else:
        filename = os.path.realpath(filename)
        external = os.path.dirname(filename) != adprompt_path or not filename.lower().endswith(".txt")
    if filename in missed: return None
    if not os.path.isfile(filename):
        missed[filename] = "Can't find path to file"
        return None
    if external:
        display_name = token
    else:
        display_name = os.path.splitext(os.path.basename(filename))[0]
    return filename, external, display_name


def get_adprompt_list(adprompt_path, negative: bool = None):
    missed = {}
    items = []
    for direntry in os.scandir(adprompt_path):
        item = find_adprompt(adprompt_path, direntry.name, missed)
        if item is None or\
                negative is not None and (negative ^ (item[2][0] == '!')):
            continue
        items.append(item)
    items.sort(key=lambda x: x[2])
    items.append((None, False, "*PROMPT*"))
    return items


class ScrolledList(ttk.Frame):
    def __init__(self, parent, label, allow_multiple=True, bg1='#FFFFFF', bg2='#F8F8FF'):
        super(ScrolledList, self).__init__(parent)

        self.selectmode = tk.EXTENDED if allow_multiple else tk.BROWSE
        self.bg1 = bg1
        self.bg2 = bg2

        self.columnconfigure(0, weight=1, minsize=125)
        self.rowconfigure(1, weight=1, minsize=125)

        self.values = tk.StringVar()

        self.label = ttk.Label(self, text=label)
        self.label.grid(row=0, column=0, padx=5, pady=5)

        self.y_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.y_scroll.grid(row=1, column=1, sticky=tk.N + tk.S)

        self.listbox = tk.Listbox(
            self, listvariable=self.values, selectmode=self.selectmode, yscrollcommand=self.y_scroll.set
        )
        self.listbox.grid(row=1, column=0, rowspan=4, sticky=tk.N + tk.S + tk.W + tk.E)
        self.y_scroll['command'] = self.listbox.yview

    def alternate_lines(self):
        n = self.listbox.size()
        for i in range(0, n, 2):
            self.listbox.itemconfigure(i, background=self.bg1)
        for i in range(1, n, 2):
            self.listbox.itemconfigure(i, background=self.bg2)


class AdPromptList(ttk.Frame):
    def __init__(self, parent):
        super(AdPromptList, self).__init__(parent)

        self.columnconfigure(1, weight=1, minsize=150)
        self.columnconfigure(3, weight=1, minsize=150)
        self.rowconfigure(1, weight=1, minsize=50)
        self.rowconfigure(4, weight=1, minsize=50)

        self.return_command = lambda result: None

        self.adprompt_path = ""
        self.old_adprompt_string = ""
        self.negative = False
        self.choosen_items = []
        self.choosen_names = []
        self.available_items = []
        self.available_names = []

        self.label_var = tk.StringVar()
        self.label = ttk.Label(self, textvariable=self.label_var)
        self.label.grid(row=0, column=0, columnspan=4, padx=5, pady=5)

        # Choosen list
        self.choosen_list = ScrolledList(self, "Choosen adPrompts", allow_multiple=False)
        self.choosen_list.grid(row=1, column=1, rowspan=4, sticky=tk.N + tk.S + tk.W + tk.E, padx=5, pady=5)

        # Available list
        self.available_list = ScrolledList(self, "Saved adPrompts", allow_multiple=False)
        self.available_list.grid(row=1, column=3, rowspan=4, sticky=tk.N + tk.S + tk.W + tk.E, padx=5, pady=5)

        # Ordering buttons
        self.arrow_up = ImageTk.PhotoImage(cfg.ICONS['arrow_up'])
        self.arrow_down = ImageTk.PhotoImage(cfg.ICONS['arrow_down'])
        self.move_up_button = ttk.Button(self, image=self.arrow_up, command=lambda *args: self.move_up())
        self.move_up_button.grid(row=2, column=0, padx=5, pady=5)
        self.move_down_button = ttk.Button(self, image=self.arrow_down, command=lambda *args: self.move_down())
        self.move_down_button.grid(row=3, column=0, padx=5, pady=5)

        # Selection buttons
        self.arrow_left = ImageTk.PhotoImage(cfg.ICONS['arrow_left'])
        self.arrow_trash = ImageTk.PhotoImage(cfg.ICONS['arrow_trash'])
        self.choose_button = ttk.Button(self, image=self.arrow_left, command=lambda *args: self.choose())
        self.choose_button.grid(row=2, column=2, padx=5, pady=5)
        self.drop_button = ttk.Button(self, image=self.arrow_trash, command=lambda *args: self.trash())
        self.drop_button.grid(row=3, column=2, padx=5, pady=5)

        # Opposite checkbox
        self.opposite_var = tk.IntVar(value=0)
        self.opposite_check = ttk.Checkbutton(
            self, text="Show opposite", variable=self.opposite_var, command=lambda *args: self.opposite()
        )
        self.opposite_check.grid(row=5, column=3, sticky=tk.W, padx=5, pady=5)

        # Finalize buttons
        self.finalize_frame = ttk.Frame(self)
        self.ok_button = ttk.Button(self.finalize_frame, text="OK", command=lambda *args: self.ok_close())
        self.ok_button.grid(row=0, column=0, padx=5, pady=5)
        self.cancel_button = ttk.Button(self.finalize_frame, text="Cancel", command=lambda *args: self.cancel())
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5)
        self.finalize_frame.grid(row=6, column=0, columnspan=4, sticky=tk.E, padx=5, pady=5)
        self.first_bind_id = self.bind('<Visibility>', lambda *args: self.hide_at_start())

    def hide_at_start(self):
        self.unbind('<Visibility>', self.first_bind_id)
        self.grid_remove()

    def activate(self, label, adprompt_path, adprompt_string, negative, return_command):
        self.label_var.set(label)

        self.return_command = return_command
        self.adprompt_path = adprompt_path
        self.old_adprompt_string = adprompt_string
        self.negative = negative

        self.choosen_items = []
        missed = {}
        for token in adprompt_string.split('+'):
            token = strip_quotes(token)
            if token == '?':
                self.choosen_items.append((None, False, "*PROMPT*"))
            else:
                append_non_zero(self.choosen_items, find_adprompt(adprompt_path, token, missed))
        self.choosen_names = [f"<file: {x[2]}>" if x[1] else x[2] for x in self.choosen_items]

        self.available_items = get_adprompt_list(adprompt_path, negative)
        self.available_names = [x[2] for x in self.available_items]

        self.choosen_list.values.set(self.choosen_names)
        self.choosen_list.alternate_lines()

        self.available_list.values.set(self.available_names)
        self.available_list.alternate_lines()

        self.opposite_var.set(0)

        self.grid()
        self.lift()

    def opposite(self):
        if not self.opposite_var.get():
            self.available_items = get_adprompt_list(self.adprompt_path, self.negative)
        else:
            self.available_items = get_adprompt_list(self.adprompt_path, None)
        self.available_names = [x[2] for x in self.available_items]
        self.available_list.values.set(self.available_names)
        self.available_list.alternate_lines()

    def move_up(self):
        sel = self.choosen_list.listbox.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            self.choosen_items[i], self.choosen_items[i - 1] = self.choosen_items[i - 1], self.choosen_items[i]
            self.choosen_names[i], self.choosen_names[i - 1] = self.choosen_names[i - 1], self.choosen_names[i]
            self.choosen_list.values.set(self.choosen_names)
            self.choosen_list.alternate_lines()
            self.choosen_list.listbox.selection_clear(i)
            self.choosen_list.listbox.selection_set(i-1)

    def move_down(self):
        sel = self.choosen_list.listbox.curselection()
        if sel and sel[0] < len(self.choosen_items)-1:
            i = sel[0]
            self.choosen_items[i], self.choosen_items[i + 1] = self.choosen_items[i + 1], self.choosen_items[i]
            self.choosen_names[i], self.choosen_names[i + 1] = self.choosen_names[i + 1], self.choosen_names[i]
            self.choosen_list.values.set(self.choosen_names)
            self.choosen_list.alternate_lines()
            self.choosen_list.listbox.selection_clear(i)
            self.choosen_list.listbox.selection_set(i + 1)

    def choose(self):
        sel = self.available_list.listbox.curselection()
        if sel:
            self.choosen_items.append(self.available_items[sel[0]])
            self.choosen_names.append(self.available_names[sel[0]])
            self.choosen_list.values.set(self.choosen_names)
            self.choosen_list.alternate_lines()

    def trash(self):
        sel = self.choosen_list.listbox.curselection()
        if sel:
            del self.choosen_items[sel[0]]
            del self.choosen_names[sel[0]]
            self.choosen_list.values.set(self.choosen_names)
            self.choosen_list.alternate_lines()

    def ok_close(self):
        if not self.choosen_names:
            adprompt_string = "?"
        else:
            if not self.choosen_items[0][0]:
                adprompt_string = "?"
            else:
                adprompt_string = self.choosen_items[0][2]
            for item in self.choosen_items[1:]:
                if not item[0]:
                    adprompt_string += " + ?"
                else:
                    adprompt_string += f" + {item[2]}"
        if '?' not in adprompt_string:
            adprompt_string = '? + ' + adprompt_string
        self.return_command(adprompt_string)
        self.grid_remove()

    def cancel(self):
        self.return_command(self.old_adprompt_string)
        self.grid_remove()


class PromptBox(ttk.LabelFrame):

    def __init__(self, parent, label, width, height,
                 negative, adprompt_path, adprompt_history,
                 adprompt_list: AdPromptList, adprompt_max_history=20,
                 init="", maxundo=8192, max_history=50):
        super().__init__(parent, text=label)

        self.negative = negative
        self.adprompt_path = adprompt_path

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self.history = []
        self.current = -1
        self.max_history = max_history

        self.adprompt_list = adprompt_list

        self.text = ScrolledText(self, width=width, height=height, undo=True, maxundo=maxundo, wrap=tk.WORD)
        self.text.grid(column=0, row=1, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        self.set(init)

        self.adprompt = HistoryCombo(self, "adPrompt: ", width,
                                     adprompt_history, max_history=adprompt_max_history,
                                     is_eq_func=None, validator=not_include('\\/:*»<>|'), readonly=False)
        self.adprompt.entry.bind('<FocusOut>', lambda *args: self.adprompt_validate())

        self.plus_icon = ImageTk.PhotoImage(cfg.ICONS['plus'])
        self.plus_ad_button = ttk.Button(self.adprompt, image=self.plus_icon,
                                         command=lambda *args: self.plus_ad())
        self.plus_ad_button.grid(column=2, row=0, padx=5, pady=5)
        self.adprompt.grid(column=0, row=2, columnspan=2, sticky=tk.W + tk.E + tk.N + tk.S, padx=5, pady=5)

        # Edit buttons
        self.edit_buttons = ttk.Frame(self)
        self.clear_button = ttk.Button(self.edit_buttons, text="Clear", command=lambda *args: self.clear())
        self.clear_button.grid(column=0, row=0, sticky=tk.E)

        # History buttons
        self.forward_icon = ImageTk.PhotoImage(cfg.ICONS['forward'])
        self.backward_icon = ImageTk.PhotoImage(cfg.ICONS['backward'])
        self.history_buttons = ttk.Frame(self)
        self.back_button = ttk.Button(self.history_buttons, image=self.backward_icon,
                                      command=lambda *args: self.back(), state=tk.DISABLED)
        self.back_button.grid(column=0, row=0, sticky=tk.E)
        self.forward_button = ttk.Button(self.history_buttons, image=self.forward_icon,
                                         command=lambda *args: self.forward(), state=tk.DISABLED)
        self.forward_button.grid(column=1, row=0, sticky=tk.E)

        self.edit_buttons.grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.history_buttons.grid(column=1, row=0, sticky=tk.E, padx=5, pady=5)

    def adprompt_validate(self):
        adprompt = self.adprompt.get().strip()
        if not adprompt.strip('+ \t\n\r'):
            self.adprompt.set("?")
            return "?"
        if adprompt[0] == '+':
            adprompt = '? ' + adprompt
        if adprompt[-1] == '+':
            adprompt += ' ?'
        if '?' not in adprompt:
            adprompt = '? + ' + adprompt
        self.adprompt.set(adprompt)
        return adprompt

    def plus_ad(self):
        self.adprompt_list.activate(
            label=f"Choose additions to the {'negative ' if self.negative else ''}prompt",
            adprompt_path=self.adprompt_path, adprompt_string=self.adprompt_validate(), negative=self.negative,
            return_command=lambda result: self.adprompt.set(result)
        )

    def exit_apl(self, result):
        self.adprompt.set(result)

    def get(self):
        missed = {}
        prompt = self.text.get('0.0', tk.END)
        prompt_seq = []
        length = len(prompt)
        pos = 0
        while pos < length:
            next_pos = prompt.find('@<', pos)
            next_pos = next_pos if next_pos != -1 else length
            append_non_zero(prompt_seq, prompt[pos:next_pos].strip())
            pos = next_pos+2
            if pos >= length:
                break
            next_pos = prompt.find('>', pos)
            next_pos = next_pos if next_pos != -1 else length
            status = find_adprompt(self.adprompt_path, prompt[pos:next_pos], missed)
            if status:
                append_non_zero(prompt_seq, load_text_file(status[0], missed))
            pos = next_pos+1

        result_seq = []

        for token in self.adprompt_validate().split('+'):
            token = token.strip()
            if not token:
                continue
            if token == '?':
                result_seq += prompt_seq
            else:
                status = find_adprompt(self.adprompt_path, token, missed)
                if status:
                    append_non_zero(result_seq, load_text_file(status[0], missed))

        if missed:
            message = "Can't load adprompt(s). Continue anyway?\n\n"
            for i, (name, error) in enumerate(missed.items()):
                message += f"{name}: {error}\n"
                if i >= 10:
                    message += '...'
                    break
            if not messagebox.askokcancel("Adprompt ERROR", message):
                raise ValueError("Wrong adprompt(s)")

        result = normalize_space_commas(', '.join(result_seq))
        return result

    def set(self, txt):
        self.text.delete('0.0', tk.END)
        self.text.insert('0.0', txt)
        self.text.edit_modified(True)

    def update_buttons(self):
        if len(self.history) == 0:  # or self.current == 0 and not self.text.edit_modified():
            self.back_button.config(state=tk.DISABLED)
        else:
            self.back_button.config(state=tk.NORMAL)

        if self.current >= len(self.history) - 1:
            self.forward_button.config(state=tk.DISABLED)
        else:
            self.forward_button.config(state=tk.NORMAL)

    def update_history(self):
        self.adprompt.update_history()
        if not self.history or self.text.edit_modified():
            self.history.append(self.text.get('0.0', tk.END))
        elif 0 <= self.current < len(self.history):
            self.history.append(self.history[self.current])
            del self.history[self.current]
        self.current = len(self.history) - 1
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self.text.edit_modified(False)
        self.update_buttons()

    def focus(self):
        self.text.focus()

    def clear(self):
        self.text.delete('0.0', tk.END)
        self.text.edit_modified(True)
        self.update_buttons()

    def forward(self):
        if self.current < len(self.history)-1:
            self.current += 1
            self.set(self.history[self.current])
            self.text.edit_modified(False)
        self.update_buttons()

    def back(self):
        if self.current < 0:
            return
        if not self.text.edit_modified():
            if self.current > 0:
                self.current -= 1
            else:
                return
        self.set(self.history[self.current])
        self.text.edit_modified(False)
        self.update_buttons()
