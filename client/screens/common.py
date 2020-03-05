import os

from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, NumericProperty, BooleanProperty, DictProperty
from kivy.uix.actionbar import ActionItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.image import Image

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


class MouseDrawnTool(Image):
    # A named dictionary of required properties
    tool_options = DictProperty({})

    def on_parent(self, *args):
        self.init_tool_options()

    # Override these in child classes

    def init_tool_options(self):
        pass

    def on_touch_down_hook(self, touch):
        pass

    def on_touch_move_hook(self, touch):
        pass

    def on_touch_up_hook(self, touch):
        pass

    # Do not override these in child classes
    def on_touch_down(self, touch):
        self.on_touch_down_hook(touch)
        return super(Image, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        self.on_touch_down_hook(touch)
        return super(Image, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        self.on_touch_up_hook(touch)
        return super(Image, self).on_touch_down(touch)
