from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.clock import mainthread

import client.utils as utils
from client.screens.common import *
from client.utils import ApiException
from client.utils import background
from kivy.clock import mainthread

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
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
            "order_by": {
                "key": "name",
                "ascending": True
            }
        }
        self._load_images(self.app.current_project_id, filter_details)

    @background
    def _load_images(self, pid, filter_details):
        resp = utils.get_project_images(pid, filter_details=filter_details)
        if resp.status_code != 200:
            raise ApiException(
                "Failed to load project images from server.",
                resp.status_code)

        result = resp.json()
        resp = utils.get_images_by_ids(result["ids"], image_data=True, max_dim=ClientConfig.TILE_MAX_DIM)
        result = resp.json()

        for iid in result["ids"]:
            resp = utils.download_image(iid)
            if resp.status_code != 200:
                raise ApiException(
                    "Failed to load image with id %d from server." % iid,
                    resp.status_code)

            img = utils.decode_image(row["image_data"])
            self.add_thumbnail(img)

    @mainthread
    def add_thumbnail(self, image):
        img = utils.bytes2texture(image, "jpg")
        thumbnail = Thumbnail()
        thumbnail.cust_texture = img
        self.tile_view.add_widget(thumbnail)
