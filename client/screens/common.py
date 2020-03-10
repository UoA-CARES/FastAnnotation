import os

import numpy as np
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.actionbar import ActionItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.stacklayout import StackLayout

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
