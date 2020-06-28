
import cv2
import numpy as np
import kivy
from kivy.app import App
from kivy.uix.image import Image
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.effectwidget import EffectWidget, InvertEffect
from glob import glob
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from client.screens.common import TransparentBlackEffect
from time import sleep
from kivy.graphics import Rectangle, Fbo, Color
from kivy.clock import Clock
import random
import time

import numpy as np
import cython
from numba.typed import List
from numba import vectorize

def mat2texture(mat):
    if mat.shape[-1] is not 4:
        mat = cv2.flip(mat, 0)
        mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGBA)
    buf = mat.tostring()
    tex = Texture.create(size=(mat.shape[1], mat.shape[0]), colorfmt='rgba')
    tex.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
    return tex


class MyApp(App):
    i = 0
    stack_capacity = 100

    def __init__(self, shape, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.image = np.zeros(shape=shape, dtype=np.uint8)
        self.image[:] = (0, 0, 255)
        self.stackmat = np.empty(shape=(np.product(shape), self.stack_capacity), dtype=np.uint8)
        self.stackmat_col = 0
        self.test = np.empty(shape=((self.stack_capacity,) + shape), dtype=np.uint8)
        self.test_bounds = np.empty(shape=(self.stack_capacity, 4), dtype=int)
        self.add_layer(self.image)

    def build(self):
        box = BoxLayout()
        self.img = Image(texture=mat2texture(self.image))
        box.add_widget(self.img)
        Clock.schedule_interval(lambda dt: self.add_random(), 0.01)

        return box

    def add_random(self):




        mat = np.zeros(shape=self.shape, dtype=np.uint8)
        center = (random.randint(0, 1500 - 1), random.randint(0, 2000 - 1))
        radius = random.randint(5, 50)
        color = tuple(np.random.choice(range(1,256), size=4).tolist())
        cv2.circle(mat, center=center, radius=radius, color=color, thickness=-1)

        self.add_layer(mat)
        self.add_bbox(self.stackmat_col - 1, center, radius)


        self.display()



    def add_bbox(self, idx, c, r):
        box = self.test_bounds[idx]
        c = np.array(c)
        box[:2] = np.min((box[:2], c-r), axis=0)
        box[2:] = np.max((box[2:], c+r), axis=0)



    def add_layer(self, mat):
        # self.stackmat = np.append(self.stackmat, mat.ravel(order='C')[:, np.newaxis], 1)
        if self.stackmat_col == self.stack_capacity:
            new_capacity = self.stack_capacity * 4
            stack = np.empty(shape=(np.product(self.shape), new_capacity), dtype=np.uint8)
            stack[:, :self.stack_capacity] = self.stackmat
            self.stackmat = stack
            self.stack_capacity = new_capacity

        self.stackmat[:, self.stackmat_col] = mat.flatten()

        self.test[self.stackmat_col] = mat
        self.test_bounds[self.stackmat_col] = [self.shape[0], self.shape[1], 0, 0]
        self.stackmat_col += 1




    # Reaches 1s delay at 58 (27 on laptop)
    def calculate_buffer(self):
        buf = np.zeros(np.product(self.shape), dtype=np.uint8)
        for layer in reversed(self.stack):
            buf[buf == 0] = layer[buf == 0]

        buf[buf == 0] = self.image.flatten(order='C')[buf == 0]
        return buf

    # Reaches 1s delay at 125 (67 on laptop)
    def calculate_buffer2(self):
        buf = np.vstack(tuple(reversed(self.stack)) + (self.image.ravel(order='C'),))
        buf = np.transpose(buf)
        return buffer_calc(buf)

    #Reaches 1s delay at 330 (80 on my laptop)
    def calculate_buffer3(self):
        buf = np.vstack(tuple(reversed(self.stack)) + (self.image.ravel(order='C'),))
        buf = np.transpose(buf)
        return buffer_calc_p(buf)


    # CONTENDERS

    # Ran out of RAM at 160 layers (0.62s max)
    # FPS after 50 ~ 3.2
    def calc_buffer6(self):
        # c2 = np.concatenate(self.stack, axis=0)
        c2 = self.stackmat[:, :self.stackmat_col]
        return buffer_calc_p2(c2)

    hist = None
    # 0.6s ,max at 200
    # FPS after 50 ~ 4.4
    # Hist boosted p2
    def calc_buffer7(self):
        if self.hist is None:
            self.hist = np.zeros(self.stackmat.shape[0], dtype=np.int)
        c2 = self.stackmat[:, :self.stackmat_col]
        buf = buffer_calc_2stage(c2, self.hist)
        return buf

    def calc_buffer7a(self):
        if self.hist is None:
            self.hist = np.zeros(self.stackmat.shape[0], dtype=np.int)
        c2 = self.stackmat[:, :self.stackmat_col]
        buf = buffer_calc_2stage2(c2, self.hist)
        return buf

    # FPS after 50 ~ 2.8
    def calc_bufferp3(self):
        c2 = self.stackmat[:, :self.stackmat_col]
        return buffer_calc_p3(c2)

    # FPS after 50 ~ 5.5
    # Box boosted p2
    def calc_calc8(self):
        c2 = self.test[:self.stackmat_col]
        b2 = self.test_bounds[:self.stackmat_col]
        return buffer_calc_bb(c2, b2).ravel()

    def calc_calc9(self):
        c2 = self.test[:self.stackmat_col]
        b2 = self.test_bounds[:self.stackmat_col]
        return buffer_calc_bb2(c2, b2).ravel()

    def calc_calc10(self):
        c2 = self.test[:self.stackmat_col]
        b2 = self.test_bounds[:self.stackmat_col]
        return quick_stack(c2, b2, self.stackmat_col - 1).ravel()


    # TODO: Box + hist boosted?

    def display(self):

        t0 = time.time()
        buf = self.calc_calc10()
        self.i += 1
        t1 = time.time()
        try:
            print("FPS %d: - %f(%f)" % (self.i, 1/(t1-t0),(t1 - t0)))
        except ZeroDivisionError:
            print("FPS %d: - MAX" % self.i)

        self.img.texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.img.canvas.ask_update()


import numba
from numba import jit


@jit(nopython=True)
def buffer_calc(stack):
    out = np.zeros(stack.shape[0], dtype=np.uint8)
    for i in range(stack.shape[0]):
        for j in range(stack.shape[1]):
            if stack[i, j] == 0:
                continue
            out[i] = stack[i, j]
            break
    return out

@jit(nopython=True, parallel=True)
def buffer_calc_p(stack):
    out = np.zeros(stack.shape[0], dtype=np.uint8)
    for i in numba.prange(stack.shape[0]):
        for j in range(stack.shape[1]):
            if stack[i, j] == 0:
                continue
            out[i] = stack[i, j]
            break
    return out

@jit(nopython=True, parallel=True)
def buffer_calc_p2(stack):
    width = stack.shape[1]
    height = stack.shape[0]
    out = np.zeros(height, dtype=np.uint8)
    for i in numba.prange(height):
        for j in range(width):
            reverse_j = width - 1 - j
            if stack[i, reverse_j] > 0:
                out[i] = stack[i, reverse_j]
                break
    return out

@jit(nopython=True, parallel=True)
def buffer_calc_p3(stack):
    width = stack.shape[1]
    height = stack.shape[0]
    out = np.zeros(height, dtype=np.uint8)
    for i in numba.prange(height):
        for j in range(width):
            reverse_j = width - 1 - j
            if out[i] == 0 and stack[i, reverse_j] > 0:
                out[i] = stack[i, reverse_j]
    return out


@jit(nopython=True, parallel=True)
def buffer_calc_2stage(stack, hist):
    width = stack.shape[1]
    height = stack.shape[0]
    out = np.zeros(height, dtype=np.uint8)
    for i in numba.prange(height):
        j1 = width - 1
        j2 = hist[i]
        if stack[i, j1] > 0:
            hist[i] = j1
            out[i] = stack[i, j1]
        elif stack[i, j2] > 0:
            hist[i] = j2
            out[i] = stack[i, j2]
        else:
            for j in range(width - 1):
                reverse_j = width - 1 - j
                if stack[i, reverse_j] > 0:
                    hist[i] = reverse_j
                    out[i] = stack[i, reverse_j]
                    break
    return out

@jit(nopython=True, parallel=True)
def buffer_calc_2stage2(stack, hist):
    width = stack.shape[1]
    height = stack.shape[0]
    out = np.zeros(height, dtype=np.uint8)
    for j in numba.prange(width):
        reverse_j = width - 1 - j
        for i in numba.prange(height):
            if stack[i, reverse_j] > 0 and out[i] == 0:
                hist[i] = reverse_j
                out[i] = stack[i, reverse_j]
    return out


@jit(nopython=True, parallel=True)
def buffer_calc_arrays(stack):
    width = stack.shape[1]
    height = stack.shape[0]
    out = np.zeros(height, dtype=np.uint8)
    for i in numba.prange(height):
        for j in range(width):
            reverse_j = width - 1 - j
            if stack[i, reverse_j] > 0:
                out[i] = stack[i, reverse_j]
                break
    return out

def calc_bbox(img):
    rows = np.any(img, axis=1)
    cols = np.any(img, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    return cmin, rmin, cmax, rmax

@jit(nopython=True, parallel=True)
def buffer_calc_bb(stack, bounds):
    n_stack = stack.shape[0]
    out = stack[0].copy()
    for n in numba.prange(n_stack):
        reverse_n = n_stack - 1 - n
        img = stack[reverse_n]
        box = bounds[reverse_n]
        for i in range(box[0], box[2]):
            for j in range(box[1], box[3]):
                if np.all(out[j, i] == stack[0, i, j]) and np.any(img[j, i] > 0):
                    out[j,i] = img[j,i]
    return out


from numba import int32


@jit(locals=dict(bounds=int32[:,:]), nopython=True, parallel=True)
def quick_stack(stack, bounds, idx):
    out = stack[0]
    img = stack[idx]
    box = bounds[idx]
    rr = slice(box[0], box[2])
    cc = slice(box[1], box[3])
    out[cc,rr] = image_add(img[cc,rr], out[cc,rr], False)
    return out


@jit(locals=dict(bounds=int32[:,:]), nopython=True, parallel=True)
def buffer_calc_bb2(stack, bounds):
    n_stack = stack.shape[0]
    out = stack[0].copy()
    for n in numba.prange(n_stack - 1):
        reverse_n = n_stack - 1 - n
        img = stack[reverse_n]
        box = bounds[reverse_n]
        rr = slice(box[0], box[2])
        cc = slice(box[1], box[3])
        out[cc,rr] = image_add(img[cc,rr], out[cc,rr], out[cc,rr] != stack[0,cc,rr])
    stack[0] = out
    return out

from numba import uint8, boolean

@vectorize([uint8(uint8, uint8, boolean)])
def image_add(top, bot, force_bot):
    return bot if force_bot or top == 0 else top


MyApp((3000,2000,3)).run()

