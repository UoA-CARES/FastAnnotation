from threading import Lock

import cv2
import kivy.utils
from kivy.app import App
from kivy.clock import Clock
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, InstructionGroup, Line
from kivy.properties import BooleanProperty
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.controller.instance_annotator_controller import InstanceAnnotatorController
from client.model.instance_annotator_model import InstanceAnnotatorModel
from client.screens.common import *

import random

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'test_annotator_screen.kv'))


def background(f):
    def aux(*xs, **kws):
        app = App.get_running_app()
        future = app.thread_pool.submit(f, *xs, **kws)
        future.add_done_callback(app.alert_user)
        return future
    return aux


class InstanceAnnotatorScreen(Screen):
    left_control = ObjectProperty(None)
    right_control = ObjectProperty(None)
    image_canvas = ObjectProperty(None)

    _update_lock = Lock()
    _update_flag = False

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.model = InstanceAnnotatorModel()
        self.controller = InstanceAnnotatorController(self.model)

    def queue_update(self):
        with self._update_lock:
            if not self._update_flag:
                self._update_flag = True
                self._update()

    @mainthread
    def _update(self):
        # TODO: Implement a diff system which only updates changed sections of
        # the model

        current_iid = self.model.tool.get_current_image_id()
        current_label_name = self.model.tool.get_current_label_name()
        current_label = self.model.labels.get(current_label_name)
        current_layer = self.model.tool.get_current_layer_name()
        image = self.model.images.get(current_iid)

        # Update ToolSelect
        print("Updating Tool Select")
        self.left_control.tool_select.alpha.value = self.model.tool.get_alpha()
        self.left_control.tool_select.pen_size.value = self.model.tool.get_pen_size()

        # Update Class Picker
        print("Updating Class Picker")
        label_names = self.model.labels.keys()
        self.left_control.class_picker.clear()
        for name in label_names:
            label = self.model.labels.get(name)
            self.left_control.class_picker.add_label(label.name, label.color)

        print("\tSelecting Label: %s" % current_label_name)
        self.left_control.class_picker.select(current_label_name)

        # Update Layer View
        print("Updating Layer View")
        if image is not None and image.annotations is not None:
            self.left_control.layer_view.clear()
            for annotation in image.annotations.values():
                self.left_control.layer_view.add_layer_item(annotation.annotation_name)

        self.left_control.layer_view.select(
            self.model.tool.get_current_layer_name())

        # Update ImageCanvas
        print("Updating Image Canvas")
        self.image_canvas.load_pen_size(self.model.tool.get_pen_size())
        self.image_canvas.load_global_alpha(self.model.tool.get_alpha())
        self.image_canvas.load_eraser_state(self.model.tool.get_eraser())

        self.image_canvas.load_current_label(current_label)

        # TODO: Handle unsaved progress
        if image is None or not image.unsaved:
            iid = self.model.tool.get_current_image_id()
            if iid > 0:
                image = self.model.images.get(iid)
                self.image_canvas.load_image(image)
                self.image_canvas.load_annotations(image.annotations, overwrite=True)
        else:
            self.image_canvas.load_annotations(image.annotations)

        self.image_canvas.load_current_layer(current_layer)

        # Update ImageQueue
        print("Updating Image Queue")
        self.right_control.load_image_queue()

        # Reset update flag
        with self._update_lock:
            self._update_flag = False

    def on_enter(self, *args):
        self.fetch_image_metas()
        self.fetch_class_labels()
        Window.bind(on_resize=self.auto_resize)
        self.image_canvas.draw_tool.bind_keyboard()

    def on_leave(self, *args):
        self.image_canvas.draw_tool.unbind_keyboard()

    @mainthread
    def auto_resize(self, *args):
        image = self.model.images.get(self.model.tool.get_current_image_id())
        self.image_canvas.load_image(image)

    @background
    def load_next(self):
        image_ids = self.model.images.keys()
        current_id = self.model.tool.get_current_image_id()
        idx = 0
        if current_id > 0:
            idx = image_ids.index(current_id)
            idx += 1

        while self.model.images.get(image_ids[idx]).is_locked:
            idx += 1
        next_id = image_ids[idx]
        self.controller.open_image(next_id)
        self.queue_update()

    @background
    def load_image(self, id):
        self.controller.open_image(id)
        self.queue_update()

    @background
    def save_image(self):
        self.controller.save_image(self.image_canvas)
        self.queue_update()

    @background
    def add_layer(self):
        self.controller.add_blank_layer(self.model.tool.get_current_image_id())
        self.queue_update()

    @background
    def fetch_image_metas(self):
        filter_details = {
            "order_by": {
                "key": "name",
                "ascending": True
            }
        }
        self.controller.fetch_image_metas(self.app.current_project_id, filter_details)
        self.queue_update()

    @background
    def fetch_class_labels(self):
        self.controller.fetch_class_labels(self.app.current_project_id)
        if self.model.tool.get_current_label_name() is "":
            self.model.tool.set_current_label_name(self.model.labels.keys()[0])
        self.queue_update()


