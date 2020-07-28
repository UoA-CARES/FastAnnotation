import math
import os

import numpy as np
from kivy.core.window import Window
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
Builder.load_file(os.path.join(ClientConfig.DATA_DIR, 'common.kv'))


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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.keyboard = KeyboardManager(Window.request_keyboard(lambda: None, self))

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


class KeyboardManager:
    def __init__(self, keyboard):
        self._keyboard_shortcuts = {}
        self.keycode_buffer = {}
        self._keyboard = keyboard

    def activate(self):
        self._keyboard.bind(on_key_down=self.on_key_down)
        self._keyboard.bind(on_key_up=self.on_key_up)

    def deactivate(self):
        self._keyboard.unbind(on_key_down=self.on_key_down)
        self._keyboard.unbind(on_key_up=self.on_key_up)

    def is_key_down(self, keycode):
        return keycode in self.keycode_buffer

    def create_shortcut(self, shortcut, func):
        if not isinstance(shortcut, tuple):
            shortcut = (shortcut,)
        self._keyboard_shortcuts[shortcut] = func

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in self.keycode_buffer:
            return
        self.keycode_buffer[keycode[1]] = keycode[0]

    def on_key_up(self, keyboard, keycode):
        for shortcut in self._keyboard_shortcuts.keys():
            if keycode[1] in shortcut and set(
                    shortcut).issubset(self.keycode_buffer):
                self._keyboard_shortcuts[shortcut]()

        self.keycode_buffer.pop(keycode[1])


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