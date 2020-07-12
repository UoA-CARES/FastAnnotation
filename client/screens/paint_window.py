import time
import os
import cv2

import numpy as np
from threading import Lock
from kivy.lang import Builder
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.clock import mainthread
from kivy.utils import get_color_from_hex
from skimage.color import rgb2gray
from skimage.draw import disk
from skimage.segmentation import flood

from client.utils import collapse_bg, collapse_top, draw_boxes, fit_box
from client.client_config import ClientConfig

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
        'paint_window.kv'))


class PaintWindow2(Widget):
    image = ObjectProperty(None)
    bg_image = ObjectProperty(None)
    box_color = ObjectProperty(None)
    box_highlight = ObjectProperty(None)
    box_thickness = NumericProperty(2)

    _checkpoint_lock = Lock()
    _checkpoint_flag = False
    _refresh_lock = Lock()
    _refresh_flag = False
    _refresh_all_flag = False

    class Inverter:
        def __init__(self, image):
            self._height = image.shape[0]

        def invert(self, point):
            inv = np.zeros(2, dtype=int)
            inv[0] = self._height - point[1]
            inv[1] = point[0]
            return inv

    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        self.image_shape = image.shape
        self.image.texture = Texture.create(size=(image.shape[1], image.shape[0]), colorfmt='rgb', bufferfmt='ubyte')
        self.bg_image.shape = image.shape
        self.bg_image.texture = Texture.create(size=(image.shape[1], image.shape[0]), colorfmt='rgb', bufferfmt='ubyte')
        self.bg_image.texture.blit_buffer(np.flip(image, 0).ravel(), colorfmt='rgb', bufferfmt='ubyte')
        self.bg_image.canvas.ask_update()
        self.size_hint = (None, None)
        self.size = (image.shape[1], image.shape[0])
        self.inverter = PaintWindow2.Inverter(image)

        self._bg_buffer = np.zeros(shape=image.shape, dtype=np.uint8)
        self._layer_manager = LayerManager(image)
        self._action_manager = ActionManager(self._layer_manager)
        self._box_manager = BoxManager(image.shape, self.box_color, self.box_highlight, self.box_thickness)

        self.box_color = (np.array(get_color_from_hex(ClientConfig.BBOX_UNSELECT)) * 255).astype(np.uint8)[:3]
        self.box_highlight = (np.array(get_color_from_hex(ClientConfig.BBOX_SELECT)) * 255).astype(np.uint8)[:3]
        self.queue_refresh()

    def on_box_color(self, instance, value):
        self._box_manager.box_color = value

    def on_box_highlight(self, instance, value):
        self._box_manager.box_select_color = value

    def on_box_thickness(self, instance, value):
        self._box_manager.box_thickness = value

    def undo(self):
        self._action_manager.undo()
        self.queue_refresh()

    def redo(self):
        self._action_manager.redo()
        self.queue_refresh()

    def draw_line(self, point, pen_size, color=None):
        point = self.inverter.invert(point)
        if self._layer_manager.get_selected() is None:
            return
        self._action_manager.draw_line(point, pen_size, color)
        self._box_manager.update_box(self._layer_manager.get_selected().name, point, pen_size)

    def fill(self, point, color=None):
        point = self.inverter.invert(point)
        if self._layer_manager.get_selected() is None:
            return
        self._action_manager.fill(point, color)

    def detect_collision(self, point):
        point = self.inverter.invert(point)
        mask = self._box_manager.detect_collision(point)
        if not np.any(mask):
            return None
        return np.array(self._layer_manager.get_all_names())[mask]

    def queue_checkpoint(self):
        with self._checkpoint_lock:
            if not self._checkpoint_flag:
                self._checkpoint_flag = True
                self._checkpoint()

    @mainthread
    def _checkpoint(self):
        self._action_manager.checkpoint()
        with self._checkpoint_lock:
            self._checkpoint_flag = False

    def queue_refresh(self, refresh_all=None):
        with self._refresh_lock:
            if refresh_all:
                self._refresh_all_flag = refresh_all
            if not self._refresh_flag:
                self._refresh_flag = True
                self._refresh()

    @mainthread
    def _refresh(self):
        t0 = time.time()
        # Stack Operation
        stack = self._layer_manager.get_stack()
        t1 = time.time()

        # Collapse Operation
        if self._refresh_all_flag:
            self._box_manager.fit_box(self._layer_manager.get_selected())
        bounds = self._box_manager.get_bounds()
        if self._refresh_all_flag:
            self._bg_buffer = collapse_bg(stack, bounds, self._layer_manager.get_visibility(), self._layer_manager.get_selected())
        buffer = collapse_top(stack, bounds, self._layer_manager.get_visibility(), self._layer_manager.get_selected(), self._bg_buffer)
        buffer = np.flip(buffer, 0)
        t2 = time.time()
        # Box Operation

        self._box_manager.draw_boxes(buffer)
        t3 = time.time()
        # Canvas Operation
        self.image.texture.blit_buffer(buffer.ravel(), colorfmt='rgb', bufferfmt='ubyte')
        self.image.canvas.ask_update()
        t4 = time.time()

        try:
            fps = "%.2f" % (1 / (t4 - t0))
        except ZeroDivisionError:
            fps = "MAX"

        print("[FPS: %s #%d] | Stack: %f\tCollapse: %f\tBox: %f (%f)\tCanvas: %f" %
              (fps, stack.shape[0], t1 - t0, t2 - t1, t3 - t2, (t3 - t2)/stack.shape[0],t4 - t3))

        with self._refresh_lock:
            self._refresh_flag = False
            self._refresh_all_flag = False

    def load_layers(self, names, colors, masks, boxes):
        refresh_all_required = False
        removed_layers = [x for x in self._layer_manager.get_all_names() if x not in names]
        for name in removed_layers:
            self.delete_layer(name)
            refresh_all_required = True

        selected = self._layer_manager.get_selected()
        selected_name = selected.name if selected else None

        for i in range(len(names)):
            name = names[i]
            if name in self._layer_manager.get_all_names():
                continue
            color = colors[i]
            mask = masks[i]
            box = boxes[i]
            if name is not selected_name:
                refresh_all_required = True
            self.add_layer(name, color, mask)
            self._box_manager.load_box(name, box)
        self.queue_refresh(refresh_all=refresh_all_required)

    def add_layer(self, name, color, mask=None):
        print("Adding Layer[%d]: %s" % (self._layer_manager._layer_index, name))
        self._layer_manager.add(name, color, mask)
        self._action_manager.clear_history()
        self._box_manager.fit_box(self._layer_manager.get(name))
        self.set_color(color, name)
        self.select_layer(name)
        self.queue_checkpoint()

    def delete_layer(self, name):
        self._layer_manager.delete(name)
        self._box_manager.delete_box(name)
        self.queue_checkpoint()

    def select_layer(self, name):
        self._layer_manager.select(name)
        self._box_manager.select_box(self._layer_manager.get_selected().name)

    def get_selected_layer(self):
        return self._layer_manager.get_selected()

    def set_visible(self, visible):
        self._layer_manager.set_visible(visible=visible)

    def set_color(self, color, name=None):
        if name is None:
            layer = self._layer_manager.get_selected()
        else:
            layer = self._layer_manager.get(name)

        if layer is None:
            return

        mat = layer.get_mat()
        if np.any(color):
            mat[np.all(mat != (0, 0, 0), axis=-1)] = color
        layer.color = color


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
            mat = self._layer_manager.get_selected().get_mat()
            self._history_idx -= 1
            mat[:] = self._layer_history[self._history_idx].copy()
        except IndexError:
            return

    def redo(self):
        try:
            mat = self._layer_manager.get_selected().get_mat()
            self._history_idx += 1
            mat[:] = self._layer_history[self._history_idx].copy()
        except IndexError:
            return

    def clear_history(self):
        self._history_idx = -1
        self._history_max = 0

    def checkpoint(self):
        layer = self._layer_manager.get_selected()
        if layer is None:
            return
        self._current_line = None
        self._history_idx += 1
        self._history_max = self._history_idx + 1
        if self._history_idx >= self._layer_history.shape[0]:
            self._layer_history.resize((self._layer_history.shape[0] * self.growth_factor,) + self._layer_history.shape[1:], refcheck=False)
            print("LayerHistory: %s %s" % (str(self._layer_history.shape), str(self._layer_history.dtype)))
        self._layer_history[self._history_idx] = layer.get_mat().copy()

    def draw_line(self, point, pen_size, color=None):
        if self._current_line is None:
            self._current_line = tuple(point)

        layer = self._layer_manager.get_selected()
        if layer is None:
            return

        if color is None:
            color = layer.color

        self._draw_line_thick(layer.get_mat(), self._current_line, tuple(point), color, pen_size)
        self._current_line = tuple(point)

    def fill(self, point, color=None):
        layer = self._layer_manager.get_selected()
        if layer is None:
            return

        if color is None:
            color = layer.color

        mat = layer.get_mat()
        mat_grey = rgb2gray(mat)
        mat[flood(mat_grey, tuple(point), connectivity=1)] = color

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
            return self._manager.get_mat(self.name)

    def __init__(self, image):
        self._base_image = image
        self._selected_layer = None

        self._layer_dict = {}
        self._layer_capacity = self.initial_capacity
        self._layer_stack = np.empty(shape=(self._layer_capacity,) + self._base_image.shape, dtype=np.uint8)
        self._layer_visibility = np.zeros(shape=(self._layer_capacity,), dtype=bool)
        self._layer_index = -1
        self._add(self._base_image)

    def get_base_image(self):
        return self._base_image

    def delete(self, name):
        layer = self._layer_dict.pop(name, None)
        if layer is None:
            return

        self._layer_stack[layer.idx] = 0
        self._layer_visibility[layer.idx] = False

    def add(self, name, color, mat=None):
        self._add(mat)
        layer = LayerManager.Layer(name, color, self._layer_index, self)
        self._layer_dict[layer.name] = layer

    def select(self, name):
        self._selected_layer = self._layer_dict[name]

    def get(self, name):
        return self._layer_dict.get(name, None)

    def get_mat(self, name):
        try:
            layer = self._layer_dict[name]
            return self._layer_stack[layer.idx]
        except KeyError:
            return None

    def get_selected(self):
        return self._selected_layer

    def get_all_names(self):
        return [x.name for x in self._layer_dict.values()]

    def set_visible(self, idx=None, visible=True):
        if idx is None:
            idx = self.get_selected().idx
        self._layer_visibility[idx] = visible

    def get_visibility(self):
        return self._layer_visibility[:self._layer_index + 1]

    def get_stack(self):
        return self._layer_stack[:self._layer_index + 1]

    def _add(self, mat=None):
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
        self._layer_stack.resize((self._layer_capacity,) + self._base_image.shape, refcheck=False)
        self._layer_visibility.resize(self._layer_capacity, refcheck=False)

        print("LayerStack: %s %s" % (str(self._layer_stack.shape), str(self._layer_stack.dtype)))
        print("LayerVisibility: %s %s" % (str(self._layer_visibility.shape), str(self._layer_visibility.dtype)))


