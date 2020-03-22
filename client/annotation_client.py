from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager

from client.screens.project_select_screen import ProjectSelectScreen
from client.screens.project_tool_screen import ProjectToolScreen
from client.screens.image_view_screen import ImageViewScreen
from client.screens.instance_annotator_screen import InstanceAnnotatorScreen


class MyScreenManager(ScreenManager):
    """
    Defines the screens which should be included in the ScreenManager at launch.
    Use the ScreenManager to handle transitions between Screens.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(ProjectSelectScreen(name="ProjectSelect"))
        self.add_widget(ProjectToolScreen(name="ProjectTool"))
        self.add_widget(ImageViewScreen(name="ImageView"))
        self.add_widget(InstanceAnnotatorScreen(name="InstanceAnnotator"))


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

    def show_image_viewer(self):
        self.sm.current = "ImageView"

    def open_instance_annotator(self):
        self.sm.current = "InstanceAnnotator"


if __name__ == "__main__":
    AnnotationClientApp().run()
