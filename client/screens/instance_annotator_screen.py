import cv2
import kivy.utils
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, InstructionGroup, Line
from kivy.properties import BooleanProperty
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *

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
                np.ones(shape=(3000, 3000, 3), dtype=np.uint8))

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
        # bbox in (x1, y1, x2, y2) format
        self.bbox = None
        if drawable_layer:
            self.texture = drawable_layer.get_fbo().texture
            self.class_name = drawable_layer.class_name
            self.mask_color = drawable_layer.mask_color
            self.bbox = drawable_layer.bbox_bounds
            self.bbox[2] += drawable_layer.bbox_bounds[0]
            self.bbox[3] += drawable_layer.bbox_bounds[1]
        elif config:
            self.mask = utils.decode_mask(
                config["mask_data"], config["shape"][:2])
            self.class_name = config["class_name"]
            if self.class_picker:
                self.mask_color = self.class_picker.class_map[self.class_name]
            self.bbox = config["bbox"]
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
        body['mask_data'] = utils.encode_mask(self.get_mask())
        body['bbox'] = np.array(self.bbox).tolist()
        body['class_name'] = self.class_name
        body['shape'] = tuple(reversed(self.texture.size)) + (3,)
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

    def on_enter(self, *args):
        # Tool Select Binds
        self.left_control.tool_select.bind_draw_tool(
            self.image_canvas.draw_tool)
        self.left_control.tool_select.bind_class_picker(
            self.left_control.class_picker)
        self.left_control.tool_select.bind_layer_stack(
            self.image_canvas.layer_stack)

        # Layer View Binds
        self.left_control.layer_view.bind_draw_tool(
            self.image_canvas.draw_tool)
        self.left_control.layer_view.bind_layer_stack(
            self.image_canvas.layer_stack)

        # Draw Tool Binds
        self.image_canvas.draw_tool.bind_layer_view(
            self.left_control.layer_view)
        self.image_canvas.draw_tool.bind_class_picker(
            self.left_control.class_picker)
        self.image_canvas.draw_tool.bind_keyboard()

        self.add_state(image_id=-1, image_name="", texture=None)
        self.load_state(index=-1)
        self.refresh_image_queue()

        print("ENTER")
        LayerState.bind_class_picker(self.left_control.class_picker)

        Window.bind(on_resize=self.auto_resize)

    def on_leave(self, *args):
        self.image_canvas.draw_tool.unbind_keyboard()

    def auto_resize(self, *args):
        Clock.schedule_once(
            lambda dt: self.image_canvas.load_image(
                self.current_state.image_texture,
                self.current_state.image_id))

    def load_state(self, index):
        if index not in self.window_cache:
            return
        state = self.window_cache[index]

        state.image_opened = True
        self.image_canvas.load_image(state.image_texture, index)
        self.left_control.layer_view.clear()

        layer_name = None
        for layer_state in state.layer_states:
            # Build Layer
            layer = DrawableLayer(
                size=layer_state.get_size(),
                mask_color=layer_state.mask_color,
                class_name=layer_state.class_name,
                texture=layer_state.get_texture(),
                bbox=layer_state.bbox)
            layer_name = self.left_control.layer_view.add_layer_item(layer)
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
        window_state.layer_states[0].mask_color = self.left_control.class_picker.current_color
        self.window_cache[image_id] = window_state

    def add_layer(self):
        layer = DrawableLayer(size=self.current_state.image_texture.size)
        layer.mask_color = self.left_control.class_picker.current_color[:3] + \
                           (self.left_control.tool_select.alpha.value,)
        layer_name = self.left_control.layer_view.add_layer_item(layer)
        self.left_control.layer_view.select_layer_item(layer_name)
        
    def clear_stale_window_states(self):
        stale_keys = []
        for key in self.window_cache:
            if not self.window_cache[key].image_opened:
                stale_keys.append(key)

        for key in stale_keys:
            self.window_cache.pop(key, None)

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
            "order_by": {
                "key": "name",
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

        utils.update_image_meta_by_id(image_id,
                                      lock=True,
                                      on_success=self.handle_image_lock_success,
                                      on_fail=self.handle_image_lock_fail)

    def save_image(self):
        self.save_state()
        annotation = self.current_state.to_dict()
        utils.add_image_annotation(self.current_state.image_id, annotation, on_success=self.handle_annotation, on_fail=self.handle_annotation)
        utils.update_image_meta_by_id(self.current_state.image_id,
                                      lock=False,
                                      on_success=self.handle_image_unlock_success, on_fail=self.handle_annotation)

    def handle_annotation(self, request, result):
        pass

    def handle_image_lock_success(self, request, result):

        locked_id = result["id"]
        print("Locked Image %d" % locked_id)
        App.get_running_app().register_image(locked_id)
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
        App.get_running_app().register_image(unlocked_id)
        self.window_cache[unlocked_id].image_opened = False
        self.right_control.image_queue.mark_item(
            unlocked_id, opened=False, locked=False)
        self.right_control.image_queue_control.btn_save.disabled = True

    def handle_image_request_success(self, request, result):
        img_bytes = utils.decode_image(result["image_data"])
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
    pen_size = ObjectProperty(None)
    alpha = ObjectProperty(None)
    class_color = ObjectProperty(None)
    class_name = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.draw_tool = None
        self.layer_stack = None

    def bind_draw_tool(self, draw_tool):
        self.draw_tool = draw_tool

    def bind_class_picker(self, class_picker):
        class_picker.fbind('current_color', self.setter('class_color'))
        class_picker.fbind('current_name', self.setter('class_name'))

    def bind_layer_stack(self, layer_stack):
        self.layer_stack = layer_stack

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
        self.layer_stack.set_alpha(alpha)

    def set_pencil_size(self, size):
        print("size: %s" % str(size))
        self.draw_tool.pen_size = size


class ClassPicker(GridLayout):
    eraser_enabled = BooleanProperty(False)

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
        self.eraser_enabled = False

    def enable_eraser(self, instance):
        print("ERASER")
        self.eraser_enabled = True
        if self.current_class:
            self.current_class.state = 'normal'
        self.current_class = instance
        self.current_class.state = 'down'


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

    current_selection = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.draw_tool = None
        self.layer_stack = None
        self.layer_item_dict = {}

    def bind_draw_tool(self, draw_tool):
        self.draw_tool = draw_tool

    def bind_layer_stack(self, layer_stack):
        self.layer_stack = layer_stack

    def get_items_at_pos(self, pos):
        selected_items = []
        for layer_item in self.layer_item_dict.values():
            layer = layer_item.layer
            bl = np.array(layer.bbox_bounds[:2])
            tr = bl + np.array(layer.bbox_bounds[2:])
            if np.all(np.logical_and(bl < pos, pos < tr)):
                selected_items.append(layer_item)
        return selected_items

    def add_layer_item(self, layer):
        # Add to Layer Stack
        stack_index = self.layer_stack.add_layer(layer)

        layer_name = "Layer %d" % stack_index
        while layer_name in self.layer_item_dict.keys():
            stack_index += 1
            layer_name = "Layer %d" % stack_index

        # Build Layer Item
        item = LayerViewItem(layer_name)
        item.bind_to_layer(layer)
        item.bind_to_layer_view(self)

        # Add to LayerView
        self.layer_item_dict[layer_name] = item
        self.layer_item_layout.add_widget(item)

        # Fit bounding box
        self.draw_tool.fit_bbox(layer)

        return layer_name

    def select_layer_item(self, name):
        if self.current_selection:
            prev_item = self.layer_item_dict[self.current_selection]
            prev_item.deselect()
        self.current_selection = name

        layer_item = self.layer_item_dict[name]
        layer = layer_item.layer

        # Draw Tool bind
        self.draw_tool.set_layer(layer)
        layer_item.select()

    def delete_layer_item(self, name):
        self.current_selection = None
        layer_item = self.layer_item_dict.pop(name, None)
        layer = layer_item.layer

        # Remove from LayerView
        self.layer_item_layout.remove_widget(layer_item)

        # Remove from LayerStack
        self.layer_stack.remove_layer(layer)

        # Unbind from Drawtool
        self.draw_tool.set_layer(None)

    def clear(self):
        self.current_selection = None
        self.layer_item_layout.clear_widgets()
        self.layer_item_dict.clear()
        self.layer_stack.clear()
        self.draw_tool.set_layer(None)


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

    def deselect(self):
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
        else:
            self.btn_bbox.background_color = self.button_up_color

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


class MaskInstruction(InstructionGroup):
    def __init__(self, pos, pen_size, negate=False, **kwargs):
        super().__init__(**kwargs)
        color = (1, 1, 1, 1)
        if negate:
            print("NEGATE!")
            color = (0, 0, 0, 1)
        self.color = Color(*color)
        self.add(self.color)
        self.circle = Ellipse(
            pos=(pos[0] -
                 pen_size / 2,
                 pos[1] -
                 pen_size / 2),
            size=(pen_size,
                  pen_size))
        self.add(self.circle)
        self.line = Line(
            points=pos,
            cap='round',
            joint='round',
            width=pen_size / 2)
        self.add(self.line)


class DrawTool(MouseDrawnTool):
    layer = ObjectProperty(None, allownone=True)
    pen_size = NumericProperty(10)
    layer_color = ObjectProperty((1, 1, 1, 1))
    class_name = StringProperty("")

    erase = BooleanProperty(False)

    # Stores binding id of last layer
    color_bind = None
    name_bind = None

    def __init__(self, **kwargs):
        self.layer_view = None

        self.keyboard_shortcuts = {}
        self.keycode_buffer = {}
        self._keyboard = Window.request_keyboard(lambda: None, self)
        self._consecutive_selects = 0

        self.mask_stack = []
        self.delete_stack = []

        self.bind_shortcuts()
        super().__init__(**kwargs)

    def bind_layer_view(self, layer_view):
        self.layer_view = layer_view

    def bind_class_picker(self, class_picker):
        class_picker.fbind('eraser_enabled', self.setter('erase'))

    def bind_shortcuts(self):
        self.keyboard_shortcuts[("lctrl", "z")] = self.undo
        self.keyboard_shortcuts[("lctrl", "y")] = self.redo

    def bind_keyboard(self):
        self._keyboard.bind(on_key_down=self.on_key_down)
        self._keyboard.bind(on_key_up=self.on_key_up)

    def unbind_keyboard(self):
        self._keyboard.unbind(on_key_down=self.on_key_down)
        self._keyboard.unbind(on_key_up=self.on_key_up)

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in self.keycode_buffer:
            return
        print("DOWN: %s" % (str(keycode[1])))
        self.keycode_buffer[keycode[1]] = keycode[0]

    def on_key_up(self, keyboard, keycode):
        print("UP: %s" % (str(keycode[1])))

        for shortcut in self.keyboard_shortcuts.keys():
            if keycode[1] in shortcut and set(shortcut).issubset(self.keycode_buffer):
                self.keyboard_shortcuts[shortcut]()

        self.keycode_buffer.pop(keycode[1])

    def undo(self):
        if not self.mask_stack:
            return
        mask = self.mask_stack.pop()
        self.delete_stack.append(mask)
        self.layer.remove_instruction(mask)
        self.fit_bbox()

    def redo(self):
        if not self.delete_stack:
            return
        mask = self.delete_stack.pop()
        self.mask_stack.append(mask)
        self.layer.add_instruction(mask)
        self.fit_bbox()

    def add_action(self, instruction_group):
        self.layer.add_instruction(instruction_group)
        self.mask_stack.append(instruction_group)
        self.delete_stack.clear()

    def set_layer(self, layer):
        self.layer = layer

        if self.color_bind:
            self.unbind_uid('layer_color', self.color_bind)

        if self.name_bind:
            self.unbind_uid('class_name', self.name_bind)

        if not layer:
            return

        self.color_bind = self.fbind(
            'layer_color', self.layer.setter('mask_color'))
        self.layer_color = self.layer.mask_color

        self.name_bind = self.fbind(
            'class_name', self.layer.setter('class_name'))
        self.class_name = self.layer.class_name

    def on_touch_down_hook(self, touch):
        if not self.layer:
            return
        if 'lctrl' in self.keycode_buffer:
            select_items = self.layer_view.get_items_at_pos(touch.pos)
            if not select_items:
                return
            item = select_items[self._consecutive_selects % len(select_items)]
            self.layer_view.select_layer_item(item.layer_name)
            self._consecutive_selects += 1
            return

        if 'shift' in self.keycode_buffer:
            self.flood_fill(touch.pos)
            return

        pos = np.round(touch.pos).astype(int)

        self._consecutive_selects = 0

        mask = MaskInstruction(
            pos=list(pos),
            pen_size=self.pen_size,
            negate=self.erase)

        self.add_action(mask)

    def on_touch_move_hook(self, touch):
        if not self.layer:
            return

        pos = np.round(touch.pos).astype(int)

        mask = self.mask_stack[-1]
        mask.line.points += list(pos)

    def on_touch_up_hook(self, touch):
        if not self.layer:
            return

        self.fit_bbox()

    def fit_bbox(self, layer=None):
        if layer is None:
            layer = self.layer

        fbo = layer.get_fbo()

        if fbo is None:
            return

        fbo.draw()
        mat_gray = np.sum(
            utils.texture2mat(fbo.texture),
            axis=2)

        col_sum = np.sum(mat_gray, axis=0)
        x1 = 0
        x2 = len(col_sum)
        for x in col_sum:
            if x > 0:
                break
            x1 += 1

        for x in reversed(col_sum):
            if x > 0:
                break
            x2 -= 1

        row_sum = np.sum(mat_gray, axis=1)
        y1 = 0
        y2 = len(row_sum)
        for x in reversed(row_sum):
            if x > 0:
                break
            y1 += 1

        for x in row_sum:
            if x > 0:
                break
            y2 -= 1

        bounds = [x1, y1, x2 - x1, y2 - y1]
        if bounds[2] <= 0 or bounds[3] <= 0:
            bounds = [0, 0, 0, 0]

        layer.bbox_bounds = bounds

    def flood_fill(self, pos):
        print("FLOOD")

        fbo = self.layer.get_fbo()
        if fbo is None:
            return

        if np.sum(fbo.get_pixel_color(*pos)) > 0:
            return

        bounds = self.layer.bbox_bounds
        valid = bounds[0] < pos[0] < bounds[0] + bounds[2] and bounds[1] < pos[1] < bounds[1] + bounds[3]
        if not valid:
            return

        region = fbo.texture.get_region(*self.layer.bbox_bounds)
        relative_pos = np.array(pos) - np.array(self.layer.bbox_bounds[:2])

        cv2_pos = np.round(relative_pos).astype(int)

        (width, height) = region.size

        mat = utils.texture2mat(region)
        mat_copy = mat.copy()
        mask = np.zeros((height + 2, width + 2), dtype=np.uint8)
        cv2.floodFill(mat_copy, mask, tuple(cv2_pos), (255, 255, 255))

        mat = np.clip(mat_copy - mat, 0, 255)
        mat = cv2.flip(mat, 0)

        # Convert to instruction
        g = InstructionGroup()
        g.add(Color(1, 1, 1, 1))
        g.add(Rectangle(size=(width, height),
                        pos=tuple(self.layer.bbox_bounds[:2]),
                        texture=utils.mat2texture(mat)))
        self.add_action(g)


class LayerStack(FloatLayout):
    layer_view = ObjectProperty(None)
    layer_list = ObjectProperty([])
    current_layer = NumericProperty(-1)
    layer_sizes = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def set_alpha(self, alpha):
        for layer in self.layer_list:
            layer.mask_color = layer.mask_color[:3] + (alpha,)

    def add_layer(self, layer):
        self.add_widget(layer)
        self.layer_list.append(layer)
        return len(self.layer_list) - 1

    def remove_layer(self, layer):
        self.remove_widget(layer)
        self.layer_list.remove(layer)

    def clear(self):
        self.layer_list = []
        self.clear_widgets()


class DrawableLayer(FloatLayout):
    fbo = ObjectProperty(None)
    class_name = StringProperty("")

    mask_color = ObjectProperty((1, 1, 1, 1))
    mask_visible = BooleanProperty(True)

    bbox_layer = ObjectProperty(None)
    bbox_visible = BooleanProperty(True)
    bbox_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.BBOX_UNSELECT))
    bbox_thickness = NumericProperty(1)

    bbox_bounds = ObjectProperty([0, 0, 0, 0])
    """ A bounding rectangle represented in the form (x, y, width, height)"""

    def __init__(
            self,
            size,
            class_name="",
            mask_color=(1, 1, 1, 1),
            texture=None,
            bbox=None,
            **kwargs):
        super().__init__(**kwargs)
        self.size = size
        self.class_name = class_name
        self.mask_color = mask_color
        self.texture = texture

        if bbox is not None:
            self.bbox_bounds = [
                bbox[0],
                bbox[1],
                bbox[2] - bbox[0],
                bbox[3] - bbox[1]]

        self.layer_view = None
        Clock.schedule_once(lambda dt: self.late_init())

    def late_init(self):
        self.paint_window.refresh()
        self.load_texture(self.texture)

    def load_texture(self, texture):
        if self.texture:
            g = InstructionGroup()
            g.add(Color(1, 1, 1, 1))
            g.add(Rectangle(size=self.get_fbo().size, texture=texture))
            self.paint_window.add_instruction(g)

    def get_fbo(self):
        return self.paint_window.fbo

    def add_instruction(self, instruction):
        self.paint_window.add_instruction(instruction)

    def remove_instruction(self, instruction):
        self.paint_window.remove_instruction(instruction)

    def toggle_mask(self):
        self.mask_visible = not self.mask_visible
        self.paint_window.mask_layer.canvas.opacity = int(self.mask_visible)

    def toggle_bbox(self):
        self.bbox_visible = not self.bbox_visible
        self.bbox_layer.canvas.opacity = int(self.bbox_visible)


