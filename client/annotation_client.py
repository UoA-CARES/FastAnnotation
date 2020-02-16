from kivy.app import App
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager

from client.screens.project_select_screen import ProjectSelectScreen
from client.screens.project_tool_screen import ProjectToolScreen


class MyScreenManager(ScreenManager):
    """
    Defines the screens which should be included in the ScreenManager at launch.
    Use the ScreenManager to handle transitions between Screens.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(ProjectToolScreen())
        self.add_widget(ProjectSelectScreen())


class AnnotationClientApp(App):
    """
    The launch point for the application itself.
    """

    current_project_name = StringProperty("")
    current_project_id = NumericProperty(0)

    def build(self):
        return MyScreenManager()


if __name__ == "__main__":
    AnnotationClientApp().run()
