import random

import kivy.utils
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Fbo, Rectangle
from kivy.properties import BooleanProperty
from kivy.uix.screenmanager import Screen

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
            image_opened=False):
        self.image_id = image_id
        self.image_name = image_name
        self.image_texture = image_texture
        self.image_opened = image_opened

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

        if new_state.image_opened:
            self.right_control.image_queue.mark_item(
                new_state.image_id, opened=True)

        self.right_control.image_queue_control.btn_save.disabled = not new_state.image_opened
        self.current_state = new_state

    def clear_stale_window_states(self):
        stale_keys = []
        for key in self.window_cache:
            if not self.window_cache[key].image_opened:
                stale_keys.append(key)

        for key in stale_keys:
            self.window_cache.pop(key, None)

    def on_enter(self, *args):
        self.image_canvas.refresh_image()
        self.refresh_image_queue()
        Window.bind(on_resize=self.auto_resize)

    def auto_resize(self, *args):
        Clock.schedule_once(lambda dt: self.image_canvas.refresh_image())

    def refresh_image_queue(self):
        print("Refreshing Image Queue")
        # clear queue of stale items
        self.clear_stale_window_states()

        self.right_control.image_queue.clear()
        for state in self.window_cache.values():
            if state.image_opened:
                self.right_control.image_queue.add_item(
                    state.image_name,
                    state.image_id,
                    opened=True)

        filter_details = {
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
            # For some reason children of a widget are pushed on like a stack
            for w in reversed(self.right_control.image_queue.queue.children):
                if not w.image_locked and not w.image_open:
                    image_id = w.image_id
                    break

            if image_id < 0:
                popup = Alert()
                popup.title = "Out of images"
                popup.alert_message = "There is no valid image to load next. Please try again later or upload more " \
                                      "images to this project. "
                popup.open()
                return
            print("Next image is %d" % image_id)

        if image_id in self.window_cache:
            print("This is the way")
            self.window_cache[image_id].image_opened = True
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
        self.window_cache[unlocked_id].image_opened = False
        self.right_control.image_queue.mark_item(unlocked_id, locked=False)
        self.right_control.image_queue_control.btn_save.disabled = True

    def handle_image_request_success(self, request, result):
        img_bytes = utils.decode_image(result["image"])
        texture = utils.bytes2texture(img_bytes, "jpg")
        new_state = WindowState(
            image_id=result["id"],
            image_name=result["name"],
            image_texture=texture,
            image_opened=True)
        self.load_window_state(new_state)
        self.image_canvas.refresh_image()


class LeftControlColumn(BoxLayout):
    tool_select = ObjectProperty(None)
    class_picker = ObjectProperty(None)


class ToolSelect(GridLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def set_color(self, color):
        print("Color: %s" % str(color))
        layer_color = self.app.root.current_screen.image_canvas.draw_tool.layer_color
        self.app.root.current_screen.image_canvas.draw_tool.layer_color = color[
            :-1] + layer_color[-1:]

    def set_alpha(self, alpha):
        print("Alpha: %s" % str(alpha))
        layer_color = self.app.root.current_screen.image_canvas.draw_tool.layer_color
        layer_color = layer_color[:-1] + (alpha,)
        self.app.root.current_screen.image_canvas.draw_tool.layer_color = layer_color

    def set_pencil_size(self, size):
        print("size: %s" % str(size))
        self.app.root.current_screen.image_canvas.draw_tool.pen_size = size

    def set_layer(self, layer):
        print("LAYER SELECT")


class ClassPicker(GridLayout):
    pass


class ClassPickerItem(Button):
    class_color = ObjectProperty((0, 0, 0, 1))
    class_name = StringProperty("")
    class_id = NumericProperty(-1)


class LayerView(BoxLayout):
    pass


class DrawTool(MouseDrawnTool):
    layer = ObjectProperty(None)
    pen_size = NumericProperty(10)
    layer_color = ObjectProperty((1, 1, 1, 1))

    def set_layer(self, layer):
        self.layer = layer
        self.bind(layer_color=self.layer.setter('col'))

    def on_touch_down_hook(self, touch):
        if not self.layer:
            return

        with self.layer.fbo:
            Color(1, 1, 1)
            d = self.pen_size
            Ellipse(pos=(touch.x - d / 2, touch.y - d / 2), size=(d, d))

    def on_touch_move_hook(self, touch):
        self.on_touch_down_hook(touch)

    def on_touch_up_hook(self, touch):
        if not self.layer:
            return


class DrawableLayer(Image):
    fbo = ObjectProperty(None)
    col = ObjectProperty((1, 1, 1, 1))

    def refresh_layer(self, size):
        self.canvas.clear()
        with self.canvas:
            # create the fbo
            self.fbo = Fbo(size=size)
            Rectangle(size=size, texture=self.fbo.texture)


class ImageCanvas(BoxLayout):
    image = ObjectProperty(None)
    drawable_layer = ObjectProperty(None)
    draw_tool = ObjectProperty(None)

    def refresh_image(self):
        print("refreshing")
        window_state = App.get_running_app().root.current_screen.current_state
        self.image.texture = window_state.image_texture
        self.image.size = window_state.image_texture.size
        self.drawable_layer.refresh_layer(size=window_state.image_texture.size)
        self.draw_tool.set_layer(self.drawable_layer)


class RightControlColumn(BoxLayout):
    image_queue = ObjectProperty(None)
    image_queue_control = ObjectProperty(None)


class ImageQueueControl(GridLayout):
    btn_save = ObjectProperty(None)


class ImageQueue(GridLayout):
    queue = ObjectProperty(None)
    queue_item_dict = {}

    def clear(self):
        self.queue.clear_widgets()
        self.queue_item_dict.clear()

    def mark_item(self, image_id, locked=False, opened=False):
        if image_id not in self.queue_item_dict:
            return
        self.queue_item_dict[image_id].set_status(lock=locked, opened=opened)

    def handle_image_ids(self, request, result):
        # No need to handle existing ids
        new_ids = [x for x in result["ids"]
                   if x not in self.queue_item_dict.keys()]
        utils.get_image_metas_by_ids(
            new_ids, on_success=self.handle_image_meta)

    def handle_image_meta(self, request, result):
        for row in result:
            self.add_item(row["name"], row["id"], locked=row["is_locked"])

    def add_item(self, name, image_id, locked=False, opened=False):
        item = ImageQueueItem()
        item.image_name = name
        item.image_id = image_id
        item.set_status(lock=locked, opened=opened)
        self.queue.add_widget(item)
        self.queue_item_dict[image_id] = item


class ImageQueueItem(BoxLayout):
    image_name = StringProperty("")
    image_id = NumericProperty(0)
    button_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_DARK_3))
    image_open = BooleanProperty(False)
    image_locked = BooleanProperty(False)

    def set_status(self, opened=False, lock=False):
        self.image_open = opened
        self.image_locked = lock
        if opened:
            self.button_color = kivy.utils.get_color_from_hex(
                ClientConfig.CLIENT_HIGHLIGHT_1)
        else:
            self.button_color = kivy.utils.get_color_from_hex(
                ClientConfig.CLIENT_DARK_3)
