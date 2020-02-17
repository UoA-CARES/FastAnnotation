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
        self.add_widget(ProjectSelectScreen(name="ProjectSelect"))
        self.add_widget(ProjectToolScreen(name="ProjectTool"))


class AnnotationClientApp(App):
    """
    The launch point for the application itself.
    """

    current_project_name = StringProperty("")
    current_project_id = NumericProperty(0)
    sm = None

    def build(self):
        self.sm = MyScreenManager()
        return self.sm

    def show_project_tools(self, name, id):
        self.current_project_name = name
        self.current_project_id = id
        self.sm.current = "ProjectTool"

    def show_home(self):
        self.sm.current = "ProjectSelect"


if __name__ == "__main__":
    AnnotationClientApp().run()
