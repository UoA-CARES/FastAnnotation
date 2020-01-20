from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from datetime import datetime
from functools import partial


class SimpleClient(App):

    def __init__(self):
        super().__init__()
        self.status_label = Label(text='')

    def update_status_label(self, status_callback, *args):
        self.status_label.text = status_callback()

    def heartbeat_request(self):
        server_response = str(datetime.now())
        return "Last Heartbeat: " + server_response

    def build(self):
        self.status_label = Label(text='NULL')
        btn_heartbeat = Button(text='Check Heartbeat',
                               on_press=partial(self.update_status_label, self.heartbeat_request))

        root = BoxLayout(orientation='vertical')
        root.add_widget(self.status_label)
        root.add_widget(btn_heartbeat)
        return root


if __name__ == '__main__':
    SimpleClient().run()
