import cv2
import sys
import numpy as np
import time
from numba import njit, prange
from intbitset import intbitset
from skimage.draw import line, polygon, circle, ellipse, disk, rectangle

class MaskStack:
    def __init__(self, rows, cols):
        self._data = np.zeros(shape=(rows, cols), dtype=np.uint32)
        self._layer_count = 0

    def append(self, mask):
        mask = mask.astype(np.uint32) * 2 ** self._layer_count
        self._data += mask
        self._layer_count += 1

    def collapse(self):
        return self._data > 0



def random_mask(shape):
    return np.random.choice(a=[False, True], size=shape, p=[0.9, 0.1])


def mask2bits(mask):
    return np.packbits(mask)


def bits2mask(bits, shape):
    return np.unpackbits(bits)[:np.product(shape)].reshape(shape).astype(np.bool)

"""
Collapse optimization options
"""


def collapse(layers):
    return np.bitwise_or.reduce(layers, axis=0)


@njit
def collapse_numba(layers):
    output = np.empty_like(layers[0])
    for i in range(layers.shape[0]):
        output = np.bitwise_or(output, layers[i])
    return output


@njit(parallel=True)
def collapse_p_numba(layers):
    output = np.empty_like(layers[0])
    for j in prange(layers.shape[1]):
        for i in range(layers.shape[0]):
            output[j] = np.bitwise_or(output[j], layers[i,j])
    return output


def collpase_bitsets(bitsets):
    output = intbitset()
    for i in range(len(bitsets)):
        output |= bitsets[i]
    return output


def bitset2mask(bitset, shape):
    ii = np.array(bitset.tolist())
    rr = (ii / shape[0]).astype(int)
    cc = ii % shape[0]
    mask = np.zeros(shape=shape, dtype=np.bool)
    mask[cc, rr] = True
    return mask


class NumpyNumba:
    def __init__(self):
        collapse_numba(np.zeros(shape=(3,3,3), dtype=np.uint8))

    def generate(self, shape, N, dtype):
        new_shape = (N, np.ceil(np.product(shape) / np.iinfo(dtype).bits).astype(int))
        return np.random.randint(np.iinfo(dtype).max + 1, size=new_shape, dtype=dtype)

    def collapse(self, data):
        return collapse_numba(data)

    def convert(self, data, shape):
        return bits2mask(data.view(np.uint8), shape)


class NumpyNumbaParallel:
    def __init__(self):
        collapse_p_numba(np.zeros(shape=(3,3,3), dtype=np.uint8))

    def generate(self, shape, N, dtype):
        new_shape = (N, np.ceil(np.product(shape) / np.iinfo(dtype).bits).astype(int))
        return np.random.randint(np.iinfo(dtype).max + 1, size=new_shape, dtype=dtype)

    def collapse(self, data):
        return collapse_p_numba(data)

    def convert(self, data, shape):
        return bits2mask(data.view(np.uint8), shape)


class Intbitset:
    def generate(self, shape, N, dtype):
        output = []
        for i in range(N):
            bitset = intbitset(np.where(random_mask(shape).flatten()))
            output.append(bitset)
        return output

    def draw(self, data, shape, n):
        bitset = data[n]
        center = (np.random.randint(shape[0]), np.random.randint(shape[1]))
        radius = 100
        rr, cc = disk(center, radius, shape=shape)
        ii = cc * shape[0] + rr

        bitset += intbitset(ii.tolist())
        # for i in ii:
        #     bitset.add(i)

    def collapse(self, data):
        return collpase_bitsets(data)

    def convert(self, data, shape):
        ii = np.array(data.tolist())
        rr = ii % shape[0]
        cc = (ii / shape[0]).astype(int)
        mask = np.zeros(shape=shape, dtype=np.bool)
        if rr.size * cc.size > 0:
            mask[rr, cc] = True
        return mask


if __name__ == '__main__':
    N = 200
    M = 6
    D = 5
    shape = (4000, 3000)

    test = Intbitset()
    t0 = time.time()
    layers = test.generate(shape, N, np.uint64)
    t1 = time.time()
    test.draw(layers, shape, 0)
    t2 = time.time()
    test.collapse(layers)
    bits = test.collapse(layers)
    t3 = time.time()
    final_mask = test.convert(bits, shape)
    t4 = time.time()

    print("Generate: %f\tDraw: %f\tCollapse: %f\tConvert: %f" % (t1 - t0, t2 - t1, t3 - t2, t4 - t3))