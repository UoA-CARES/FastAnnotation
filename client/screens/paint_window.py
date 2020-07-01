import time
import os

import numpy as np
from kivy.lang import Builder
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from skimage.color import rgb2gray
from skimage.draw import disk
from skimage.segmentation import flood

from client.utils import collapse_layers, collapse_select, draw_boxes, invert_coords
from client.client_config import ClientConfig

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
        'paint_window.kv'))


class PaintWindow(Widget):
    image = ObjectProperty(None)
    box_color = ObjectProperty(None)
    box_highlight = ObjectProperty(None)
    box_thickness = NumericProperty(2)

    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        self.image_shape = image.shape
        size = self.image_shape[:2]
        self.image.texture = Texture.create(size=size, colorfmt='bgr', bufferfmt='ubyte')
        self.size_hint = (None, None)
        self.size = size

        self._layer_manager = LayerManager(image)
        self._action_manager = ActionManager(self._layer_manager)
        self._box_manager = BoxManager(image.shape, self.box_color, self.box_highlight, self.box_thickness)

        self.box_color = (np.array(get_color_from_hex(ClientConfig.BBOX_UNSELECT)) * 255).astype(np.uint8)[:3]
        self.box_highlight = (np.array(get_color_from_hex(ClientConfig.BBOX_SELECT)) * 255).astype(np.uint8)[:3]
        self.refresh()

    def on_box_color(self, instance, value):
        self._box_manager.box_color = value

    def on_box_highlight(self, instance, value):
        self._box_manager.box_select_color = value

    def on_box_thickness(self, instance, value):
        self._box_manager.box_thickness = value

    def undo(self):
        self._action_manager.undo()
        self.refresh()

    def redo(self):
        self._action_manager.redo()
        self.refresh()

    def draw_line(self, point, pen_size):
        if self._layer_manager.get_selected_layer() is None:
            return
        self._action_manager.draw_line(point, pen_size)
        self._box_manager.update_box(self._layer_manager.get_selected_layer().name, point, pen_size)

    def fill(self, point):
        if self._layer_manager.get_selected_layer() is None:
            return
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
        buffer = collapse_select(stack, bounds, self._layer_manager._layer_visibility, self._layer_manager.get_selected_layer())
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
        color = np.array(color)
        if np.any(color):
            print("Incrementing zero values in label color")
            color[color == 0] = 1
        self._layer_manager.add_layer(name, color.tolist())
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
    growth_factor = 4

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
        print(layer.color)
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
    growth_factor = 4

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
    initial_capacity = 4
    growth_factor = 4

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
        draw_boxes(image, self._bounds[:self._next_idx], self.box_color, self.box_thickness)
        draw_boxes(image, self._bounds[self._selected_box:self._selected_box + 1], self.box_select_color, self.box_thickness)

    @staticmethod
    def _fit_box(img):
        if not np.any(img):
            return img.shape[0], img.shape[1], 0, 0

        rows = np.any(img, axis=1)
        cols = np.any(img, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        return rmin, cmin, rmax, cmax