from core.mask_stack import MaskStack
from skimage.draw import disk
import numpy as np
from random import randint, choices
import string
import time

def bounds(data, shape):
    data = data.view(np.uint8)
    nz = np.nonzero(data)[0]
    x0 = nz[0]
    x1 = nz[-1]
    nz = np.mod(nz, int(shape[0] / 8))
    y0 = np.min(nz)
    y1 = np.max(nz)
    return x0, y0, x1, y1


def rand_disk(shape):
    p = (randint(0, shape[0]), randint(0, shape[1]))
    max_size = np.ceil(min(shape) / 10).astype(int)
    min_size = np.ceil(min(shape) / 20).astype(int)
    size = randint(min_size, max_size)
    return disk(p, size, shape=shape)


def random_color():
    return np.random.choice([0, 255], size=3).tolist()


def random_name(N=10):
    return ''.join(choices(string.ascii_uppercase + string.digits, k=N))


M = 4000
N = 4000
K = 200

colors = []
for i in range(K):
    colors.append(random_color())
uniq_colors = np.unique(colors, axis=0)
stack = MaskStack(N, M)

for i in range(K):
    t0 = time.time()
    name = random_name()
    col = random_color()
    t0 = time.time()
    stack.add(name, col)
    rr, cc = rand_disk((N, M))
    rr1, cc1 = rand_disk((N, M))
    rr2, cc2 = rand_disk((N, M))
    t1 = time.time()
    stack.draw_on_mask(name, rr, cc)
    stack.draw_on_mask(name, rr1, cc1)
    stack.draw_on_mask(name, rr2, cc2)
    t2 = time.time()
    out = stack.collapse(uniq_colors=uniq_colors)
    t3 = time.time()
    print("[%d] |Total: %.3f | Add: %.3f | Draw: %.3f | Collapse: %.3f" % (i, t3 - t0, t1 - t0, t2 - t1, t3 - t2))


