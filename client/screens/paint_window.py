import os
import time
from threading import Lock

import numpy as np
from kivy.clock import mainthread
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from skimage.color import rgb2gray
from skimage.draw import disk
from skimage.segmentation import flood

from client.client_config import ClientConfig
from client.utils import collapse_bg, collapse_top, draw_boxes, fit_box, DynamicTable

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
        'paint_window.kv'))

STACK_KEY = "stack"
COLOR_KEY = "color"
BOUNDS_KEY = "bounds"
VISIBLE_KEY = "vis"


class PaintWindow(Widget):
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
        self.inverter = PaintWindow.Inverter(image)

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
        self._box_manager.update_box(self._layer_manager.get_selected(), point, pen_size)

    def fill(self, point, color=None):
        point = self.inverter.invert(point)
        if self._layer_manager.get_selected() is None:
            return
        self._action_manager.fill(point, color)

    def detect_collision(self, point):
        point = self.inverter.invert(point)
        return self._box_manager.detect_collision(point)

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
        name = self._layer_manager.get_selected()
        idx = self._box_manager.get_idx(name)
        if self._refresh_all_flag:
            self._box_manager.fit_box(name, self._layer_manager.get_mask(name))
        bounds = self._box_manager.get_bounds()
        if self._refresh_all_flag:
            self._bg_buffer = collapse_bg(stack, bounds, self._layer_manager.get_visibility(), idx)
        buffer = collapse_top(stack, bounds, self._layer_manager.get_visibility(), idx, self._bg_buffer)
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

        # Mark image as unsaved
        with self._refresh_lock:
            self._refresh_flag = False
            self._refresh_all_flag = False

    def load_layers(self, names, colors, masks, boxes, mask_vis, box_vis):
        refresh_all_required = False

        removed_layers = [x for x in self._layer_manager.get_all_names() if x not in names]
        for name in removed_layers:
            if not name:
                continue
            self.delete_layer(name)
            refresh_all_required = True

        # Load new layers
        new_layers = [x for x in names if x not in self._layer_manager.get_all_names()]
        for i in range(len(new_layers)):
            name = new_layers[i]
            if name is not self._layer_manager.get_selected():
                refresh_all_required = True
            self.add_layer(name, colors[i], mask=masks[i])
            self._box_manager.set_bound(name, boxes[i])

        # Load Visibility
        for i in range(len(names)):
            if self._layer_manager.get_visible(names[i]) is not mask_vis[i]:
                self._layer_manager.set_visible(names[i], mask_vis[i])
                refresh_all_required = True

            if self._box_manager.get_visible(names[i]) is not mask_vis[i]:
                self._box_manager.set_visible(names[i], box_vis[i])
                refresh_all_required = True
        self.queue_refresh(refresh_all=refresh_all_required)

    def add_layer(self, name, color, box=None, mask=None):
        self._layer_manager.add(name, color, mask)
        self._action_manager.clear_history()
        self._box_manager.add(name, box)
        self.set_color(color, name)
        self.select_layer(name)
        self.queue_checkpoint()

    def delete_layer(self, name):
        self._layer_manager.delete(name)
        self._box_manager.delete(name)
        self.queue_checkpoint()

    def select_layer(self, name):
        self._layer_manager.select(name)
        self._box_manager.select_box(name)

    def get_selected_layer(self):
        return self._layer_manager.get_selected()

    def get_all_names(self):
        return self._layer_manager.get_all_names()

    def get_mask(self, name):
        return self._layer_manager.get_mask(name)

    def get_bound(self, name):
        return self._box_manager.get_bound(name)

    def get_color(self, name):
        return self._layer_manager.get_color(name)

    def set_visible(self, visible, name=None):
        if name is None:
            name = self._layer_manager.get_selected()
        if name is None:
            return
        self._layer_manager.set_visible(name, visible)

    def set_color(self, color, name=None):
        if name is None:
            name = self._layer_manager.get_selected()
        if name is None:
            return
        layer_data = self._layer_manager.get(name)

        try:
            mat = layer_data[STACK_KEY]
            if np.any(color):
                mat[np.all(mat != (0, 0, 0), axis=-1)] = color
            self._layer_manager.set_color(name, color)
        except (AttributeError, TypeError):
            return


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
            name = self._layer_manager.get_selected()
            mat = self._layer_manager.get_mask(name)
            self._history_idx -= 1
            mat[:] = self._layer_history[self._history_idx].copy()
        except (IndexError, AttributeError):
            return

    def redo(self):
        try:
            name = self._layer_manager.get_selected()
            mat = self._layer_manager.get_mask(name)
            self._history_idx += 1
            mat[:] = self._layer_history[self._history_idx].copy()
        except (IndexError, AttributeError):
            return

    def clear_history(self):
        self._history_idx = -1
        self._history_max = 0

    def checkpoint(self):
        name = self._layer_manager.get_selected()
        if name is None:
            return
        self._current_line = None
        self._history_idx += 1
        self._history_max = self._history_idx + 1

        if self._history_idx >= self._layer_history.shape[0]:
            self._layer_history.resize((self._layer_history.shape[0] * self.growth_factor,) + self._layer_history.shape[1:], refcheck=False)
            print("LayerHistory: %s %s" % (str(self._layer_history.shape), str(self._layer_history.dtype)))

        try:
            mat = self._layer_manager.get_mask(name)
            self._layer_history[self._history_idx] = mat.copy()
        except AttributeError:
            return

    def draw_line(self, point, pen_size, color=None):
        if self._current_line is None:
            self._current_line = tuple(point)

        name = self._layer_manager.get_selected()
        if name is None:
            return

        if color is None:
            color = self._layer_manager.get_color(name)

        mat = self._layer_manager.get_mask(name)
        self._draw_line_thick(mat, self._current_line, tuple(point), color, pen_size)
        self._current_line = tuple(point)

    def fill(self, point, color=None):
        name = self._layer_manager.get_selected()
        if name is None:
            return

        if color is None:
            color = self._layer_manager.get_color(name)
        try:
            mat = self._layer_manager.get_mask(name)
            mat_grey = rgb2gray(mat)
            mat[flood(mat_grey, tuple(point), connectivity=1)] = color
        except (AttributeError, IndexError):
            return

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
    def __init__(self, image):
        self._base_image = image
        self._selected_layer = None

        self._layers = DynamicTable()
        self._layers.add_row(STACK_KEY, dtype=np.uint8, cell_shape=self._base_image.shape)
        self._layers.add_row(VISIBLE_KEY, dtype=bool, cell_shape=(1,))
        self._layers.add_row(COLOR_KEY, dtype=np.uint8, cell_shape=(3,))

        row_data = {STACK_KEY: self._base_image, VISIBLE_KEY: True}
        self._layers.add_col("", row_data)

    def get_base_image(self):
        return self._base_image

    def delete(self, name):
        if name is None:
            return

        self._layers.del_col(name)
        if self._selected_layer == name:
            self._selected_layer = None

    def add(self, name, color, mat=None):
        if name is None:
            return

        if mat is None:
            mat = np.zeros(shape=self._base_image.shape, dtype=np.uint8)

        row_data = {STACK_KEY: mat, VISIBLE_KEY: True, COLOR_KEY: color}
        self._layers.add_col(name, row_data)

    def select(self, name):
        self._selected_layer = name

    def get(self, name):
        if name is None:
            return
        return self._layers.get_col(name)

    def get_selected(self):
        return self._selected_layer

    def get_all(self):
        return self._layers.get_all()

    def get_all_names(self):
        return self._layers.columns()

    def set_visible(self, name, visible=True):
        if name is None:
            return
        row = self._layers.get_col(name)
        row[VISIBLE_KEY][:] = visible

    def get_visible(self, name):
        if name is None:
            return
        row = self._layers.get_col(name)
        return row[VISIBLE_KEY]

    def set_color(self, name, color):
        if name is None:
            return
        row = self._layers.get_col(name)
        row[COLOR_KEY][:] = color

    def get_color(self, name):
        if name is None:
            return
        row = self._layers.get_col(name)
        return row[COLOR_KEY]

    def set_mask(self, name, mask):
        if name is None:
            return
        row = self._layers.get_col(name)
        row[STACK_KEY][:] = mask

    def get_mask(self, name):
        if name is None:
            return
        row = self._layers.get_col(name)
        return row[STACK_KEY]

    def get_visibility(self):
        return self._layers.get_row(VISIBLE_KEY)

    def get_stack(self):
        return self._layers.get_row(STACK_KEY)


