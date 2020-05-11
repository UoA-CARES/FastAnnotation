import traceback
import requests
from concurrent.futures import ThreadPoolExecutor
from kivy.app import App
from kivy.config import Config
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager

from client.client_config import ClientConfig
from client.screens.image_view_screen import ImageViewScreen
from client.screens.instance_annotator_screen import InstanceAnnotatorScreen
from client.screens.project_select_screen import ProjectSelectScreen
from client.screens.project_tool_screen import ProjectToolScreen

import client.utils as utils
from client.utils import ApiException
from client.screens.common import Alert

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
    thread_pool = ThreadPoolExecutor(max_workers=ClientConfig.CLIENT_POOL_LIMIT)

    def register_image(self, image_id):
        self.open_images.append(image_id)

    def deregister_image(self, image_id):
        self.open_images.remove(image_id)

    def build(self):
        print("Building")
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

    def show_instance_annotator(self):
        self.sm.current = "InstanceAnnotator"

    def alert_user(self, future):
        if not future.exception():
            return

        exception = future.exception()
        try:
            raise exception
        except Exception:
            tb = traceback.format_exc()
            print(tb)

        pop_up = Alert()
        if isinstance(exception, ApiException):
            pop_up.title = "Server Error: %d" % exception.code
        else:
            pop_up.title = "Unknown Error: %s" % type(exception).__name__
        pop_up.alert_message = str(exception)
        pop_up.open()


if __name__ == "__main__":
    app = AnnotationClientApp()
    try:
        app.run()
    except Exception as e:
        print(str(e))
        tb = traceback.format_exc()
        print(tb)
    finally:
        app.thread_pool.shutdown(wait=True)
        print(app.open_images)
        for iid in app.open_images:
            response = utils.update_image_meta_by_id(iid, lock=False)
            if response.status_code == 200:
                print("Unlocked %d" % iid)
            else:
                print("Failed to unlock %d" % iid)
