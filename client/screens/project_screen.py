import os

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen

from client.definitions import SCREEN_DIR

# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'project_screen.kv'))


class ProjectScreen(Screen):
    pass


class ProjectCard:
    pass


class ProjectViewWindow:
    pass