class LeftControlColumn(BoxLayout):
    tool_select = ObjectProperty(None)
    class_picker = ObjectProperty(None)
    layer_view = ObjectProperty(None)


class ToolSelect(GridLayout):
    pen_size = ObjectProperty(None)
    alpha = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def set_alpha(self, alpha):
        print("Alpha: %s" % str(alpha))
        self.app.root.current_screen.controller.update_tool_state(alpha=alpha)
        self.app.root.current_screen.queue_update()

    def set_pencil_size(self, size):
        print("Pen Size: %s" % str(size))
        self.app.root.current_screen.controller.update_tool_state(
            pen_size=size)
        self.app.root.current_screen.queue_update()


class ClassPicker(GridLayout):
    eraser_enabled = BooleanProperty(False)
    current_label = ObjectProperty(None, allownone=True)
    grid = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.label_dict = {}

    def on_eraser_enabled(self, instance, value):
        print("Eraser: %s" % str(value))
        self.app.root.current_screen.controller.update_tool_state(eraser=value)

    def on_current_label(self, instance, value):
        class_name = ""
        if value is not None:
            class_name = value.class_name

        print("Label: %s" % str(class_name))
        self.app.root.current_screen.controller.update_tool_state(
            current_label=class_name)

        if class_name not in ("", "eraser"):
            self.app.root.current_screen.controller.update_annotation(label_name=class_name)
        self.app.root.current_screen.queue_update()

    def clear(self):
        self.grid.clear_widgets()
        self.label_dict.clear()
        self.add_eraser()

    def select(self, name):
        label = self.label_dict.get(name, None)
        if label is None:
            return
        self._change_label(label)

    def add_eraser(self):
        def eraser_enable():
            self.eraser_enabled = True
            item.enable()

        def eraser_disable():
            self.eraser_enabled = False
            item.disable()

        name = "eraser"
        item = self._make_label(name, [0.2, 0.2, 0.2, 1.0])
        item.enable_cb = eraser_enable
        item.disable_cb = eraser_disable
        self.grid.add_widget(item)
        self.label_dict[name] = item

    def add_label(self, name, color):
        item = self._make_label(name, color)
        self.grid.add_widget(item)
        self.label_dict[name] = item

    def _make_label(self, name, color):
        item = ClassPickerItem()
        item.class_name = name
        item.class_color = color
        item.enable_cb = item.enable
        item.disable_cb = item.disable
        item.bind(on_release=lambda *args: self._change_label(item))
        return item

    def _change_label(self, instance):
        self.eraser_enabled = False
        if self.current_label:
            self.current_label.disable_cb()
        self.current_label = instance
        self.current_label.enable_cb()
        self.app.root.current_screen.queue_update()


class ClassPickerItem(Button):
    class_color = ObjectProperty((0, 0, 0, 1))
    class_name = StringProperty("")
    class_id = NumericProperty(-1)

    enable_cb = ObjectProperty(None)
    disable_cb = ObjectProperty(None)

    def enable(self):
        self.state = 'down'

    def disable(self):
        self.state = 'normal'


class LayerView(GridLayout):
    layer_item_layout = ObjectProperty(None)

    current_selection = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.layers = {}

    def on_current_selection(self, instance, value):
        layer_name = ""
        if value is None:
            print("Setting LayerView Layer to None")
        else:
            layer_name = value.layer_name
        print("Layer: %s" % str(value))
        self.app.root.current_screen.controller.update_tool_state(
            current_layer=layer_name)

    def clear(self):
        self.layer_item_layout.clear_widgets()
        self.layers.clear()

    def select(self, layer_name):
        item = self.layers.get(layer_name, None)
        if item is None:
            return
        self._change_layer(item)

    def add_layer_item(self, name):
        item = LayerViewItem(name)
        item.layer_select_cb = lambda: self._change_layer(item)
        item.layer_delete_cb = lambda: self._delete_layer(item)
        self.layer_item_layout.add_widget(item)
        self.layers[name] = item

    def _change_layer(self, instance):
        if self.current_selection:
            self.current_selection.deselect()
        self.current_selection = instance
        self.current_selection.select()
        self.app.root.current_screen.queue_update()

    def _delete_layer(self, instance):
        if instance is self.current_selection:
            self.current_selection = None
        self.layer_item_layout.remove_widget(instance)
        iid = self.app.root.current_screen.model.tool.get_current_image_id()
        self.app.root.current_screen.controller.delete_layer(iid, instance.layer_name)
        self.app.root.current_screen.queue_update()


