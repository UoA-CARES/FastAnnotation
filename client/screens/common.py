import os

from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.actionbar import ActionItem
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup

from client.definitions import SCREEN_DIR

# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'common.kv'))


class Alert(Popup):
    alert_message = StringProperty('')


class LabelInput(BoxLayout):
    text_field = ObjectProperty(None)


class ActionCustomButton(Button, ActionItem):
    pass


class TileView(GridLayout):
    tile_width = NumericProperty(0)
    tile_height = NumericProperty(0)
