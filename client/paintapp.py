import random
import string

import cv2
from skimage.draw import line, disk, rectangle_perimeter
from skimage.segmentation import flood
import numba
from numba import vectorize, uint8, boolean, int32
import numpy as np
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from numba import jit
from kivy.core.window import Window

from skimage.color import rgb2gray

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

    def is_key_down(self, keycode):
        return keycode in self.keycode_buffer

    def create_shortcut(self, shortcut, func):
        if not isinstance(shortcut, tuple):
            shortcut = (shortcut,)
        self._keyboard_shortcuts[shortcut] = func

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in self.keycode_buffer:
            return
        self.keycode_buffer[keycode[1]] = keycode[0]

    def on_key_up(self, keyboard, keycode):
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
        self.keyboard.create_shortcut("q", lambda: self.paint_window.set_visible(True))
        self.keyboard.create_shortcut("w", lambda: self.paint_window.set_visible(False))
        self.keyboard.activate()

        def random_name(N):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

        def random_color():
            return list(np.random.choice(range(256), size=3))

        def add_random_layer():
            self.paint_window.add_layer(random_name(10), random_color())

        self.keyboard.create_shortcut("spacebar", add_random_layer)

    def on_touch_down_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        if self.keyboard.is_key_down("shift"):
            self.paint_window.fill(pos)
        else:
            self.paint_window.draw_line(pos, 10)
        self.paint_window.refresh()

    def on_touch_move_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        self.paint_window.draw_line(pos, 10)
        self.paint_window.refresh()

    def on_touch_up_hook(self, touch):
        self.paint_window.checkpoint()
        self.paint_window.refresh()


class PaintWindow(Widget):
    image = ObjectProperty(None)
    box_color = [255, 0, 255]
    box_highlight = [0, 255, 0]

    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        self.image_shape = image.shape
        size = self.image_shape[:2]
        self.image.texture = Texture.create(size=size, colorfmt='bgr', bufferfmt='ubyte')
        self.size_hint = (None, None)
        self.size = size

        self._layer_manager = LayerManager(image)
        self._action_manager = ActionManager(self._layer_manager)
        self._box_manager = BoxManager(image.shape, self.box_color, self.box_highlight)
        self.refresh()

    def undo(self):
        self._action_manager.undo()
        self.refresh()

    def redo(self):
        self._action_manager.redo()
        self.refresh()

    def draw_line(self, point, pen_size):
        self._action_manager.draw_line(point, pen_size)
        self._box_manager.update_box(self._layer_manager.get_selected_layer().name, point, pen_size)

    def fill(self, point):
        self._action_manager.fill(point)

    def checkpoint(self):
        self._action_manager.checkpoint()

    def refresh(self):
        t0 = time.time()
        # Stack Operation
        stack = self._layer_manager.get_stack()
        t1 = time.time()
        # Collapse Operation
        bounds = self._box_manager.get_bounds()
        buffer = _collapse_select(stack, bounds, self._layer_manager._layer_visibility, self._layer_manager.get_selected_layer())
        t2 = time.time()
        # Box Operation
        self._box_manager.draw_boxes(buffer)
        t3 = time.time()
        # Canvas Operation
        self.image.texture.blit_buffer(buffer.ravel(), colorfmt='bgr', bufferfmt='ubyte')
        self.image.canvas.ask_update()
        t4 = time.time()

        print("[FPS: %.2f #%d] | Stack: %f\tCollapse: %f\tBox: %f (%f)\tCanvas: %f" %
              (1 / (t4 - t0), stack.shape[0], t1 - t0, t2 - t1, t3 - t2, (t3 - t2)/stack.shape[0],t4 - t3))

    def add_layer(self, name, color):
        print("Adding Layer[%d]: %s" % (self._layer_manager._layer_index, name))
        self._layer_manager.add_layer(name, color)
        self._action_manager.clear_history()
        self._box_manager.add_box(self._layer_manager.get_layer(name))
        self.select_layer(name)
        self.checkpoint()

    def delete_layer(self, name):
        self._layer_manager.delete_layer(name)
        self._box_manager.delete_box(name)
        self.checkpoint()

    def select_layer(self, name):
        self._layer_manager.select_layer(name)
        self._box_manager.select_box(self._layer_manager.get_selected_layer().name)

    def set_visible(self, visible):
        self._layer_manager.set_visible(visible=visible)


