from kivy.app import App
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'image_view_screen.kv'))


class Thumbnail(BoxLayout):
    cust_texture = ObjectProperty(None)


class ImageViewScreen(Screen):
    tile_view = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def on_enter(self, *args):
        # TODO: Optimize to cache previously retrieved data
        self.tile_view.clear_widgets()
        print("Loading Images")
        filter_details = {
            "order": {
                "by": "name",
                "ascending": True
            }
        }
        utils.get_project_images(
            self.app.current_project_id,
            filter_details=filter_details,
            on_success=self._get_image_ids_success)

    def _get_image_ids_success(self, request, result):
        print("Ids: %s" % str(result["ids"]))

        utils.get_images_by_ids(
            result["ids"],
            on_success=self._on_load_images_success,
            on_fail=self._on_load_images_fail)

    def _on_load_images_success(self, request, result):
        for row in result:
            img = utils.decode_image(row["image"])
            self.add_thumbnail(img)

    def _on_load_images_fail(self, request, result):
        print("FAILED")

    def add_thumbnail(self, image):

        img = utils.bytes2texture(image, "jpg")
        thumbnail = Thumbnail()
        thumbnail.cust_texture = img
        self.tile_view.add_widget(thumbnail)