class BoxManager:
    initial_capacity = 4
    growth_factor = 2

    def __init__(self, image_shape, box_color, box_select_color, box_thickness):
        self.box_thickness = box_thickness
        self.box_color = np.array(box_color)
        self.box_select_color = np.array(box_select_color)
        self.image_shape = image_shape

        self._box_dict = {}
        """ Bounding box in the form (x1, y1, x2, y2)"""
        self._bounds = np.empty(shape=(self.initial_capacity, 4), dtype=int)
        self._visibility = np.empty(shape=(self.initial_capacity,), dtype=bool)
        self._selected_box = 0
        self._next_idx = 0

    def detect_collision(self, pos):
        bl = self.get_bounds()[:, :2]
        tr = self.get_bounds()[:, 2:]
        return np.all(np.logical_and(bl < pos, pos < tr), axis=1)

    def fit_box(self, layer):
        bounds = fit_box(layer.get_mat())
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
        point = np.array(point)
        try:
            idx = self._box_dict[name]
            bounds = self._bounds[idx]
            bounds[:2] = np.min((bounds[:2], point - radius), axis=0)
            bounds[:2] = np.max((bounds[:2], np.zeros(2)), axis=0)
            bounds[2:] = np.max((bounds[2:], point + radius, np.zeros(2)), axis=0)
            bounds[2:] = np.min((bounds[2:], self.image_shape[:2]), axis=0)
        except KeyError:
            return

    def load_box(self, name, box):
        idx = self._box_dict[name]
        self._bounds[idx] = box

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
        draw_boxes(image, self._bounds[:self._next_idx], self.box_color, self.box_thickness)
        draw_boxes(image, self._bounds[self._selected_box:self._selected_box + 1], self.box_select_color, self.box_thickness)

