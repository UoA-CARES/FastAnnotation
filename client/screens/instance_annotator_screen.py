import kivy.utils
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Fbo, Rectangle, InstructionGroup, Line
from kivy.graphics.texture import Texture
from kivy.properties import BooleanProperty
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *
import cv2

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'instance_annotator_screen.kv'))


class WindowState:
    def __init__(
            self,
            image_id=-1,
            image_name="",
            image_texture=None,
            image_opened=False,
            layer_states=None):
        self.image_id = image_id
        self.image_name = image_name
        self.image_texture = image_texture
        self.image_opened = image_opened
        self.layer_states = layer_states

        if not self.image_texture:
            self.image_texture = utils.mat2texture(
                np.ones(shape=(2000, 2000, 3), dtype=np.uint8))

        if not self.layer_states:
            self.layer_states = [
                LayerState(
                    empty_size=self.image_texture.size)]

    def to_dict(self):
        output = {}
        output['image_id'] = self.image_id
        output['image_name'] = self.image_name
        layers = []
        for state in self.layer_states:
            layers.append(state.to_dict())
        output['annotations'] = layers
        return output


class LayerState:
    class_picker = None

    def __init__(self, drawable_layer=None, config=None, empty_size=None):
        self.mask = None
        self.texture = None
        self.class_name = ""
        self.mask_color = [1, 1, 1, 1]
        self.bbox = None
        if drawable_layer:
            self.texture = drawable_layer.fbo.texture
            self.class_name = drawable_layer.class_name
            self.mask_color = drawable_layer.mask_color
            self.bbox = drawable_layer.bbox_bot_left + drawable_layer.bbox_top_right
        elif config:
            self.mask = utils.decode_mask(
                config["mask"], config["info"]["source_shape"][:2])
            self.class_name = config["info"]["class_name"]
            if self.class_picker:
                self.mask_color = self.class_picker.class_map[self.class_name]
            self.bbox = config["info"]["bbox"]
        elif empty_size:
            self.mask = np.zeros(shape=empty_size, dtype=bool)
            if self.class_picker:
                self.class_name = self.class_picker.current_class.class_name
                self.mask_color = self.class_picker.current_class.class_color
            else:
                self.class_name = ""
                self.mask_color = [1, 1, 1, 1]
        else:
            raise ValueError("One of keyword parameters must be set.")

    @staticmethod
    def bind_class_picker(class_picker):
        LayerState.class_picker = class_picker

    def get_size(self):
        if self.mask is not None:
            return self.mask.shape
        elif self.texture is not None:
            return self.texture.size
        return None

    def get_mask(self):
        if self.mask is not None:
            return self.mask
        self.mask = utils.texture2mat(self.texture)
        self.mask = np.all(self.mask.astype(bool), axis=2)
        return self.mask

    def get_texture(self):
        if self.texture is not None:
            return self.texture
        mat = cv2.cvtColor(
            self.mask.astype(
                np.uint8) * 255,
            cv2.COLOR_GRAY2BGR)
        self.texture = utils.mat2texture(mat)
        return self.texture

    def to_dict(self):
        body = {}
        body['mask'] = utils.encode_mask(self.get_mask())
        info = {
            'source_shape': tuple(
                reversed(
                    self.texture.size)) + (
                3,), 'class_name': self.class_name, 'bbox': np.array(
                    self.bbox).tolist()}

        body['info'] = info
        return body


