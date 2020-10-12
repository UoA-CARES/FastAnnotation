import numpy as np


class DynamicTable:
    def __init__(self, initial_capacity=10, growth_amount=10):
        self.capacity = initial_capacity
        self.growth_amount = growth_amount
        self._next_col = 0
        self._active_cols = []
        self._col_map = {}
        self._row_dict = {}

    def add_row(self, name, dtype, cell_shape):
        shape = (self.capacity,) + cell_shape
        row = np.zeros(shape=shape, dtype=dtype)
        if name in self._row_dict:
            raise KeyError("Row named '%s' already exists" % name)
        self._row_dict[name] = row

    def get_row(self, name):
        return self._row_dict[name][slice(self._next_col)]

    def add_col(self, name, row_data):
        if name in self._col_map:
            raise KeyError("Column named '%s' already exists" % name)
        self._active_cols.append(name)
        self._col_map[name] = self._next_col
        for k in row_data.keys():
            self._row_dict[k][self._next_col] = row_data[k]
        self._next_col += 1
        if self._next_col >= self.capacity:
            self._resize()

    def get_col(self, name):
        row_data = {}
        idx = self._col_map[name]
        for k in self._row_dict.keys():
            row_data[k] = self._row_dict[k][idx]
        return row_data

    def del_col(self, name):
        self._active_cols.remove(name)
        self._clean()

    def get_all(self):
        row_data = {}
        for k in self._row_dict.keys():
            row_data[k] = self.get_row(k)
        return row_data

    def columns(self):
        return self._active_cols

    def rows(self):
        return list(self._row_dict.keys())

    def _clean(self):
        deleted_idxs = [self._col_map[x] for x in self._col_map.keys() if x not in self._active_cols]

        for k in self._row_dict.keys():
            self._row_dict[k] = np.delete(self._row_dict[k], deleted_idxs, 0)

        self._col_map = {}
        self._next_col = len(self._active_cols)
        self.capacity -= 1
        for i in range(len(self._active_cols)):
            self._col_map[self._active_cols[i]] = i

    def _resize(self):
        if len(self._active_cols) < len(self._col_map.keys()):
            self._clean()
        self.capacity = self.capacity + self.growth_amount
        for row in self._row_dict.values():
            new_shape = list(row.shape)
            new_shape[0] = self.capacity
            row.resize(new_shape, refcheck=False)
        print("Resizing to %d. Total Size: %s" % (self.capacity, '{:,}'.format(self._get_size())))

    def _get_size(self):
        total = 0
        for row in self._row_dict.values():
            total += np.product(row.shape)
        return total