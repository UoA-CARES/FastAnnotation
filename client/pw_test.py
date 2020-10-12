import numpy as np
from core.mask_stack import MaskStack
from core.dynamic_table import DynamicTable
from skimage.draw import disk

class Inverter:
    def __init__(self, image):
        self._height = image.shape[0]

    def invert(self, point):
        inv = np.zeros(2, dtype=int)
        inv[0] = self._height - point[1]
        inv[1] = point[0]
        return inv


class PaintWindow:
    DRAW_LINE_STEP_SIZE = 0.3

    def __init__(self, image):
        self._image_shape = image.shape
        self._mask_stack = MaskStack(image.shape[0], image.shape[1])
        self._inverter = Inverter(image)
        self._action_manager = ActionManager(self._mask_stack.mask_shape, self._mask_stack.IMAGE_DTYPE)
        self._current_line = None
        self._selected_layer = None

    def redraw(self):
        return self._mask_stack.collapse()

    def set_box_color(self, color):
        pass

    def set_box_highlight(self, color):
        pass

    def set_box_thickness(self, color):
        pass

    # Action Manager
    def undo(self):
        data = self._action_manager.undo()
        if data is None:
            return

        selected_name = self.get_selected()
        self._mask_stack.set_bit_mask(selected_name, data)
        # self.redraw()

    def redo(self):
        data = self._action_manager.redo()
        if data is None:
            return

        selected_name = self.get_selected()
        self._mask_stack.set_bit_mask(selected_name, data)
        # self.redraw()

    def checkpoint(self):
        bit_mask = self._mask_stack.get_bit_mask(self.get_selected())
        self._action_manager.checkpoint(bit_mask)
    ######

    # Drawing Inputs
    def draw_line(self, point, pen_size, new_line=False):
        point = self._inverter.invert(point)
        if new_line or self._current_line is None:
            p0 = point
        else:
            p0 = self._current_line
        self._current_line = point
        p1 = point
        rr, cc = self._draw_line(p0, p1, pen_size)

        selected_name = self.get_selected()
        self._mask_stack.draw_on_mask(selected_name, rr, cc)
        # self.redraw()

    def _draw_line(self, p0, p1, thickness):
        def flatten_disk(center, radius, shape):
            return np.ravel_multi_index(disk(center, radius, shape=shape[:2]), dims=shape[:2])

        idx = flatten_disk(p0, thickness, self._image_shape)
        idx = np.append(idx, flatten_disk(p1, thickness, self._image_shape))

        d = np.array((p1[0] - p0[0], p1[1] - p0[1]))
        if not np.any(np.abs(d) <= 5):
            step_size = thickness * \
                self.DRAW_LINE_STEP_SIZE / np.sqrt(np.dot(d, d))
            for i in np.arange(0.0, 1.0, step_size):
                c = np.round(p0 + i * d)
                idx = np.append(idx, flatten_disk(c, thickness, self._image_shape))
        idx = np.unique(idx)
        # idx = np.sort(idx)
        return np.unravel_index(idx, self._image_shape[:2])

    def fill(self, point):
        point = self._inverter.invert(point)
        pass
    ####

    ## Layer Manager > Use MaskStack?
    def get_layer(self, name):
        return self._mask_stack.get_bit_mask(name)

    def update_layer(self, name, color=None, mask=None, box=None, mask_vis=None, box_vis=None):
        if color:
            self._mask_stack.set_color(name, color)
        if mask:
            self._mask_stack.set_mask(name, mask)
        if box:
            self._mask_stack.set_bounds(name, box)
        if mask_vis:
            self._mask_stack.set_mask_vis(name, mask_vis)
        if box_vis:
            self._mask_stack.set_bound_vis(name, box_vis)

    def add_layer(self, name, color, mask=None, box=None):
        self._mask_stack.add(name, color)
        self.update_layer(name, mask=mask, box=box)

    def delete_layer(self, name):
        self._mask_stack.delete(name)
        if self.get_selected() == name:
            self.select_layer(None)

    ## Selection Manager
    def select_layer(self, name):
        if name:
            try:
                self._mask_stack.get_bit_mask(name)
            except KeyError:
                return
        self._selected_layer = name

    def select_layer_by_point(self, point):
        pass

    def get_selected(self):
        return self._selected_layer


class UserInputManager:
    pass


class ActionManager:
    HISTORY_DATA = "history"

    def __init__(self, dshape, dtype):
        self._dshape = dshape
        self._dtype = dtype
        self._history = None
        self._index = None
        self.clear()

    def undo(self):
        try:
            output = self._history.get_col(self._index - 1)
            self._index -= 1
            return output
        except KeyError:
            return None

    def redo(self):
        try:
            output = self._history.get_col(self._index + 1)
            self._index += 1
            return output
        except KeyError:
            return None

    def clear(self):
        self._history = DynamicTable()
        self._history.add_row(ActionManager.HISTORY_DATA, self._dtype, self._dshape)
        self._history.add_col(0, {ActionManager.HISTORY_DATA: np.zeros(self._dshape, dtype=self._dtype)})
        self._index = 0

    def checkpoint(self, data):
        self._index += 1
        try:
            row = self._history.get_col(self._index)[ActionManager.HISTORY_DATA]
            row[:] = data
            old_cols = [x for x in self._history.columns() if x > self._index]
            for x in old_cols:
                self._history.del_col(x)
        except KeyError:
            self._history.add_col(self._index, {ActionManager.HISTORY_DATA: data})

if __name__ == '__main__':
    N = 300000
    M = 5
    Stress_M = 1000
    x = ActionManager(dshape=(N,), dtype=np.uint64)
    for i in range(M):
        a = np.ones((N,), dtype=np.uint64) * i
        x.checkpoint(a)
    print("Undo")
    for i in range(M):
        print(x.undo())
    print("Redo")
    for i in range(M):
        print(x.redo())
    print("Undo Half")
    for i in range(int(M/2)):
        print(x.undo())
    print("Add half")
    for i in range(M, 2*M):
        a = np.ones((N,), dtype=np.uint64) * i
        x.checkpoint(a)
    print("Undo All")
    for i in range(2*M):
        print(x.undo())
    print("Stress Test")
    x.clear()
    for i in range(Stress_M):
        a = np.ones((N,), dtype=np.uint64) * i
        x.checkpoint(a)
    print("done")