class InstanceAnnotatorScreen(Screen):
    left_control = ObjectProperty(None)
    right_control = ObjectProperty(None)
    image_canvas = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.current_state = WindowState()
        self.window_cache = {}

    def load_state(self, index):
        if index not in self.window_cache:
            return
        state = self.window_cache[index]

        state.image_opened = True
        self.image_canvas.load_image(state.image_texture, index)
        self.image_canvas.layer_stack.clear()

        layer_name = None
        for layer_state in state.layer_states:
            # Build Layer
            layer = DrawableLayer(
                size=layer_state.get_size(),
                texture=layer_state.get_texture(),
                mask_color=layer_state.mask_color,
                class_name=layer_state.class_name,
                bbox=layer_state.bbox)
            layer.bind_to_draw_tool(self.image_canvas.draw_tool)
            layer.refresh_bbox()

            # Add to LayerStack
            stack_index = self.image_canvas.layer_stack.add_layer(layer)

            # Add to LayerView
            layer_name = "Layer %d" % stack_index
            self.left_control.layer_view.add_layer_item(layer, layer_name)
        self.left_control.layer_view.select_layer_item(layer_name)

        # Record as current state
        self.current_state = state

    # Saves the currently opened state
    def save_state(self):
        if self.image_canvas.image_id not in self.window_cache:
            return

        # Build WindowState
        window_state = self.window_cache[self.image_canvas.image_id]
        window_state.image_texture = self.image_canvas.image.texture
        window_state.image_opened = True

        # Build Layer States
        layer_states = []
        for layer in self.image_canvas.layer_stack.layer_list:
            layer_states.append(LayerState(drawable_layer=layer))

        if layer_states:
            window_state.layer_states = layer_states
        self.window_cache[self.image_canvas.image_id] = window_state

    # Add a new state with a given id
    def add_state(self, image_id, image_name, texture):
        window_state = WindowState(
            image_id=image_id,
            image_name=image_name,
            image_texture=texture,
            image_opened=True
        )
        self.window_cache[image_id] = window_state

    def add_layer(self):
        layer = DrawableLayer(size=self.current_state.image_texture.size)
        # Add to Layer Stack
        stack_index = self.image_canvas.layer_stack.add_layer(layer)

        # Add to Layer View
        layer_name = "Layer %d" % stack_index
        self.left_control.layer_view.add_layer_item(layer, layer_name)
        self.left_control.layer_view.select_layer_item(layer_name)

    def clear_stale_window_states(self):
        stale_keys = []
        for key in self.window_cache:
            if not self.window_cache[key].image_opened:
                stale_keys.append(key)

        for key in stale_keys:
            self.window_cache.pop(key, None)

    def on_enter(self, *args):
        self.left_control.tool_select.bind_draw_tool(
            self.image_canvas.draw_tool)
        self.left_control.layer_view.bind_draw_tool(
            self.image_canvas.draw_tool)
        self.left_control.tool_select.bind_class_picker(
            self.left_control.class_picker)
        self.add_state(image_id=-1, image_name="", texture=None)
        self.load_state(index=-1)
        # self.image_canvas.refresh_image()
        self.refresh_image_queue()

        print("ENTER")
        LayerState.bind_class_picker(self.left_control.class_picker)

        Window.bind(on_resize=self.auto_resize)
        Window.bind(on_keyboard=self.on_keyboard)

    # Entry point for keyboard shortcuts
    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        if modifier == ['ctrl']:
            if codepoint == 'z':
                print("UNDO")
            elif codepoint == 'y':
                print("REDO")

    def auto_resize(self, *args):
        Clock.schedule_once(
            lambda dt: self.image_canvas.load_image(
                self.current_state.image_texture,
                self.current_state.image_id))

    def refresh_image_queue(self):
        print("Refreshing Image Queue")
        # clear queue of stale items
        self.clear_stale_window_states()

        self.right_control.image_queue.clear()
        for state in self.window_cache.values():
            if state.image_opened and state.image_id > 0:
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
        # Save current window state
        self.save_state()

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
            self.load_state(image_id)
            return

        utils.get_image_lock_by_id(image_id,
                                   lock=True,
                                   on_success=self.handle_image_lock_success,
                                   on_fail=self.handle_image_lock_fail)

    def save_image(self):
        self.save_state()
        annotation = self.current_state.to_dict()
        utils.add_image_annotation(self.current_state.image_id, annotation)
        utils.get_image_lock_by_id(self.current_state.image_id,
                                   lock=False,
                                   on_success=self.handle_image_unlock_success)

    def handle_image_lock_success(self, request, result):
        locked_id = result["id"]
        print("Locked Image %d" % locked_id)
        utils.get_image_by_id(
            locked_id,
            on_success=self.handle_image_request_success)
        self.right_control.image_queue.mark_item(
            result["id"], opened=True, locked=False)
        self.right_control.image_queue_control.btn_save.disabled = False

    def handle_image_lock_fail(self, request, result):
        popup = Alert()
        popup.title = "Image unavailable"
        popup.alert_message = "Image is already locked, please try again later."
        popup.open()

    def handle_image_unlock_success(self, request, result):
        unlocked_id = result["id"]
        print("Locked Image %d" % unlocked_id)
        self.window_cache[unlocked_id].image_opened = False
        self.right_control.image_queue.mark_item(
            unlocked_id, opened=False, locked=False)
        self.right_control.image_queue_control.btn_save.disabled = True

    def handle_image_request_success(self, request, result):
        img_bytes = utils.decode_image(result["image"])
        texture = utils.bytes2texture(img_bytes, "jpg")
        self.add_state(
            image_id=result["id"],
            image_name=result["name"],
            texture=texture
        )
        self.load_state(result["id"])
        utils.get_image_annotation(
            result["id"],
            on_success=self.handle_annotation_request_success)

    def handle_annotation_request_success(self, request, result):
        # Add layer state info to correct window state
        window_state = self.window_cache[result["image_id"]]

        layer_states = []
        for row in result["annotations"]:
            layer_states.append(LayerState(config=row))

        if layer_states:
            window_state.layer_states = layer_states

        self.load_state(result["image_id"])


