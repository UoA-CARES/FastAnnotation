# cython: infer_types=True
# cython: boundscheck=False
# cython: wraparound=False

import Cython.Compiler.Options as CO
CO.extra_compile_args = ["-O3", "-funroll-loops", "-ffast-math", "-march=native", "-fopenmp" ]
CO.extra_link_args = ['-fopenmp']

cimport cython
import numpy as np
cimport numpy as np
from cython.parallel import prange

cdef unsigned int CHUNK_SIZE = 4
cdef unsigned int CHUNK_BITS = 64


def bitwise_or_reduce(unsigned long long[:, ::1] A, unsigned char[::1] mask, long long[:, ::1] bounds):
    cdef int num_layers = A.shape[0]
    cdef int layer_size = A.shape[1]
    cdef unsigned long long[::1] out = np.zeros(layer_size, dtype=np.uint64)
    cdef unsigned int i, j, k
    cdef long long start_j, end_j

    with nogil:
        for i in prange(num_layers):
            if mask[i]:
                start_j = bounds[i, 0]
                end_j = bounds[i, 1]
                for j in prange(start_j, end_j):
                    out[j] |= A[i,j]
    return out.base


def bitwise_set(unsigned long long[::1] data, long long[::1] ii):
    cdef int n = ii.shape[0]
    cdef unsigned long idx
    cdef unsigned int i, j
    cdef unsigned long long bit

    with nogil:
        for i in prange(n):
            idx = ii[i]
            j = idx / CHUNK_BITS
            bit = idx % CHUNK_BITS
            data[j] |= 2 ** bit


def bitview_to_mask(unsigned long long[::1] data):
    cdef int m = data.shape[0]
    cdef char[::1] out = np.empty(m * CHUNK_BITS, dtype=np.int8)
    cdef unsigned int i,j

    with nogil:
        for i in prange(m):
            for j in range(64):
                out[i*64 + j] = (data[i] >> j) & 1

    return out.base


def compute_bounds(unsigned long long[::1] data, int rows, int cols):
    cdef int m = data.shape[0]
    cdef unsigned int i,j
    cdef unsigned long long ii, idx, bit
    cdef unsigned long long[::1] out = np.empty(4, dtype=np.uint64)
    cdef bint top_flag = False, bot_flag = False, left_flag = False, right_flag = False

    with nogil:
        for i in range(rows):
            for j in range(cols):
                ii = i * cols + j
                idx = ii / CHUNK_BITS
                bit = ii % CHUNK_BITS
                if data[idx] >> bit:
                    out[0] = i
                    top_flag = True
                    break
            if top_flag:
                break

        for i in range(rows - 1, -1, -1):
            for j in range(cols):
                ii = i * cols + j
                idx = ii / CHUNK_BITS
                bit = ii % CHUNK_BITS
                if data[idx] >> bit:
                    out[2] = i
                    bot_flag = True
                    break
            if bot_flag:
                break

        for j in range(cols):
            for i in range(out[0], out[3] + 1):
                ii = i * cols + j
                idx = ii / CHUNK_BITS
                bit = ii % CHUNK_BITS
                if data[idx] >> bit:
                    out[1] = i
                    left_flag = True
                    break
            if left_flag:
                break

        for j in range(cols - 1, -1, -1):
            for i in range(out[0], out[3] + 1):
                ii = i * cols + j
                idx = ii / CHUNK_BITS
                bit = ii % CHUNK_BITS
                if data[idx] >> bit:
                    out[3] = i
                    right_flag = True
                    break
            if right_flag:
                break
    return out








