import numpy as np

import time
# Cython Functions to Compare
from cython_util import bitwise_or_reduce, bitwise_set, bitview_to_mask
from skimage.draw import disk

# Python Functions to Compare

def bitwise_or2(A):
    return np.bitwise_or.reduce(A.view(np.uint8), axis=0)

def np_bitview_to_mask(A):
    return np.unpackbits(A.view(np.uint8), bitorder='little')

def np_mask_to_bitview(A):
    return np.packbits(A.ravel(), bitorder='little').view(np.uint64)


if __name__ == "__main__":
    M = 187500
    N = 200
    reps = 20
    dtype = np.uint64
    total = 0

    A = np.random.randint(np.iinfo(dtype).max, size=M, dtype=dtype)
    t = time.time()
    out = bitview_to_mask(A)
    print("CYTHON get time: %f" % (time.time() - t))

    A = np.random.randint(np.iinfo(dtype).max, size=M, dtype=dtype)
    t = time.time()
    out = bitview_to_mask(A)
    print("NP get time: %f" % (time.time() - t))

    A = np.zeros(M, dtype=dtype)
    rr, cc = disk((2000, 1500), 1000)
    t = time.time()
    bitwise_set(A, 4000, np.ascontiguousarray(rr), np.ascontiguousarray(cc), 1)
    print("CYTHON set time: %f" % (time.time() - t))

    A = np.zeros(M, dtype=dtype)
    t = time.time()
    A_bool = np_bitview_to_mask(A).reshape((4000, 3000)).astype(np.bool)
    A_bool[rr, cc] = True
    A2 = np_mask_to_bitview(A_bool)
    print("NP set time: %f" % (time.time() - t))

    for j in range(100,400,100):
        for i in range(reps):
            A = np.random.randint(np.iinfo(dtype).max, size=(j, M), dtype=dtype)
            t = time.time()
            mask = np.ones(shape=(j,), dtype=np.bool)
            out = bitwise_or_reduce(A, mask)
            total += time.time() - t
        print("cython average [%d] :%fs (%fs per N)" % (j, total/reps, total/reps/j))



    A = np.random.randint(np.iinfo(dtype).max, size=(M, N), dtype=dtype)
    t = time.time()
    bitwise_or2(A)
    print("numpy finished :", time.time() - t, "s")

    print()