class LeftControlColumn(BoxLayout):
    tool_select = ObjectProperty(None)
    class_picker = ObjectProperty(None)
    layer_view = ObjectProperty(None)


class ToolSelect(GridLayout):
    class_color = ObjectProperty(None)
    class_name = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.draw_tool = None

    def bind_draw_tool(self, draw_tool):
        self.draw_tool = draw_tool

    def bind_class_picker(self, class_picker):
        class_picker.fbind('current_color', self.setter('class_color'))
        class_picker.fbind('current_name', self.setter('class_name'))

    def on_parent(self, *args):
        Clock.schedule_once(lambda dt: self.late_init())

    def late_init(self):
        self.draw_tool = App.get_running_app().root.get_screen(
            "InstanceAnnotator").image_canvas.draw_tool

    def on_class_color(self, *args):
        print("Color: %s" % str(self.class_color))
        self.draw_tool.layer_color = self.class_color[
            :-1] + self.draw_tool.layer_color[-1:]

    def on_class_name(self, *args):
        self.draw_tool.class_name = self.class_name

    def set_alpha(self, alpha):
        print("Alpha: %s" % str(alpha))
        layer_color = self.draw_tool.layer_color
        layer_color = layer_color[:-1] + (alpha,)
        self.draw_tool.layer_color = layer_color

    def set_pencil_size(self, size):
        print("size: %s" % str(size))
        self.draw_tool.pen_size = size


class ClassPicker(GridLayout):
    current_class = ObjectProperty(None)
    current_color = ObjectProperty(None)
    current_name = StringProperty("")
    class_map = {}

    def register(self, item):
        if not isinstance(item, ClassPickerItem):
            return
        self.class_map[item.class_name] = item.class_color

    def change_class(self, instance):
        if self.current_class:
            self.current_class.state = 'normal'
        self.current_class = instance
        self.current_class.state = 'down'

        # Set properties
        self.current_color = self.current_class.class_color
        self.current_name = self.current_class.class_name


class ClassPickerItem(Button):
    class_color = ObjectProperty((0, 0, 0, 1))
    class_name = StringProperty("")
    class_id = NumericProperty(-1)

    def on_parent(self, screen, parent):
        class_picker = parent
        while not isinstance(class_picker, ClassPicker) and class_picker:
            class_picker = class_picker.parent

        if not class_picker:
            return
        Clock.schedule_once(lambda dt: class_picker.register(self))


class LayerView(GridLayout):
    layer_item_layout = ObjectProperty(None)

    layer_item_dict = {}
    current_selection = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.draw_tool = None

    def bind_draw_tool(self, draw_tool):
        self.draw_tool = draw_tool

    def add_layer_item(self, layer, name):
        # Avoid name collisions
        name_copy = name
        copy_i = 1
        while name in self.layer_item_dict:
            name_copy = "%s (%d)" % (name, copy_i)
            copy_i += 1
        name = name_copy

        item = LayerViewItem(name)
        item.bind_to_layer(layer)
        item.bind_to_layer_view(self)

        self.layer_item_dict[name] = item

        self.layer_item_layout.add_widget(item)

    def select_layer_item(self, name):
        if self.current_selection:
            prev_item = self.layer_item_dict[self.current_selection]
            prev_item.unselect()
        self.current_selection = name

        layer_item = self.layer_item_dict[name]
        layer = layer_item.layer

        # Draw Tool bind
        self.draw_tool.set_layer(layer)
        layer_item.select()

        # UI changes

    def clear(self):
        self.layer_item_layout.clear_widgets()
        self.layer_item_dict.clear()


