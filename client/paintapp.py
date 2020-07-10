import random
import string

import numpy as np
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout

from client.screens.common import MouseDrawnTool
from client.screens.paint_window import PaintWindow2


class PaintApp(App):
    def build(self):
        return Test()


class Test(RelativeLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        image = np.zeros(shape=(3000, 2000, 3), dtype=np.uint8)
        image[:] = (255, 0, 0)
        image[0:10, 0:10, :] = 0
        image[290:300, 0:10, :] = 80
        image[0:10, 190:200, :] = 160
        image[290:300, 190:200, :] = 240
        pw = PaintWindow2(image)
        self.add_widget(pw)
        pw.add_layer('test', [255, 255, 255])
        drawtool = DrawTool(pw)
        self.add_widget(drawtool)


class DrawTool(MouseDrawnTool):
    def __init__(self, paint_window, **kwargs):
        super().__init__(**kwargs)
        self.paint_window = paint_window
        self.size = self.paint_window.size

        self.keyboard.create_shortcut(("lctrl", "z"), self.paint_window.undo)
        self.keyboard.create_shortcut(("lctrl", "y"), self.paint_window.redo)
        self.keyboard.create_shortcut("q", lambda: self.paint_window.set_visible(True))
        self.keyboard.create_shortcut("w", lambda: self.paint_window.set_visible(False))
        self.keyboard.activate()

        def random_name(N):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

        def random_color():
            return np.random.choice(range(256), size=3).tolist()

        def add_random_layer():
            self.paint_window.add_layer(random_name(10), random_color())

        self.keyboard.create_shortcut("spacebar", add_random_layer)

    def on_touch_down_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        if self.keyboard.is_key_down("shift"):
            self.paint_window.fill(pos)
        else:
            self.paint_window.draw_line(pos, 10)
        self.paint_window.queue_refresh(True)

    def on_touch_move_hook(self, touch):
        pos = np.round(touch.pos).astype(int)
        self.paint_window.draw_line(pos, 10)
        self.paint_window.queue_refresh(True)

    def on_touch_up_hook(self, touch):
        self.paint_window.queue_checkpoint()
        self.paint_window.queue_refresh(True)


if __name__ == '__main__':
    PaintApp().run()