class LayerViewItem(RelativeLayout):
    layer_name = StringProperty('')
    mask_enabled = BooleanProperty(True)
    bbox_enabled = BooleanProperty(True)

    layer_select_cb = ObjectProperty(None)
    layer_delete_cb = ObjectProperty(None)

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
        self.layer_name = name

    def select(self):
        self.btn_base.background_color = self.button_down_color
        self.btn_base.state = 'down'

    def deselect(self):
        self.btn_base.background_color = self.button_up_color
        self.btn_base.state = 'normal'

    def toggle_mask(self):
        self.mask_enabled = not self.mask_enabled
        self.btn_mask.background_color = self.button_down_color if self.mask_enabled else self.button_up_color
        self.btn_mask.state = 'down' if self.mask_enabled else 'normal'

    def toggle_bbox(self):
        self.bbox_enabled = not self.bbox_enabled
        self.btn_bbox.background_color = self.button_down_color if self.mask_enabled else self.button_up_color
        self.btn_bbox.state = 'down' if self.mask_enabled else 'normal'


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

    erase = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        self.keyboard_shortcuts = {}
        self.keycode_buffer = {}
        self._keyboard = Window.request_keyboard(lambda: None, self)
        self._consecutive_selects = 0

        self.mask_stack = []
        self.delete_stack = []

        self.bind_shortcuts()
        super().__init__(**kwargs)

    def bind_shortcuts(self):
        self.keyboard_shortcuts[("lctrl", "z")] = self.undo
        self.keyboard_shortcuts[("lctrl", "y")] = self.redo

    def bind_keyboard(self):
        print("Binding keyboard")
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
            if keycode[1] in shortcut and set(
                    shortcut).issubset(self.keycode_buffer):
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

        iid = self.app.root.current_screen.model.tool.get_current_image_id()
        self.app.root.current_screen.controller.update_image_meta(iid, unsaved=True)

    def set_layer(self, layer):
        print("Setting DrawTool Layer: %s" % layer.layer_name)
        self.layer = layer

    def on_touch_down_hook(self, touch):
        if not self.layer:
            return
        if 'lctrl' in self.keycode_buffer:
            image_id = self.app.root.current_screen.model.tool.get_current_image_id()
            image = self.app.root.current_screen.model.images.get(image_id)
            select_items = image.detect_collisions(touch.pos)
            if not select_items:
                return
            item = select_items[self._consecutive_selects % len(select_items)]

            self.app.root.current_screen.controller.update_tool_state(
                current_layer=item.annotation_name)
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
        image_id = self.app.root.current_screen.model.tool.get_current_image_id()
        layer_name = self.layer.layer_name
        self.app.root.current_screen.controller.update_annotation(
            image_id, layer_name, bbox=self.layer.bbox_bounds)

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
        valid = bounds[0] < pos[0] < bounds[0] + \
            bounds[2] and bounds[1] < pos[1] < bounds[1] + bounds[3]
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
    layer_sizes = ObjectProperty(None)

    alpha = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()
        self.layer_dict = {}

    def set_alpha(self, alpha):
        if np.isclose(alpha, self.alpha):
            return
        self.alpha = alpha
        for layer in self.layer_dict.values():
            print("Layer Color: %s" % str(layer.mask_color))
            new_color = layer.get_mask_color()
            new_color[3] = float(alpha)
            layer.set_mask_color(new_color)

    def add_layer(self, layer):
        print("Adding Layer to Stack")
        new_color = layer.get_mask_color()
        new_color[3] = float(self.alpha)
        layer.set_mask_color(new_color)

        self.add_widget(layer)
        self.layer_dict[layer.layer_name] = layer

    def get_layer(self, name):
        return self.layer_dict.get(name, None)

    def remove_layer(self, layer):
        self.remove_widget(layer)
        self.layer_dict.pop(layer.layer_name, None)

    def clear(self):
        print("Clearing Stack")
        self.layer_dict = {}
        self.clear_widgets()


