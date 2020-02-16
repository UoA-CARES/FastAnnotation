import tkinter as tk
from tkinter import filedialog

from kivy.app import App
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.definitions import ROOT_DIR
from client.screens.common import *

# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'project_tool_screen.kv'))


class ProjectToolScreen(Screen):
    action_previous = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def upload_images(self, *args):
        root = tk.Tk()
        root.withdraw()
        filepath = filedialog.askdirectory(initialdir=ROOT_DIR)
        image_paths = []
        for (root, _, filename) in os.walk(filepath):
            for f in filename:
                # tkinter does not return windows style filepath
                image_paths.append(root + '/' + f)
        utils.add_project_images(
            self.app.current_project_id,
            image_paths,
            on_fail=self._upload_images_failure)

    def _upload_images_failure(self, request, result):
        popup = Alert()
        popup.alert_message = "Failed to upload the requested images"
        popup.open()

    def on_enter(self, *args):
        self.app.current_project_id = 31
        self.action_previous.title = self.app.current_project_name