class ActionManager:
    line_granularity = 0.3
    initial_capacity = 4
    growth_factor = 2

    def __init__(self, layer_manager):
        self._layer_manager = layer_manager
        self._current_line = None
        self._layer_history = np.empty(shape=(self.initial_capacity,) + self._layer_manager.get_base_image().shape, dtype=np.uint8)
        self._history_idx = -1
        self._history_max = 0

    def undo(self):
        try:
            mat = self._layer_manager.get_selected_layer().get_mat()
            self._history_idx -= 1
            mat[:] = self._layer_history[self._history_idx].copy()
        except IndexError:
            return

    def redo(self):
        try:
            mat = self._layer_manager.get_selected_layer().get_mat()
            self._history_idx += 1
            mat[:] = self._layer_history[self._history_idx].copy()
        except IndexError:
            return

    def clear_history(self):
        self._history_idx = -1
        self._history_max = 0

    def checkpoint(self):
        layer = self._layer_manager.get_selected_layer()
        self._current_line = None
        self._history_idx += 1
        self._history_max = self._history_idx + 1
        if self._history_idx >= self._layer_history.shape[0]:
            self._layer_history.resize((self._layer_history.shape[0] * self.growth_factor,) + self._layer_history.shape[1:])
            print("LayerHistory: %s %s" % (str(self._layer_history.shape), str(self._layer_history.dtype)))
        self._layer_history[self._history_idx] = layer.get_mat().copy()

    def draw_line(self, point, pen_size):
        point = invert_coords(point)
        if self._current_line is None:
            self._current_line = tuple(point)

        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        self._draw_line_thick(layer.get_mat(), self._current_line, tuple(point), layer.color, pen_size)
        self._current_line = tuple(point)

    def fill(self, point):
        point = invert_coords(point)
        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        mat = layer.get_mat()
        mat_grey = rgb2gray(mat)
        mat[flood(mat_grey, tuple(point), connectivity=1)] = layer.color

    def _draw_line_thick(self, mat, p0, p1, color, thickness):
        mat[disk(p0, thickness, shape=mat.shape)] = color
        mat[disk(p1, thickness, shape=mat.shape)] = color

        d = np.array((p1[0] - p0[0], p1[1] - p0[1]))
        if np.all(np.abs(d) <= 5):
            return
        else:
            step_size = thickness * self.line_granularity / np.sqrt(np.dot(d, d))
            for i in np.arange(0.0, 1.0, step_size):
                c = np.round(p0 + i * d)
                mat[disk(c, thickness, shape=mat.shape)] = color


class LayerManager:
    initial_capacity = 4
    growth_factor = 2

    class Layer:
        def __init__(self, name, color, idx, manager):
            self.name = name
            self.color = color
            self.idx = idx
            self._manager = manager

        def get_mat(self):
            return self._manager.get_layer_mat(self.name)

    def __init__(self, image):
        self._base_image = image.swapaxes(0, 1)
        self._selected_layer = None

        self._layer_dict = {}
        self._layer_capacity = self.initial_capacity
        self._layer_stack = np.empty(shape=(self._layer_capacity,) + self._base_image.shape, dtype=np.uint8)
        self._layer_visibility = np.zeros(shape=(self._layer_capacity,), dtype=bool)
        self._layer_index = -1

        self._add_layer(self._base_image)

    def get_base_image(self):
        return self._base_image

    def delete_layer(self, name):
        layer = self._layer_dict.pop(name, None)
        if layer is None:
            return

        self._layer_stack[layer.idx] = 0
        self._layer_visibility[layer.idx] = False

    def add_layer(self, name, color):
        self._add_layer()
        layer = LayerManager.Layer(name, color, self._layer_index, self)
        self._layer_dict[layer.name] = layer

    def select_layer(self, name):
        self._selected_layer = self._layer_dict[name]

    def get_layer(self, name):
        return self._layer_dict.get(name, None)

    def get_layer_mat(self, name):
        try:
            layer = self._layer_dict[name]
            return self._layer_stack[layer.idx]
        except KeyError:
            return None

    def get_selected_layer(self):
        return self._selected_layer

    def get_all_layer_names(self):
        return [x.name for x in self._layer_dict.values()]

    def set_visible(self, idx=None, visible=True):
        if idx is None:
            idx = self.get_selected_layer().idx
        self._layer_visibility[idx] = visible

    def get_stack(self):
        return self._layer_stack[:self._layer_index + 1]

    def _add_layer(self, mat=None):
        self._layer_index += 1

        # Resize arraylists
        if self._layer_index == self._layer_capacity:
            self._resize()

        if mat is None:
            self._layer_stack[self._layer_index] = 0
        else:
            self._layer_stack[self._layer_index] = mat.copy()

        self.set_visible(self._layer_index, True)

    def _resize(self):
        self._layer_capacity = self._layer_capacity * self.growth_factor
        self._layer_stack.resize((self._layer_capacity,) + self._base_image.shape)
        self._layer_visibility.resize(self._layer_capacity)

        print("LayerStack: %s %s" % (str(self._layer_stack.shape), str(self._layer_stack.dtype)))
        print("LayerVisibility: %s %s" % (str(self._layer_visibility.shape), str(self._layer_visibility.dtype)))



