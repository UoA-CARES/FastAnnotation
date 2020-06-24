import random
import string

import cv2
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
        print(pos)
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

    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        self._layer_manager = LayerManager(image)
        self._action_manager = ActionManager(self._layer_manager)
        self._box_manager = BoxManager()
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
        buffer = self._layer_manager.collapse_all()
        self.image.texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
        self.image.canvas.ask_update()

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
        self._current_line = []
        self._history_index += 1
        self._layer_history = self._layer_history[:self._history_index]
        self._layer_history.append(layer.mat.copy())

    def draw_line(self, point, pen_size):
        if not self._current_line:
            self._current_line.append(point)

        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        cv2.line(layer.mat, tuple(self._current_line[-1]), tuple(point), layer.color, pen_size)
        self._current_line.append(point)

    def fill(self, point):
        layer = self._layer_manager.get_selected_layer()
        if layer is None:
            return

        if np.sum(layer.mat[point]) > 0:
            return

        mask = np.zeros((layer.mat.shape[1] + 2, layer.mat.shape[0] + 2), dtype=np.uint8)
        cv2.floodFill(layer.mat, mask, point, layer.color)


class Layer:
    def __init__(self, name, mat, color, visible=True):
        self.name = name
        self.mat = mat
        self.color = color
        self.visible = visible


class LayerManager:
    def __init__(self, image):
        self._layer_stack = []
        self._layer_dict = {}
        self._base_image = image.swapaxes(0, 1)
        self._selected_layer = None
        self._collapse_unselected_cache = None

    def get_base_image(self):
        return self._base_image

    def add_layer(self, name, color):
        mat = np.zeros(shape=self.get_base_image().shape, dtype=np.uint8)
        layer = Layer(name, mat, color)
        self._layer_stack.append(layer)
        self._layer_dict[layer.name] = layer

    def select_layer(self, name):
        self._selected_layer = self._layer_dict[name]
        self._collapse_unselected_cache = None

    def get_selected_layer(self):
        return self._selected_layer

    def set_visible(self, visible):
        self._selected_layer.visible = visible

    def collapse_all(self):
        unselected = self.collapse_unselected()
        if not self._selected_layer or not self._selected_layer.visible:
            return unselected
        else:
            buf = np.vstack((self._selected_layer.mat.ravel(), unselected))
            buf = np.transpose(buf)
            return LayerManager._collapse_operation(buf)

    def collapse_unselected(self):
        if self._collapse_unselected_cache is None:
            visible = [x.mat.ravel() for x in reversed(self._layer_stack) if
                       x.visible and x is not self._selected_layer]
            buf = np.vstack(tuple(visible) + (self._base_image.ravel(),))
            buf = np.transpose(buf)
            self._collapse_unselected_cache = LayerManager._collapse_operation(buf)
        return self._collapse_unselected_cache

    @staticmethod
    @jit(nopython=True, parallel=True)
    def _collapse_operation(stack):
        out = np.zeros(stack.shape[0], dtype=np.uint8)
        for i in numba.prange(stack.shape[0]):
            for j in range(stack.shape[1]):
                if stack[i, j] == 0:
                    continue
                out[i] = stack[i, j]
                break
        return out


class BoxManager:
    def __init__(self):
        self._box_dict = {}

    def add_box(self, layer):
        pass

    def fit_box(self, layer):
        pass

    def toggle_visible(self, name):
        pass

    def toggle_highlight(self, name):
        pass


PaintApp().run()
