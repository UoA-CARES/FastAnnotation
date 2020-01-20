from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.network.urlrequest import UrlRequest

from client.client_config import ClientConfig


class SimpleClient(App):

    def __init__(self):
        super().__init__()
        self.status_label = Label(text='')
        self.client_config = ClientConfig()

    def heartbeat_request(self, *args):
        UrlRequest(self.client_config.SERVER_URL, self.handle_heartbeat)

    def handle_heartbeat(self, req, result):
        self.status_label.text = str("Last Heartbeat: " + str(result))

    def build(self):
        self.status_label = Label(text='NULL')
        btn_heartbeat = Button(text='Check Heartbeat',
                               on_press=self.heartbeat_request)

        root = BoxLayout(orientation='vertical')
        root.add_widget(self.status_label)
        root.add_widget(btn_heartbeat)
        return root


if __name__ == '__main__':
    SimpleClient().run()