class BoxManager:
    box_thickness = 2
    initial_capacity = 4
    growth_factor = 2

    def __init__(self, image_shape, box_color, box_select_color):
        self.box_color = np.array(box_color)
        self.box_select_color = np.array(box_select_color)
        self.image_shape = image_shape

        self._box_dict = {}
        """ Bounding box in the form (x1, y1, x2, y2)"""
        self._bounds = np.empty(shape=(self.initial_capacity, 4), dtype=int)
        self._visibility = np.empty(shape=(self.initial_capacity,), dtype=bool)
        self._selected_box = 0
        self._next_idx = 0

    def add_box(self, layer):
        bounds = BoxManager._fit_box(layer.get_mat())
        try:
            idx = self._box_dict[layer.name]
            self._bounds[idx] = bounds
        except KeyError:
            self._bounds[self._next_idx] = bounds
            self._visibility[self._next_idx] = True
            self._box_dict[layer.name] = self._next_idx
            self._next_idx += 1
            if self._next_idx == self._bounds.shape[0]:
                self._bounds.resize((self._bounds.shape[0] * self.growth_factor, 4), refcheck=False)
                self._visibility.resize((self._visibility.shape[0] * self.growth_factor,), refcheck=False)
                print("Bounds: %s %s" % (str(self._bounds.shape), str(self._bounds.dtype)))
                print("BoundsVisibility: %s %s" % (str(self._visibility.shape), str(self._visibility.dtype)))



    def update_box(self, name, point, radius):
        point = invert_coords(point)
        point = np.array(point)
        try:
            idx = self._box_dict[name]
            bounds = self._bounds[idx]
            bounds[:2] = np.max((np.min((bounds[:2], point - radius), axis=0), np.zeros(2)), axis=0)
            bounds[2:] = np.min((np.max((bounds[2:], point + radius, np.zeros(2)), axis=0), invert_coords(self.image_shape[:2])), axis=0)
        except KeyError:
            return

    def delete_box(self, name):
        self._box_dict.pop(name, None)

    def get_bounds(self):
        return self._bounds[:self._next_idx]

    def set_visible(self, name, visible):
        idx = self._box_dict[name]
        self._visibility[idx] = visible

    def select_box(self, name):
        idx = self._box_dict[name]
        self._selected_box = idx

    def draw_boxes(self, image):
        _draw_boxes(image, self._bounds[:self._next_idx], self.box_color, self.box_thickness)
        _draw_boxes(image, self._bounds[self._selected_box:self._selected_box + 1], self.box_select_color, self.box_thickness)

    @staticmethod
    def _fit_box(img):
        if not np.any(img):
            return img.shape[0], img.shape[1], 0, 0

        rows = np.any(img, axis=1)
        cols = np.any(img, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        return rmin, cmin, rmax, cmax


def invert_coords(coords):
    return coords[::-1]


@jit(locals=dict(bounds=int32[:, :]), nopython=True, parallel=True)
def _draw_boxes(mat, bounds, color, thick):
    n_box = bounds.shape[0]
    for i in numba.prange(n_box):
        if np.all(bounds[i, 2:] == 0):
            continue

        # Inner coordinates
        ix0, iy0, ix1, iy1 = bounds[i]

        ox0 = max(ix0 - thick, 0)
        oy0 = max(iy0 - thick, 0)
        ox1 = min(ix1 + thick + 1, mat.shape[0])
        oy1 = min(iy1 + thick + 1, mat.shape[1])

        mat[ox0:ox1, oy0:iy0] = color
        mat[ox0:ox1, iy1:oy1] = color

        mat[ox0:ix0, oy0:oy1] = color
        mat[ix1:ox1, oy0:oy1] = color

def _collapse_select(stack, bounds, visible, layer):
    if layer is None or layer.idx == 0:
        return stack[0]
    else:
        return _collapse_idx(stack, bounds, visible, layer.idx).copy()

@jit(nopython=True, parallel=True)
def _collapse_idx(stack, bounds, visible, idx):
    out = stack[0]
    if not visible[idx]:
        return out
    img = stack[idx]
    box = bounds[idx - 1]
    rr = slice(box[0], box[2])
    cc = slice(box[1], box[3])
    out[rr, cc] = image_add(img[rr, cc], out[rr, cc])
    return out


def collapse_layers(stack, bounds, visible):
    if bounds.shape[0] == 0:
        return stack[0].copy()
    else:
        return _collapse_all_layers(stack, bounds, visible)


@jit(locals=dict(bounds=int32[:, :]), nopython=True)
def _collapse_all_layers(stack, bounds, visible):
    n_stack = stack.shape[0]
    out = stack[0].copy()
    for n in range(n_stack - 1):
        reverse_n = n_stack - 1 - n
        if not visible[reverse_n]:
            continue
        img = stack[reverse_n]
        box = bounds[reverse_n - 1]
        rr = slice(box[0], box[2])
        cc = slice(box[1], box[3])
        out[rr, cc] = image_add_visible(img[rr, cc], out[rr, cc], out[rr, cc] != stack[0, rr, cc])
    stack[0] = out
    return out


@vectorize([uint8(uint8, uint8, boolean)])
def image_add_visible(top, bot, force_bot=False):
    return bot if force_bot or top == 0 else top


@vectorize([uint8(uint8, uint8)])
def image_add(top, bot):
    return bot if top == 0 else top


if __name__ == '__main__':
    PaintApp().run()