class DrawableLayer(FloatLayout):
    layer_name = StringProperty("")
    class_name = StringProperty("")

    """ A bounding rectangle represented in the form (x, y, width, height)"""
    bbox_bounds = ObjectProperty([0, 0, 0, 0])

    bbox_visible = BooleanProperty(True)
    mask_visible = BooleanProperty(True)

    # fbo = ObjectProperty(None)
    bbox_layer = ObjectProperty(None)
    bbox_color = ObjectProperty(
        kivy.utils.get_color_from_hex(
            ClientConfig.BBOX_UNSELECT))
    bbox_thickness = NumericProperty(1)

    def __init__(self,
                 layer_name,
                 size,
                 class_name="",
                 mask_color=(1, 1, 1, 1),
                 texture=None,
                 bbox=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.layer_name = layer_name
        self.size = size
        self.class_name = class_name
        self.texture = texture

        self._mask_color = mask_color

        if bbox is not None:
            self.bbox_bounds = bbox

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

    def set_mask_color(self, color):
        print("New Mask Color: %s" % color)
        self._mask_color = color
        self.paint_window.update_color(color)

    def get_mask_color(self):
        return self._mask_color

    def update_label(self, label):
        self.class_name = label.name
        new_color = label.color[:3] + [self.get_mask_color()[3],]
        self.set_mask_color(new_color)

    def update_bbox(self, bbox):
        self.bbox_bounds = bbox

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
    unsaved = BooleanProperty(False)
    draw_tool = ObjectProperty(None)
    layer_stack = ObjectProperty(None)

    max_scale = NumericProperty(10.0)
    min_scale = NumericProperty(0.5)
    step_scale = NumericProperty(0.1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def load_save_status(self, unsaved):
        self.unsaved = unsaved

    def load_pen_size(self, size):
        self.draw_tool.pen_size = size

    def load_global_alpha(self, alpha):
        self.layer_stack.set_alpha(alpha)

    def load_eraser_state(self, eraser):
        self.draw_tool.erase = eraser

    def load_current_label(self, label):
        if label is None or self.draw_tool.layer is None:
            return
        new_color = self.draw_tool.layer.get_mask_color()
        new_color[:3] = label.color[:3]
        self.draw_tool.layer.set_mask_color(new_color)

    def load_current_layer(self, layer_name):
        print("Loading Current Layer: %s" % layer_name)
        layer = self.layer_stack.get_layer(layer_name)
        if layer is None:
            return
        self.draw_tool.set_layer(layer)

    @mainthread
    def load_image(self, image_state):
        if image_state is None:
            return
        print("Loading Image")
        self.image_id = image_state.id
        texture = utils.mat2texture(image_state.image)
        self.image.texture = texture
        self.image.size = image_state.shape[1::-1]

    def load_annotations(self, annotations, overwrite=False):
        print("Loading Annotations")
        if overwrite:
            self.layer_stack.clear()
        for annotation in annotations.values():
            layer = self.layer_stack.get_layer(annotation.annotation_name)
            label = self.app.root.current_screen.model.labels.get(annotation.class_name)
            if overwrite or layer is None:
                layer = DrawableLayer(
                    layer_name=annotation.annotation_name,
                    class_name=label.name,
                    size=annotation.mask.shape[1::-1],
                    mask_color=label.color,
                    texture=utils.mat2texture(annotation.mask),
                    bbox=annotation.bbox)
                self.layer_stack.add_layer(layer)
            else:
                layer.update_label(label)
                layer.update_bbox(annotation.bbox)

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


class RightControlColumn(BoxLayout):
    image_queue = ObjectProperty(None)
    image_queue_control = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def load_image_queue(self):
        self.image_queue.clear()
        image_ids = self.app.root.current_screen.model.images.keys()
        for iid in image_ids:
            image = self.app.root.current_screen.model.images.get(iid)
            self.image_queue.add_item(image.name,
                                      iid,
                                      locked=image.is_locked,
                                      opened=image.is_open)


class ImageQueueControl(GridLayout):
    btn_save = ObjectProperty(None)


class ImageQueue(GridLayout):
    queue = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.queue_item_dict = {}

    def clear(self):
        self.queue.clear_widgets()
        self.queue_item_dict.clear()

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
