import random
import string

import cv2
from skimage.draw import line, circle
from skimage.segmentation import flood_fill
import numba
import numpy as np
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from numba import jit
from kivy.core.window import Window

from client.screens.common import MouseDrawnTool
from kivy.graphics.texture import Texture
import time


class PaintApp(App):
    def build(self):
        box = FloatLayout()
        image = np.zeros(shape=(3000, 2000, 3), dtype=np.uint8)
        image[:] = (255, 0, 0)
        pw = PaintWindow(image)
        box.add_widget(pw)
        pw.add_layer('test', (0, 0, 255))
        drawtool = DrawTool(pw)
        box.add_widget(drawtool)
        return box


class KeyboardManager:
    def __init__(self, keyboard):
        self._keyboard_shortcuts = {}
        self.keycode_buffer = {}
        self._keyboard = keyboard

    def activate(self):
        print("Binding keyboard")
        self._keyboard.bind(on_key_down=self.on_key_down)
        self._keyboard.bind(on_key_up=self.on_key_up)

    def deactivate(self):
        self._keyboard.unbind(on_key_down=self.on_key_down)
        self._keyboard.unbind(on_key_up=self.on_key_up)

    def create_shortcut(self, shortcut, func):
        if not isinstance(shortcut, tuple):
            shortcut = tuple(shortcut)
        self._keyboard_shortcuts[shortcut] = func

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in self.keycode_buffer:
            return
        print("DOWN: %s" % (str(keycode[1])))
        self.keycode_buffer[keycode[1]] = keycode[0]

    def on_key_up(self, keyboard, keycode):
        print("UP: %s" % (str(keycode[1])))

        for shortcut in self._keyboard_shortcuts.keys():
            if keycode[1] in shortcut and set(
                    shortcut).issubset(self.keycode_buffer):
                self._keyboard_shortcuts[shortcut]()

        self.keycode_buffer.pop(keycode[1])


class DrawTool(MouseDrawnTool):
    def __init__(self, paint_window, **kwargs):
        super().__init__(**kwargs)
        self.paint_window = paint_window
        self.size = self.paint_window.size
        self.keyboard = KeyboardManager(Window.request_keyboard(lambda: None, self))
        self.keyboard.create_shortcut(("lctrl", "z"), self.paint_window.undo)
        self.keyboard.create_shortcut(("lctrl", "y"), self.paint_window.redo)
        self.keyboard.activate()

        def random_name(N):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

        def random_color():
            return list(np.random.choice(range(256), size=3))

        def add_random_layer():
            self.paint_window.add_layer(random_name(10), random_color)

        self.keyboard.create_shortcut("spacebar", add_random_layer)

    def on_touch_down_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        self.paint_window.draw_line(pos, 10)
        self.paint_window.refresh()

    def on_touch_move_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        self.paint_window.draw_line(pos, 10)
        self.paint_window.refresh()

    def on_touch_up_hook(self, touch):
        self.paint_window.checkpoint()


class PaintWindow(Widget):
    image = ObjectProperty(None)
    box_color = [255, 0, 255]
    box_highlight = [0, 255, 0]

    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        self._layer_manager = LayerManager(image)
        self._action_manager = ActionManager(self._layer_manager)
        self._box_manager = BoxManager(image.shape, self.box_color, self.box_highlight)
        size = image.shape[:2]
        self.image.texture = Texture.create(size=size, colorfmt='bgr', bufferfmt='ubyte')
        self.size_hint = (None, None)
        self.size = size
        self.refresh()

    def undo(self):
        self._action_manager.undo()
        self.refresh()

    def redo(self):
        self._action_manager.redo()
        self.refresh()

    def draw_line(self, point, pen_size):
        self._action_manager.draw_line(point, pen_size)

    def fill(self, point):
        self._action_manager.fill(point)

    def checkpoint(self):
        self._action_manager.checkpoint()

    def refresh(self):
        t0 = time.time()
        box_layer = self._box_manager.get_box_layer()
        t1 = time.time()
        stack = self._layer_manager.get_stack()
        t2 = time.time()
        buffer = collapse_layers(stack)
        t3 = time.time()
        self.image.texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
        self.image.canvas.ask_update()
        t4 = time.time()

        print("[FPS: %.2f] | Box: %f\tStack: %f\tCollapse: %f\tCanvas: %f" % (1/(t4-t0),t1-t0, t2-t1, t3-t2, t4-t3))

    def add_layer(self, name, color):
        self._layer_manager.add_layer(name, color)
        self._layer_manager.select_layer(name)
        self.checkpoint()


