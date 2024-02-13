from tkinter import Tk, PhotoImage
from mainframe import MainFrame

root = Tk()
root.title("Diffusers GUI")
favicon = PhotoImage(file='Icons//favicon.png')
root.wm_iconphoto(False, favicon)

# Main Frame
mainframe = MainFrame(root, "config.yml")

root.mainloop()