class ImageCanvas(BoxLayout):
    scatter = ObjectProperty(None)
    image = ObjectProperty(None)
    image_id = NumericProperty(-1)
    draw_tool = ObjectProperty(None)
    layer_stack = ObjectProperty(None)

    max_scale = NumericProperty(10.0)
    min_scale = NumericProperty(0.5)
    step_scale = NumericProperty(0.1)

    def on_touch_down(self, touch):
        if 'lctrl' in self.draw_tool.keycode_buffer and touch.is_mouse_scrolling:
            if touch.button == 'scrolldown':
                self.zoom(1.0 + self.step_scale)
            elif touch.button == 'scrollup':
                self.zoom(1.0 - self.step_scale)
        super(ImageCanvas, self).on_touch_down(touch)

    def zoom(self, scale):
        print("pos: %s size: %s" % (str(self.scatter.pos),
                                    str(self.scatter.size)))
        self.scatter.scale = np.clip(self.scatter.scale * scale,
                                     self.min_scale,
                                     self.max_scale)
        self.scatter.pos = self.pos

    def load_image(self, texture, image_id):
        self.image_id = image_id
        self.image.texture = texture
        self.image.size = texture.size

    def refresh_image(self):
        print("refreshing")
        window_state = App.get_running_app().root.current_screen.current_state
        self.image.texture = window_state.image_texture
        self.image.size = window_state.image_texture.size

    def resize_image(self):
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
        for row in result["images"]:
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
