from client.screens.common import *
from kivy.uix.screenmanager import Screen

from client.definitions import ROOT_DIR
import tkinter as tk
from tkinter import filedialog


# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'project_tool_screen.kv'))


class ProjectToolScreen(Screen):
    def open_file_chooser(self, *args):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askdirectory(initialdir=ROOT_DIR)
        print(file_path)


class FileChooserPopup(Popup):
    default_path = StringProperty("")
