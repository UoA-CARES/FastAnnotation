import os

import numpy as np
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
        return super(FloatLayout, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        self.on_touch_move_hook(touch)
        return super(FloatLayout, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        self.on_touch_up_hook(touch)
        return super(FloatLayout, self).on_touch_up(touch)


class NumericInput(StackLayout):
    value = NumericProperty(0)
    min = NumericProperty(-float('inf'))
    max = NumericProperty(float('inf'))
    step = NumericProperty(1)
    text_input = ObjectProperty(None)

    def validate_user_input(self):
        try:
            user_input = float(self.text_input.text)
        except ValueError:
            self.text_input.text = str(self.value)
        else:
            self.value = type(
                self.value)(
                np.clip(
                    user_input,
                    self.min,
                    self.max))


class TransparentBlackEffect(EffectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.glsl = """
        vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
        {
            if (color.r == 0.0 && color.g == 0.0 && color.b == 0.0) {
                return vec4(color.rgb,0.0);
            }
            return color;
        }
        """


class PaintWindow(Widget):
    fbo = ObjectProperty(None)
    mask_layer = ObjectProperty(None)
    mask_color = ObjectProperty([1, 1, 1, 1])

    def refresh(self):
        with self.mask_layer.canvas:
            self.fbo = Fbo(size=self.size)
            Rectangle(size=self.size, texture=self.fbo.texture)

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
