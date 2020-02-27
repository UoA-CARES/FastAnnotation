import os

from kivy.lang import Builder
from kivy.network.urlrequest import UrlRequest
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen

from client.client_config import ClientConfig

# Load corresponding kivy file
Builder.load_file(os.path.join(ClientConfig.SCREEN_DIR, 'simple_screen.kv'))


class SimpleScreen(Screen):
    # Placeholder for label generated by .kv file
    status_label = ObjectProperty(None)

    def heartbeat_request(self, *args):
        UrlRequest(
            ClientConfig.SERVER_URL +
            "heartbeat",
            self.handle_heartbeat)

    def handle_heartbeat(self, req, result):
        self.status_label.text = str("Last Heartbeat: " + str(result))
