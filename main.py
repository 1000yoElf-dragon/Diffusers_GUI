from tkinter import Tk, PhotoImage
from mainframe import MainFrame

root = Tk()
root.title("Diffusers GUI")
favicon = PhotoImage(file='Icons//favicon.png')
root.wm_iconphoto(False, favicon)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
# Main Frame
mainframe = MainFrame(root, "config.yml")
root.mainloop()
