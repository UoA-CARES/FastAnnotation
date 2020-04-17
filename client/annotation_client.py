import traceback
import requests
from kivy.app import App
from kivy.config import Config
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager

from client.client_config import ClientConfig
from client.screens.image_view_screen import ImageViewScreen
from client.screens.instance_annotator_screen import InstanceAnnotatorScreen
from client.screens.project_select_screen import ProjectSelectScreen
from client.screens.project_tool_screen import ProjectToolScreen

Config.set('input', 'mouse', 'mouse,disable_multitouch')


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
    open_images = []

    def register_image(self, image_id):
        self.open_images.append(image_id)

    def deregister_image(self, image_id):
        self.open_images.remove(image_id)

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
    app = AnnotationClientApp()
    try:
        app.run()
    except Exception as e:
        print(str(e))
        tb = traceback.format_exc()
        print(tb)
    finally:
        print(app.open_images)
        for image_id in app.open_images:
            url = ClientConfig.SERVER_URL + \
                "images/" + str(image_id) + "/unlock"
            headers = {"Accept": "application/json"}
            response = requests.put(url, headers=headers)
            if response.status_code == 200:
                print("Unlocked %d" % image_id)
            else:
                print("Failed to unlock %d" % image_id)
