import numpy as np
from kivy.app import App
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'instance_annotator_screen.kv'))


class InstanceAnnotatorScreen(Screen):
    left_control = ObjectProperty(None)
    right_control = ObjectProperty(None)
    image_canvas = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def on_enter(self, *args):
        self.refresh_image_queue()
        empty_image = np.zeros((2000, 2000, 3), np.uint8)
        self.image_canvas.load_image(utils.mat2texture(empty_image))

    def refresh_image_queue(self):
        print("Refreshing Image Queue")
        utils.get_project_images(
            self.app.current_project_id,
            on_success=self.right_control.image_queue.handle_image_ids)

    def load_image(self, image_id=-1):
        if image_id < 0:
            image_id = 278
            print("Load next Image")
        utils.get_image_by_id(image_id,on_success=self.image_canvas.handle_image_request)



class LeftControlColumn(BoxLayout):
    pass


class ImageCanvas(BoxLayout):
    image = ObjectProperty(None)

    def handle_image_request(self, request, result):
        img_bytes = utils.decode_image(result["image"])
        texture = utils.bytes2texture(img_bytes, "jpg")
        self.load_image(texture)

    def load_image(self, texture):
        self.image.texture = texture
        self.image.size = texture.size

    def get_image(self):
        return self.image_texture


class RightControlColumn(BoxLayout):
    image_queue = ObjectProperty(None)


class ImageQueueControl(GridLayout):
    pass


class ImageQueue(GridLayout):
    def handle_image_ids(self, request, result):
        for image_id in result["ids"]:
            utils.get_image_meta_by_id(
                image_id, on_success=self.handle_image_meta)

    def handle_image_meta(self, request, result):
        self.add_item(result["name"], result["id"])

    def add_item(self, name, id):
        item = ImageQueueItem()
        item.image_name = name
        item.image_id = id
        self.add_widget(item)


class ImageQueueItem(BoxLayout):
    image_name = StringProperty("")
    image_id = NumericProperty(0)