class ActionManager:
    def __init__(self, layer_manager):
        self._layer_manager = layer_manager
        self._current_line = []
        self._layer_history = []
        self._history_index = -1

    def undo(self):
        if not self._layer_history or self._history_index <= 0:
            return

        layer = self._layer_manager.get_selected_layer()
        self._history_index -= 1
        try:
            layer.mat = self._layer_history[self._history_index].copy()
        except IndexError:
            layer.mat[:] = 0

    def redo(self):
        if not self._layer_history or self._history_index >= len(self._layer_history) - 1:
            return

        layer = self._layer_manager.get_selected_layer()
        self._history_index += 1
        try:
            layer.mat = self._layer_history[self._history_index].copy()
        except IndexError:
            print("ERROR with redo")

    def checkpoint(self):
        layer = self._layer_manager.get_selected_layer()
        self._current_line = None
        self._history_index += 1
        self._layer_history = self._layer_history[:self._history_index]
        self._layer_history.append(layer.mat.copy())

    def draw_line(self, point, pen_size):
        if self._current_line is None:
            self._current_line = tuple(point)

        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        self._draw_line_thick(layer.mat, self._current_line, tuple(point), layer.color, pen_size)
        self._current_line = tuple(point)

    def fill(self, point):
        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        if np.sum(layer.mat[point]) > 0:
            return

        mask = np.zeros((layer.mat.shape[1] + 2, layer.mat.shape[0] + 2), dtype=np.uint8)
        cv2.floodFill(layer.mat, mask, point, layer.color)

    def _draw_line_thick(self, mat, p0, p1, color, thickness):
        thickness = np.floor(thickness / 2).astype(int)
        mat = mat.swapaxes(0, 1)
        mat[circle(p0[0], p0[1], thickness)] = color
        mat[circle(p1[0], p1[1], thickness)] = color

        d = np.array((p1[0] - p0[0], p1[1] - p0[1]))
        if np.all(np.abs(d) <= 5):
            return
        else:
            mag = np.sqrt(np.dot(d, d))
            step_size = thickness / mag
            for i in np.arange(0.0, 1.0, step_size):
                c = np.round(p0 + i * d)
                mat[circle(c[0], c[1], thickness)] = color



class Layer:
    def __init__(self, name, mat, color, idx):
        self.name = name
        self.mat = mat
        self.color = color
        self.idx = idx


class LayerManager:
    initial_stack_capacity = 100
    stack_growth_factor = 4

    def __init__(self, image):
        self._base_image = image.swapaxes(0, 1)
        self._selected_layer = None

        self._layer_dict = {}
        self._layer_capacity = self.initial_stack_capacity
        self._layer_stack = np.empty(shape=(np.product(image.shape), self._layer_capacity), dtype=np.uint8)
        self._layer_visibility = np.zeros(shape=(self._layer_capacity,), dtype=bool)
        self._layer_index = -1

        self._add_layer(self._base_image)

    def get_base_image(self):
        return self._base_image

    def add_layer(self, name, color):
        # Resize arraylists
        if self._layer_index == self._layer_capacity:
            self._resize()

        self._add_layer()
        mat_view = self._layer_stack[:, self._layer_index].reshape(self.get_base_image().shape)
        layer = Layer(name, mat_view, color, self._layer_index)
        self._layer_dict[layer.name] = layer

    def _add_layer(self, mat=None):
        self._layer_index += 1
        if mat is None:
            self._layer_stack[:, self._layer_index] = 0
        else:
            self._layer_stack[:, self._layer_index] = mat.ravel()
        self._layer_visibility[self._layer_index] = True

    def _resize(self):
        self._layer_capacity = self._layer_capacity * self.stack_growth_factor

        new_stack = np.empty(shape=(np.product(self.get_base_image().shape), self._layer_capacity), dtype=np.uint8)
        new_stack[:, :self._layer_index] = self._layer_stack
        new_visibility = np.zeros(shape=(self._layer_capacity,), dtype=bool)
        new_visibility[:self._layer_index] = self._layer_visibility

        self._layer_stack = new_stack
        self._layer_visibility = new_visibility

    def select_layer(self, name):
        self._selected_layer = self._layer_dict[name]

    def get_selected_layer(self):
        return self._selected_layer

    def set_visible(self, visible=True):
        self._layer_visibility[self.get_selected_layer().idx] = visible

    def get_stack(self):
        return self._layer_stack[:, :self._layer_index + 1]

class Box:
    def __init__(self, bounds, color, visible=True):
        """ Bounding box in the form (x1, y1, x2, y2)"""
        self.bounds = bounds
        self.color = color
        self.visible = visible


class BoxManager:
    box_thickness = 2

    def __init__(self, image_shape, box_color, box_select_color):
        self.box_color = box_color
        self.box_select_color = box_select_color
        self.image_shape = image_shape

        self._box_dict = {}
        self._box_layer_cache = None

    def update_box(self, layer):
        bounds = BoxManager._fit_box(layer.mat)
        self._box_dict[layer.name] = Box(bounds, self.box_color)
        self._box_layer_cache = None

    def set_visible(self, name, visible):
        self._box_dict[name].visible = visible
        self._box_layer_cache = None

    def set_highlight(self, name, highlight):
        self._box_dict[name].color = self.box_select_color if highlight else self.box_color
        self._box_layer_cache = None

    def get_box_layer(self):
        if self._box_layer_cache is not None:
            return self._box_layer_cache

        box_layer = np.zeros(shape=self.image_shape, dtype=np.uint8)

        for box in self._box_dict.values():
            cv2.rectangle(box_layer, box.bounds[:2], box.bounds[2:], box.color, self.box_thickness)

        self._box_layer_cache = box_layer
        return self._box_layer_cache

    @staticmethod
    def _fit_box(img):
        mat_gray = np.sum(img, axis=2)

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

        bounds = [x1, y1, x2, y2]
        return bounds


@jit(nopython=True, parallel=True)
def collapse_layers(stack):
    width = stack.shape[1]
    height = stack.shape[0]
    out = np.zeros(height, dtype=np.uint8)
    for i in numba.prange(height):
        for j in range(width):
            reverse_j = width - 1 - j
            if stack[i, reverse_j] > 0:
                out[i] = stack[i, reverse_j]
                break
    return out


if __name__ == '__main__':
    PaintApp().run()
