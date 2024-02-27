import tkinter as tk
from tkinter import Tk, ttk
from tkinter.messagebox import askokcancel
from PIL import ImageTk

import cfg
from widgets.inference_tab import InferenceTab


if __name__ == '__main__':
    try:
        cfg.load()
    except Exception as error:
        if not askokcancel(
                title="Warning!",
                message="It seems configuration file is broken. Create default configuration?"
        ):
            raise error

    root = Tk()
    root.title("Diffusers GUI")
    root.wm_iconphoto(True, ImageTk.PhotoImage(cfg.ICONS['favicon']))
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.wm_minsize(1024, 768)

    # Main Frame
    mainframe = ttk.Frame(root)
    mainframe.columnconfigure(1, weight=1)
    mainframe.rowconfigure(1, weight=1)
    mainframe.grid(row=0, column=0, sticky=tk.N+tk.S+tk.W+tk.E, padx=5, pady=5)

    # Notebook
    notebook = ttk.Notebook(mainframe)
    notebook.grid(row=1, column=1, sticky=tk.N+tk.S+tk.W+tk.E, padx=5, pady=5)

    inference_tab = InferenceTab(notebook)
    notebook.add(inference_tab, text="Inference")

    root.mainloop()
