import random
import string

import cv2
from skimage.draw import line, disk, rectangle_perimeter
from skimage.segmentation import flood
import numba
import numpy as np
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from numba import jit
from kivy.core.window import Window

from skimage.color import rgb2grey

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
        print(pos)
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

    def fill(self, point):
        self._action_manager.fill(point)

    def checkpoint(self):
        self._action_manager.checkpoint()
        self._box_manager.update_box(self._layer_manager.get_selected_layer())

    def refresh(self):
        t0 = time.time()
        stack = self._layer_manager.get_stack()
        t1 = time.time()
        buffer = collapse_layers(stack)
        t2 = time.time()
        image = buffer.reshape(self._layer_manager.get_base_image().shape, order='C')
        image[disk((10,10), 10)] = (0,0,0)
        image[disk((10,self._layer_manager.get_base_image().shape[1] - 10), 10)] = (80,80,80)
        self._box_manager.draw_boxes(image)
        # cv2.imshow('test', image)
        # cv2.waitKey(0)
        t3 = time.time()
        self.image.texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
        self.image.canvas.ask_update()
        t4 = time.time()

        print("[FPS: %.2f] | Stack: %f\tCollapse: %f\tBox: %f\tCanvas: %f" % (1/(t4-t0),t1-t0, t2-t1, t3-t2, t4-t3))

    def add_layer(self, name, color):
        self._layer_manager.add_layer(name, color)
        self.select_layer(name)
        self.checkpoint()

    def select_layer(self, name):
        current_layer = self._layer_manager.get_selected_layer()
        if current_layer is not None:
            self._box_manager.set_highlight(current_layer.name, False)

        self._layer_manager.select_layer(name)

        new_layer = self._layer_manager.get_selected_layer()
        self._box_manager.update_box(new_layer)
        self._box_manager.set_highlight(new_layer.name, True)


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
        point = invert_coords(point)
        if self._current_line is None:
            self._current_line = tuple(point)

        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        self._draw_line_thick(layer.mat, self._current_line, tuple(point), layer.color, pen_size)
        self._current_line = tuple(point)

    def fill(self, point):
        point = invert_coords(point)
        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        mat_grey = rgb2grey(layer.mat)
        layer.mat[flood(mat_grey, tuple(point), connectivity=1)] = layer.color

    def _draw_line_thick(self, mat, p0, p1, color, thickness):
        thickness = np.floor(thickness / 2).astype(int)
        mat[disk(p0, thickness, shape=mat.shape)] = color
        mat[disk(p1, thickness, shape=mat.shape)] = color

        d = np.array((p1[0] - p0[0], p1[1] - p0[1]))
        if np.all(np.abs(d) <= 5):
            return
        else:
            step_size = thickness / np.sqrt(np.dot(d, d))
            for i in np.arange(0.0, 1.0, step_size):
                c = np.round(p0 + i * d)
                mat[disk(c, thickness, shape=mat.shape)] = color

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

    def update_box(self, layer):
        bounds = BoxManager._fit_box(layer.mat)
        if layer.name in self._box_dict:
            self._box_dict[layer.name].bounds = bounds
        else:
            self._box_dict[layer.name] = Box(bounds, self.box_color)

    def set_visible(self, name, visible):
        self._box_dict[name].visible = visible

    def set_highlight(self, name, highlight):
        self._box_dict[name].color = self.box_select_color if highlight else self.box_color

    def draw_boxes(self, image):
        for box in self._box_dict.values():
            if box.bounds[2:] == [0, 0]:
                continue
            print("Drawing: %s | %s" % (str(box.bounds), str(box.color)))
            BoxManager._draw_box(image, box.bounds[:2], box.bounds[2:], box.color, self.box_thickness)

    @staticmethod
    def _draw_box(mat, p0, p1, color, thickness):
        p0 = np.array(p0)
        p1 = np.array(p1)
        d = p1 - p0
        d = np.clip(d, -1, 1)
        for i in range(thickness):
            c0 = p0 + i*d
            c1 = p1 - i*d
            rr, cc = rectangle_perimeter(start=tuple(c0), end=tuple(c1), shape=mat.shape, clip=True)
            mat[rr, cc] = color

    @staticmethod
    def _fit_box(img):
        #TODO: Optimize with numpy and numba
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

        # Flipping y coordinates to account for numpy origin vs kivy origin
        y1 = mat_gray.shape[0] - y1
        y2 = mat_gray.shape[0] - y2

        bounds = invert_coords((x1, y1)) + invert_coords((x2, y2))
        return bounds


def invert_coords(coords):
    return coords[::-1]


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
