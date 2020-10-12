import random
import string

import numpy as np
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture

from client.screens.common import MouseDrawnTool
from client.pw_test import PaintWindow


class PaintApp(App):
    def build(self):
        return Test()


class Test(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        image = np.zeros(shape=(4000, 2000, 3), dtype=np.uint8)
        image[:] = (255, 0, 0)
        image[0:10, 0:10, :] = 0
        image[290:300, 0:10, :] = 80
        image[0:10, 190:200, :] = 160
        image[290:300, 190:200, :] = 240
        self.kivy_image = Image()
        self.kivy_image.texture = Texture.create(
            size=(
                image.shape[1],
                image.shape[0]),
            colorfmt='rgb',
            bufferfmt='ubyte')
        self.draw(image)
        self.add_widget(self.kivy_image)
        pw = PaintWindow(image)
        pw.add_layer('test', [255, 255, 255])
        drawtool = DrawTool(pw)
        self.add_widget(drawtool)
        self.kivy_image.size = self.size
        drawtool.size = self.size

    def draw(self, image):
        self.kivy_image.texture.blit_buffer(
            np.flip(
                image,
                0).ravel(),
            colorfmt='rgb',
            bufferfmt='ubyte')
        self.canvas.ask_update()


class DrawTool(MouseDrawnTool):
    def __init__(self, paint_window, **kwargs):
        super().__init__(**kwargs)
        self.paint_window = paint_window

        self.keyboard.create_shortcut(("lctrl", "z"), self.paint_window.undo)
        self.keyboard.create_shortcut(("lctrl", "y"), self.paint_window.redo)
        self.keyboard.create_shortcut("q", lambda: self.paint_window.set_visible(True))
        self.keyboard.create_shortcut("w", lambda: self.paint_window.set_visible(False))
        self.keyboard.activate()

        def random_name(N):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

        def random_color():
            return np.random.choice([0, 255], size=3).tolist()

        def add_random_layer():
            name = random_name(10)
            self.paint_window.add_layer(name, random_color())
            self.paint_window.select_layer(name)

        self.keyboard.create_shortcut("spacebar", add_random_layer)

    def on_touch_down_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        if self.keyboard.is_key_down("shift"):
            self.paint_window.fill(pos)
        else:
            self.paint_window.draw_line(pos, 50, new_line=True)
        self.parent.draw(self.paint_window.redraw())

    def on_touch_move_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        self.paint_window.draw_line(pos, 50)
        self.parent.draw(self.paint_window.redraw())

    def on_touch_up_hook(self, touch):
        self.paint_window.checkpoint()


if __name__ == '__main__':
    PaintApp().run()
