from core.dynamic_table import DynamicTable
from cython_build.cython_util import bitwise_or_reduce, bitwise_set, compute_bounds
import numpy as np

class MaskStack:
    IMAGE_DATA = "image"
    IMAGE_DTYPE = np.uint64
    COLOR_DATA = "color"
    COLOR_DTYPE = np.uint8
    COLOR_SHAPE = (3,)
    MASK_VIS_DATA = "mask_vis"
    MASK_VIS_DTYPE = np.bool
    MASK_VIS_SHAPE = (1,)
    BOUND_VIS_DATA = "bound_vis"
    BOUND_VIS_DTYPE = np.bool
    BOUND_VIS_SHAPE = (1,)
    BOUND_DATA = "bounds"
    BOUND_SHAPE = (4,)
    BOUND_DTYPE = np.int64

    BITORDER = 'big'

    def __init__(self, rows, cols):
        self.mask_shape = (np.ceil(rows * cols / np.iinfo(MaskStack.IMAGE_DTYPE).bits).astype(int),)
        self._rows = rows
        self._cols = cols
        self._data = DynamicTable()
        self._data.add_row(MaskStack.IMAGE_DATA, dtype=MaskStack.IMAGE_DTYPE, cell_shape=self.mask_shape)
        self._data.add_row(MaskStack.COLOR_DATA, dtype=MaskStack.COLOR_DTYPE, cell_shape=MaskStack.COLOR_SHAPE)
        self._data.add_row(MaskStack.MASK_VIS_DATA, dtype=MaskStack.MASK_VIS_DTYPE, cell_shape=MaskStack.MASK_VIS_SHAPE)
        self._data.add_row(MaskStack.BOUND_VIS_DATA, dtype=MaskStack.BOUND_VIS_DTYPE, cell_shape=MaskStack.BOUND_VIS_SHAPE)
        self._data.add_row(MaskStack.BOUND_DATA, dtype=MaskStack.BOUND_DTYPE, cell_shape=MaskStack.BOUND_SHAPE)

    def add(self, name, color):
        row_data = {
            MaskStack.IMAGE_DATA: np.zeros(shape=self.mask_shape, dtype=MaskStack.IMAGE_DTYPE),
            MaskStack.COLOR_DATA: np.array(color).astype(MaskStack.COLOR_DTYPE),
            MaskStack.MASK_VIS_DATA: np.ones(shape=MaskStack.MASK_VIS_SHAPE, dtype=MaskStack.MASK_VIS_DTYPE),
            MaskStack.BOUND_VIS_DATA: np.ones(shape=MaskStack.BOUND_VIS_SHAPE, dtype=MaskStack.BOUND_VIS_DTYPE),
            MaskStack.BOUND_DATA: np.zeros(shape=MaskStack.BOUND_SHAPE, dtype=MaskStack.BOUND_DTYPE)
        }

        self._data.add_col(name, row_data)

    def delete(self, name):
        self._data.del_col(name)

    def get_bit_mask(self, name):
        return self._data.get_col(name)[MaskStack.IMAGE_DATA]

    def set_bit_mask(self, name, data):
        self._data.get_col(name)[MaskStack.IMAGE_DATA] = data

    def get_color(self, name):
        return self._data.get_col(name)[MaskStack.COLOR_DATA]

    def set_color(self, name, color):
        col = self._data.get_col(name)
        col[MaskStack.COLOR_DATA][:] = color

    def get_mask_vis(self, name):
        return self._data.get_col(name)[MaskStack.MASK_VIS_DATA]

    def set_mask_vis(self, name, vis):
        self._data.get_col(name)[MaskStack.MASK_VIS_DATA] = vis

    def get_bound_vis(self, name):
        return self._data.get_col(name)[MaskStack.BOUND_VIS_DATA]

    def set_bound_vis(self, name, vis):
        self._data.get_col(name)[MaskStack.BOUND_VIS_DATA] = vis

    def get_bounds(self, name):
        return self._data.get_col(name)[MaskStack.BOUND_DATA]

    def set_bounds(self, name, bounds):
        self._data.get_col(name)[MaskStack.BOUND_DATA][:] = bounds

    def get_mask(self, name):
        return self._bitview_to_mask(self.get_bit_mask(name))

    def set_mask(self, name, mask):
        bit_view = self._mask_to_bitview(mask)
        self.set_bit_mask(name, bit_view)

    def clear_mask(self, name):
        col = self._data.get_col(name)
        col[MaskStack.IMAGE_DATA][:] = 0

    def draw_on_mask(self, name, rr, cc):
        if rr.size is 0 or cc.size is 0:
            return
        col = self._data.get_col(name)
        img = col[MaskStack.IMAGE_DATA]
        ii = np.ravel_multi_index((rr, cc), (self._rows, self._cols))
        bitwise_set(img, ii)

        bounds = col[MaskStack.BOUND_DATA]
        if bounds[0] > 0:
            bounds[0] = min(bounds[0], np.min(rr))
            bounds[1] = min(bounds[1], np.min(cc))
            bounds[2] = max(bounds[2], np.max(rr))
            bounds[3] = max(bounds[3], np.max(cc))
        else:
            bounds[:] = (np.min(rr), np.min(cc), np.max(rr), np.max(cc))

    def erase_on_mask(self, name, rr, cc):
        rr = np.ascontiguousarray(rr)
        cc = np.ascontiguousarray(cc)
        img = self._data.get_col(name)[MaskStack.IMAGE_DATA]
        bitwise_set(img, self._cols, rr, cc, 0)
        # cython compute bounds

    def collapse(self, order=False, uniq_colors=None):
        output = np.zeros(shape=(self._rows, self._cols) + MaskStack.COLOR_SHAPE, dtype=np.uint8)

        all_data = self._data.get_all()

        if order:
            raise NotImplementedError()

        color_data = all_data[MaskStack.COLOR_DATA]
        image_data = all_data[MaskStack.IMAGE_DATA]
        bound_data = all_data[MaskStack.BOUND_DATA]
        reduce_bounds = np.zeros((bound_data.shape[0], 2), dtype=np.int64)
        reduce_bounds[:, 0] = (bound_data[:, 0] * self._cols + bound_data[:, 1]) / np.iinfo(MaskStack.IMAGE_DTYPE).bits
        reduce_bounds[:, 1] = (bound_data[:, 2] * self._cols + bound_data[:, 3]) / np.iinfo(MaskStack.IMAGE_DTYPE).bits

        if uniq_colors is None:
            uniq_colors = np.unique(color_data, axis=0)

        for col in uniq_colors:
            mask = np.all(np.equal(color_data, col), axis=1)
            bit_mask = bitwise_or_reduce(image_data, mask, reduce_bounds)
            # image_mask = self._bitview_to_mask()
            # output[image_mask] = col
        return output

    def _bitview_to_mask(self, bit_view):
        flat_mask = np.unpackbits(bit_view.view(np.uint8), bitorder=self.BITORDER)
        return flat_mask[:(self._rows * self._cols)].reshape((self._rows, self._cols)).astype(np.bool)

    def _mask_to_bitview(self, mask):
        return np.packbits(mask.ravel(), bitorder=self.BITORDER).view(self.IMAGE_DTYPE)
