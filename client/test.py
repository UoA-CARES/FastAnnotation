
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
    def __init__(self, shape, **kwargs):
        super().__init__(**kwargs)
        self.shape = shape
        self.image = np.zeros(shape=shape, dtype=np.uint8)
        self.image[:] = (0, 0, 255)
        self.stack = []

    def build(self):
        box = BoxLayout()
        self.img = Image(texture=mat2texture(self.image))

        box.add_widget(self.img)
        Clock.schedule_interval(lambda dt: self.add_random(), 0.01)

        return box

    def add_random(self):
        t0 = time.time()
        mat = np.zeros(shape=self.shape, dtype=np.uint8)
        center = (random.randint(0, 2000), random.randint(0, 1500))
        radius = random.randint(5, 50)
        color = tuple(np.random.choice(range(1,256), size=4).tolist())
        cv2.circle(mat, center=center, radius=radius, color=color, thickness=-1)
        self.stack.append(mat.ravel(order='C'))
        self.display()
        self.i += 1
        t1 = time.time()
        print("TEST %d - %f" %(self.i, t1-t0))

    # Reaches 1s delay at 58
    def calculate_buffer(self):
        buf = np.zeros(np.product(self.shape), dtype=np.uint8)
        for layer in reversed(self.stack):
            buf[buf == 0] = layer[buf == 0]

        buf[buf == 0] = self.image.flatten(order='C')[buf == 0]
        return buf

    # Reaches 1s delay at 125
    def calculate_buffer2(self):
        buf = np.vstack(tuple(reversed(self.stack)) + (self.image.ravel(order='C'),))
        buf = np.transpose(buf)
        return buffer_calc(buf)

    #Reaches 1s delay at 330
    def calculate_buffer3(self):
        buf = np.vstack(tuple(reversed(self.stack)) + (self.image.ravel(order='C'),))
        buf = np.transpose(buf)
        return buffer_calc_p(buf)




    def display(self):

        buf = self.calculate_buffer3()

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


MyApp((2000,1500,3)).run()
