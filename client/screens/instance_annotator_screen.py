from kivy.uix.screenmanager import Screen

from client.screens.common import *

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'instance_annotator_screen.kv'))


class InstanceAnnotatorScreen(Screen):
    left_control = ObjectProperty(None)
    right_control = ObjectProperty(None)
    image_canvas = ObjectProperty(None)

    def load_image(self, image_id=-1):
        if image_id < 0:
            print("Load next Image")
        else:
            print("Load specific Image")

    def refresh_image_queue(self):
        print("Refreshing Image Queue")


class LeftControlColumn(BoxLayout):
    pass


class ImageCanvas(BoxLayout):
    pass


class RightControlColumn(BoxLayout):
    image_queue = ObjectProperty(None)


class ImageQueueControl(GridLayout):
    pass


class ImageQueue(GridLayout):
    def add_item(self, name, id):
        item = ImageQueueItem()
        item.image_name = name
        item.image_id = id
        self.add_widget(item)


class ImageQueueItem(Button):
    image_name = StringProperty("")
    image_id = NumericProperty(0)
