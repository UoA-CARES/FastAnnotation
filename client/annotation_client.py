from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

from client.screens.project_screen import ProjectScreen


class MyScreenManager(ScreenManager):
    """
    Defines the screens which should be included in the ScreenManager at launch.
    Use the ScreenManager to handle transitions between Screens.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(ProjectScreen())


class AnnotationClientApp(App):
    """
    The launch point for the application itself.
    """

    def build(self):
        return MyScreenManager()


if __name__ == "__main__":
    AnnotationClientApp().run()