class LayerViewItem(RelativeLayout):
    layer_index = NumericProperty(0)
    layer_name = StringProperty('')
    mask_enabled = BooleanProperty(True)
    bbox_enabled = BooleanProperty(True)
    layer_selected = BooleanProperty(False)

    btn_base = ObjectProperty(None)
    btn_mask = ObjectProperty(None)
    btn_bbox = ObjectProperty(None)

    button_down_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_HIGHLIGHT_1))
    button_up_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.CLIENT_DARK_3))

    def __init__(self, name, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.layer = None
        self.layer_view = None
        self.layer_name = name

    def bind_to_layer(self, layer):
        self.layer = layer
        layer.fbind('mask_visible', self.setter('mask_enabled'))
        layer.fbind('bbox_visible', self.setter('bbox_enabled'))

    def bind_to_layer_view(self, layer_view):
        self.layer_view = layer_view

    def select(self):
        if not self.layer:
            return
        self.layer_selected = True

    def unselect(self):
        if not self.layer:
            return
        self.layer_selected = False

    def on_mask_enabled(self, *args):
        print("test")
        if self.mask_enabled:
            self.btn_mask.background_color = self.button_down_color
            self.btn_mask.state = 'down'
        else:
            self.btn_mask.background_color = self.button_up_color
            self.btn_mask.state = 'normal'

    def on_bbox_enabled(self, *args):
        if self.bbox_enabled:
            self.btn_bbox.background_color = self.button_down_color
            # self.btn_bbox.state = 'down'
        else:
            self.btn_bbox.background_color = self.button_up_color
            # self.btn_bbox.state = 'normal'

    def on_layer_selected(self, *args):
        if self.layer_selected:
            self.layer.bbox_color = kivy.utils.get_color_from_hex(
                ClientConfig.BBOX_SELECT)
            self.btn_base.background_color = self.button_down_color
        else:
            self.layer.bbox_color = kivy.utils.get_color_from_hex(
                ClientConfig.BBOX_UNSELECT)
            self.btn_base.background_color = self.button_up_color

    def toggle_mask(self):
        if self.layer:
            self.layer.toggle_mask()

    def toggle_bbox(self):
        if self.layer:
            self.layer.toggle_bbox()


class DrawTool(MouseDrawnTool):
    layer = ObjectProperty(None)
    pen_size = NumericProperty(10)
    layer_color = ObjectProperty((1, 1, 1, 1))
    class_name = StringProperty("")

    # Stores binding id of last layer
    color_bind = None
    name_bind = None

    def set_layer(self, layer):
        self.layer = layer

        if self.color_bind:
            self.unbind_uid('layer_color', self.color_bind)

        self.color_bind = self.fbind(
            'layer_color', self.layer.setter('mask_color'))

        if self.name_bind:
            self.unbind_uid('class_name', self.name_bind)

        self.name_bind = self.fbind(
            'class_name', self.layer.setter('class_name'))

    def on_touch_down_hook(self, touch):
        if not self.layer:
            return

        pen_radius = self.pen_size / 2
        self.layer.bbox_top_right[0] = np.ceil(max(
            self.layer.bbox_top_right[0], touch.x + np.ceil(pen_radius))).astype(int).tolist()
        self.layer.bbox_top_right[1] = np.ceil(max(
            self.layer.bbox_top_right[1], touch.y + np.ceil(pen_radius))).astype(int).tolist()

        self.layer.bbox_bot_left[0] = np.ceil(min(
            self.layer.bbox_bot_left[0], touch.x - np.ceil(pen_radius))).astype(int).tolist()
        self.layer.bbox_bot_left[1] = np.ceil(min(
            self.layer.bbox_bot_left[1], touch.y - np.ceil(pen_radius))).astype(int).tolist()

        with self.layer.fbo:
            Color(1, 1, 1)
            d = self.pen_size
            Ellipse(
                pos=(touch.x - pen_radius,
                     touch.y - pen_radius),
                size=(d, d))

    def on_touch_move_hook(self, touch):
        self.on_touch_down_hook(touch)

    def on_touch_up_hook(self, touch):
        self.layer.refresh_bbox()


class LayerStack(FloatLayout):
    layer_view = ObjectProperty(None)
    layer_list = ObjectProperty([])
    current_layer = NumericProperty(-1)
    layer_sizes = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def add_layer(self, layer):
        self.add_widget(layer)
        self.layer_list.append(layer)
        return len(self.layer_list) - 1

    # def select_layer(self, index=-1):
    #     if index < 0:
    #         index = self.current_layer + 1
    #     self.current_layer = index
    #     layer = self.layer_list[index]
    #     self.app.root.current_screen.image_canvas.draw_tool.set_layer(layer)
    #
    # def toggle_mask(self):
    #     layer = self.layer_list[self.current_layer]
    #     layer.toggle_mask()
    #
    # def toggle_bbox(self):
    #     layer = self.layer_list[self.current_layer]
    #     layer.toggle_bbox()

    def clear(self):
        self.layer_list = []
        self.current_layer = -1
        self.clear_widgets()
        layer_view = self.app.root.current_screen.left_control.layer_view
        layer_view.clear()

    def save_state(self):
        state = []
        for layer in self.layer_list:
            state.append(LayerState(layer))
        return state

    def load_state(self, state):
        raise NotImplementedError()

        if not state:
            return

        self.clear()
        for layer_state in state:
            layer = DrawableLayer(
                fbo=layer_state.layer_fbo,
                mask_color=layer_state.layer_color)
            layer.refresh_layer()

            self.layer_list.append(layer)
            self.add_widget(layer)
        self.select_layer(len(self.layer_list) - 1)


class DrawableLayer(FloatLayout):
    fbo = ObjectProperty(None)
    class_name = StringProperty("")

    mask_layer = ObjectProperty(None)
    mask_color = ObjectProperty((1, 1, 1, 1))
    mask_visible = BooleanProperty(True)

    bbox_layer = ObjectProperty(None)
    bbox_visible = BooleanProperty(True)
    bbox_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.BBOX_UNSELECT))
    bbox_thickness = NumericProperty(1)

    bbox_top_right = ObjectProperty([])
    bbox_bot_left = ObjectProperty([])
    bbox_bounds = ObjectProperty([0, 0, 0, 0])

    def __init__(
            self,
            size=None,
            texture=None,
            class_name=None,
            mask_color=None,
            bbox=None,
            **kwargs):
        super().__init__(**kwargs)
        if size:
            self.size = size

        if texture:
            self.size = texture.size
            self.texture = texture

        if self.size:
            self.fbo = Fbo(size=self.size, texture=texture)

        if mask_color:
            self.mask_color = mask_color

        if class_name:
            self.class_name = class_name

        self.bbox_top_right = [-1, -1]
        self.bbox_bot_left = [np.iinfo(int).max, np.iinfo(int).max]

        if bbox is not None:
            bbox = np.array(bbox)
            self.bbox_bot_left = list(bbox[:2])
            self.bbox_top_right = list(bbox[2:])

        self.draw_tool = None
        self.layer_view = None
        self.refresh_mask()

    def bind_to_draw_tool(self, draw_tool):
        self.draw_tool = draw_tool

    def bind_to_layer_view(self, layer_view):
        self.layer_view = layer_view

    def refresh_layer(self):
        self.refresh_mask()
        self.refresh_bbox()

    def refresh_mask(self):
        texture = None
        if self.fbo:
            texture = self.fbo.texture

        self.mask_layer.canvas.clear()
        with self.mask_layer.canvas:
            if self.size:
                self.fbo = Fbo(size=self.size, texture=texture)
            Rectangle(size=self.fbo.texture.size, texture=self.fbo.texture)

    def refresh_bbox(self):
        rect = list(self.bbox_bot_left)
        rect += list(np.array(self.bbox_top_right) -
                     np.array(self.bbox_bot_left))

        if not np.all(np.array(rect) > 0):
            rect = [0, 0, 0, 0]
        self.bbox_bounds = rect

    def toggle_mask(self):
        self.mask_visible = not self.mask_visible
        self.mask_layer.canvas.opacity = int(self.mask_visible)

    def toggle_bbox(self):
        self.bbox_visible = not self.bbox_visible
        self.bbox_layer.canvas.opacity = int(self.bbox_visible)


class ImageCanvas(BoxLayout):
    image = ObjectProperty(None)
    image_id = NumericProperty(-1)
    draw_tool = ObjectProperty(None)
    layer_stack = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def load_image(self, texture, image_id):
        self.image_id = image_id
        self.image.texture = texture
        self.image.size = texture.size

    def refresh_image(self):
        print("refreshing")
        window_state = App.get_running_app().root.current_screen.current_state
        self.image.texture = window_state.image_texture
        self.image.size = window_state.image_texture.size
        # self.layer_stack.clear()
        # self.layer_stack.layer_sizes = self.image.size
        # self.layer_stack.add_layer()

    def resize_image(self):
        window_state = App.get_running_app().root.current_screen.current_state
        self.image.texture = window_state.image_texture
        self.image.size = window_state.image_texture.size

    def export_data(self):
        state = self.layer_stack.save_state()
        body = []
        for s in state:
            body.append(s.to_dict())
        return body


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
