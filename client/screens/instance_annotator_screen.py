import numpy as np
from kivy.app import App
from kivy.uix.screenmanager import Screen
import kivy.utils

import client.utils as utils
from client.screens.common import *

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'instance_annotator_screen.kv'))

# TODO:
# Need to draw signal diagrams to optimze flows for UI interactions
# Might need to optimize REST calls
# Figure out how images will be represented when open


class WindowState:
    def __init__(
            self,
            image_id=-1,
            image_name="",
            image_texture=None,
            image_locked=False):
        self.image_id = image_id
        self.image_name = image_name
        self.image_texture = image_texture
        self.image_locked = image_locked

        if not self.image_texture:
            empty_image = np.zeros((2000, 2000, 3), np.uint8)
            self.image_texture = utils.mat2texture(empty_image)


class InstanceAnnotatorScreen(Screen):
    left_control = ObjectProperty(None)
    right_control = ObjectProperty(None)
    image_canvas = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.current_state = WindowState()
        self.window_cache = {}

    def load_window_state(self, new_state):
        if new_state.image_id is not -1:
            self.window_cache[new_state.image_id] = new_state

        if new_state.image_locked:
            self.right_control.image_queue.mark_item(
                new_state.image_id, locked=True)

        self.right_control.image_queue_control.btn_save.disabled = not new_state.image_locked
        self.current_state = new_state

    def clear_stale_window_states(self):
        stale_keys = []
        for key in self.window_cache:
            if not self.window_cache[key].image_locked:
                stale_keys.append(key)

        for key in stale_keys:
            self.window_cache.pop(key, None)

    def on_enter(self, *args):
        self.refresh_image_queue()
        self.image_canvas.refresh_image()

    def refresh_image_queue(self):
        print("Refreshing Image Queue")
        # clear queue of stale items
        self.clear_stale_window_states()

        self.right_control.image_queue.queue.clear_widgets()
        for state in self.window_cache.values():
            if state.image_locked:
                self.right_control.image_queue.add_item(
                    state.image_name,
                    state.image_id,
                    locked=True)

        filter_details = {
            "filter": {
                "locked": False,
                "labelled": False
            },
            "order": {
                "by": "name",
                "ascending": True
            }
        }
        utils.get_project_images(
            self.app.current_project_id,
            filter_details=filter_details,
            on_success=self.right_control.image_queue.handle_image_ids)

    def load_image(self, image_id=-1):
        if image_id < 0:
            image_id = 278
            print("Load next Image")

        if image_id in self.window_cache:
            self.window_cache[image_id].image_locked = True
            self.load_window_state(self.window_cache[image_id])
            self.image_canvas.refresh_image()
            return

        utils.get_image_lock_by_id(image_id,
                                   lock=True,
                                   on_success=self.handle_image_lock_success,
                                   on_fail=self.handle_image_lock_fail)

    def save_image(self):
        utils.get_image_lock_by_id(self.current_state.image_id,
                                   lock=False,
                                   on_success=self.handle_image_unlock_success)

    def handle_image_lock_success(self, request, result):
        locked_id = result["id"]
        print("Locked Image %d" % locked_id)
        utils.get_image_by_id(
            locked_id,
            on_success=self.handle_image_request_success)

    def handle_image_lock_fail(self, request, result):
        popup = Alert()
        popup.title = "Image unavailable"
        popup.alert_message = "Image is already locked, please try again later."
        popup.open()

    def handle_image_unlock_success(self, request, result):
        unlocked_id = result["id"]
        print("Locked Image %d" % unlocked_id)
        self.window_cache[unlocked_id].image_locked = False
        self.right_control.image_queue.mark_item(unlocked_id, locked=False)
        self.right_control.image_queue_control.btn_save.disabled = True

    def handle_image_request_success(self, request, result):
        img_bytes = utils.decode_image(result["image"])
        texture = utils.bytes2texture(img_bytes, "jpg")
        new_state = WindowState(
            image_id=result["id"],
            image_name=result["name"],
            image_texture=texture,
            image_locked=True)
        self.load_window_state(new_state)
        self.image_canvas.refresh_image()


class LeftControlColumn(BoxLayout):
    pass


class ImageCanvas(BoxLayout):
    image = ObjectProperty(None)

    def refresh_image(self):
        window_state = App.get_running_app().root.current_screen.current_state
        self.image.texture = window_state.image_texture
        self.image.size = window_state.image_texture.size


class RightControlColumn(BoxLayout):
    image_queue = ObjectProperty(None)
    image_queue_control = ObjectProperty(None)


class ImageQueueControl(GridLayout):
    btn_save = ObjectProperty(None)


class ImageQueue(GridLayout):
    queue = ObjectProperty(None)

    def mark_item(self, image_id, locked=True):
        for w in self.queue.children:
            if w.image_id == image_id:
                w.lock(locked)

    def handle_image_ids(self, request, result):
        utils.get_image_metas_by_ids(
            result["ids"], on_success=self.handle_image_meta)

    def handle_image_meta(self, request, result):
        for row in result:
            self.add_item(row["name"], row["id"])

    def add_item(self, name, id, locked=False):
        item = ImageQueueItem()
        item.image_name = name
        item.image_id = id
        item.image_locked = locked
        item.lock(locked)
        self.queue.add_widget(item)


class ImageQueueItem(BoxLayout):
    image_name = StringProperty("")
    button_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_DARK_3))
    image_locked = BooleanProperty(False)

    def lock(self, lock=True):
        self.image_locked = lock
        if lock:
            self.button_color = kivy.utils.get_color_from_hex(
                ClientConfig.CLIENT_HIGHLIGHT_1)
        else:
            self.button_color = kivy.utils.get_color_from_hex(
                ClientConfig.CLIENT_DARK_3)
