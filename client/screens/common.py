import math
import os

import numpy as np
from kivy.graphics import Color
from kivy.graphics import Rectangle, Fbo
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.actionbar import ActionItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.effectwidget import EffectBase
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget

from client.client_config import ClientConfig

# Load corresponding kivy file
Builder.load_file(os.path.join(ClientConfig.SCREEN_DIR, 'common.kv'))


class Alert(Popup):
    alert_message = StringProperty('')


class LabelInput(BoxLayout):
    text_field = ObjectProperty(None)


class ActionCustomButton(Button, ActionItem):
    pass


class TileView(GridLayout):
    tile_width = NumericProperty(0)
    tile_height = NumericProperty(0)


class MouseDrawnTool(FloatLayout):
    # Override these in child classes
    def on_touch_down_hook(self, touch):
        pass

    def on_touch_move_hook(self, touch):
        pass

    def on_touch_up_hook(self, touch):
        pass

    # Do not override these in child classes
    def on_touch_down(self, touch):
        self.on_touch_down_hook(touch)
        return super(MouseDrawnTool, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        self.on_touch_move_hook(touch)
        return super(MouseDrawnTool, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        self.on_touch_up_hook(touch)
        return super(MouseDrawnTool, self).on_touch_up(touch)


class NumericInput(StackLayout):
    decimal_places = NumericProperty(0)
    value = NumericProperty(0)
    min = NumericProperty(-float('inf'))
    max = NumericProperty(float('inf'))
    step = NumericProperty(1)
    text_input = ObjectProperty(None)

    def validate_user_input(self):
        try:
            user_input = float(self.text_input.text)
        except ValueError:
            pass
        else:
            self.value = type(self.value)(
                np.clip(
                    user_input,
                    self.min,
                    self.max))
        finally:
            self.text_input.text = str(self.value)

    def increment(self, n):
        # To accommodate for floating point division
        x = round(self.value / self.step, 10)
        # Round down to the nearest 'step size'
        x = math.floor(x) * self.step
        # Add n 'step size'
        x = x + (n * self.step)
        # Round to desired display decimal places
        x = round(x, self.decimal_places)
        # Clip to bounds
        x = np.clip(x, self.min, self.max)
        # Maintain type of value (int or float)
        self.value = type(self.value)(x)


class TransparentBlackEffect(EffectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.glsl = """
        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {
            if (color.r < 0.01 && color.g < 0.01 && color.b < 0.01) {
                return vec4(0.0, 0.0, 0.0, 0.0);
            }
            return color;
        }
        """


class PaintWindow(Widget):
    fbo = ObjectProperty(None)
    mask_layer = ObjectProperty(None)
    color = ObjectProperty(None)

    def refresh(self):
        with self.mask_layer.canvas:
            self.color = Color([1, 0, 1, 1])
            self.fbo = Fbo(size=self.size)
            Rectangle(size=self.size, texture=self.fbo.texture)

    def set_visible(self, visible=True):
        self.mask_layer.canvas.opacity = float(visible)

    def update_color(self, color):
        if self.color is None:
            return
        self.color.rgba = color

    def add_instruction(self, instruction):
        self.fbo.add(instruction)

    def remove_instruction(self, instruction):
        new_children = [x for x in self.fbo.children if x != instruction]
        self.fbo.clear()
        self.fbo.bind()
        self.fbo.clear_buffer()
        self.fbo.release()
        for c in new_children:
            self.fbo.add(c)

        self.fbo.draw()
