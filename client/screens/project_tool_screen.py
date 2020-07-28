import tkinter as tk
from tkinter import filedialog

from kivy.app import App
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *
from client.utils import ApiException
from client.utils import background
from definitions import ROOT_DIR

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
        'project_tool_screen.kv'))


class ProjectToolScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def upload_images(self, *args):
        root = tk.Tk()
        root.withdraw()
        filepath = filedialog.askdirectory(initialdir=ROOT_DIR)
        image_paths = []
        if isinstance(filepath, str):
            for (root, _, filename) in os.walk(filepath):
                for f in filename:
                    # tkinter does not return windows style filepath
                    image_paths.append(root + '/' + f)
        self._upload_images(self.app.current_project_id, image_paths)

    @background
    def _upload_images(self, pid, image_paths):
        resp = utils.add_project_images(pid, image_paths)
        if resp.status_code == 200:
            result = resp.json()
            msg = []
            for row in result["results"]:
                if "error" in row:
                    msg.append(row["error"]["message"])
            msg = '\n'.join(msg)
            raise ApiException(
                message="The following errors occurred while trying to upload images:\n %s" %
                (msg,), code=resp.status_code)
        elif resp.status_code != 201:
            raise ApiException(
                "Failed to upload images to project.",
                resp.status_code)
        else:
            pop_up = Alert()
            pop_up.title = "Success!"
            pop_up.alert_message = "Successfully added new images to the '%s' project" % self.app.current_project_name
            pop_up.open()