class BoxManager:
    def __init__(self, image_shape, box_color, box_select_color, box_thickness):
        self.box_thickness = box_thickness
        self.box_color = np.array(box_color)
        self.box_select_color = np.array(box_select_color)
        self.image_shape = image_shape

        self._selected_box = None

        self._box_table = DynamicTable()
        """ Bounding box in the form (x1, y1, x2, y2)"""
        self._box_table.add_row(BOUNDS_KEY, dtype=int, cell_shape=(4,))
        self._box_table.add_row(VISIBLE_KEY, dtype=bool, cell_shape=(1,))

    def add(self, name, box=None, visible=True):
        if name is None:
            return

        if box is None:
            box = [self.image_shape[0], self.image_shape[1], 0, 0]
        col_data = {BOUNDS_KEY: box, VISIBLE_KEY: visible}
        self._box_table.add_col(name, col_data)

    def get(self, name):
        if name is None:
            return

        return self._box_table.get_col(name)

    def get_all(self):
        return self._box_table.get_all()

    def delete(self, name):
        if name is None:
            return

        if self._selected_box is name:
            self._selected_box = None

        self._box_table.del_col(name)

    def set_bound(self, name, box):
        if name is None:
            return

        col_data = self._box_table.get_col(name)
        col_data[BOUNDS_KEY][:] = box

    def get_bound(self, name):
        if name is None:
            return

        col_data = self._box_table.get_col(name)
        return col_data[BOUNDS_KEY]

    def set_visible(self, name, visible=True):
        if name is None:
            return

        col_data = self._box_table.get_col(name)
        col_data[VISIBLE_KEY][:] = visible

    def get_visible(self, name):
        if name is None:
            return

        col_data = self._box_table.get_col(name)
        return col_data[VISIBLE_KEY]

    def get_visibility(self):
        return self._box_table.get_row(VISIBLE_KEY)

    def get_bounds(self):
        return self._box_table.get_row(BOUNDS_KEY)

    def get_idx(self, name):
        boxes = self._box_table.columns()
        if name not in boxes:
            return -1
        else:
            return boxes.index(name)

    def detect_collision(self, pos):
        bounds = self._box_table.get_row(BOUNDS_KEY)
        bl = bounds[:, :2]
        tr = bounds[:, 2:]
        mask = np.all(np.logical_and(bl < pos, pos < tr), axis=1)
        return np.array(self._box_table.columns())[mask].tolist()

    def fit_box(self, name, mask):
        if name is None:
            return

        bounds = fit_box(mask)
        self.set_bound(name, bounds)

    def update_box(self, name, point, radius):
        if name is None:
            return

        point = np.array(point)
        try:
            bounds = self.get_bound(name)
            bounds[:2] = np.min((bounds[:2], point - radius), axis=0)
            bounds[:2] = np.max((bounds[:2], np.zeros(2)), axis=0)
            bounds[2:] = np.max((bounds[2:], point + radius, np.zeros(2)), axis=0)
            bounds[2:] = np.min((bounds[2:], self.image_shape[:2]), axis=0)
        except KeyError:
            return

    def select_box(self, name):
        self._selected_box = name

    def draw_boxes(self, image):
        bounds = self._box_table.get_row(BOUNDS_KEY)
        visible = self._box_table.get_row(VISIBLE_KEY)
        draw_boxes(image, bounds, visible, self.box_color, self.box_thickness)

        if self._selected_box is None:
            return

        select_idx = self.get_idx(self._selected_box)
        draw_boxes(image, bounds[select_idx:select_idx+1], visible[select_idx:select_idx+1], self.box_select_color, self.box_thickness)

