import os

from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty
from kivy.network.urlrequest import UrlRequest

from client.client_config import ClientConfig
from client.definitions import SCREEN_DIR

# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'project_screen.kv'))


class ControlBar(BoxLayout):
    def trigger_project_refresh(self):
        self.parent.parent.ids.project_view_window.refresh_projects()


class ProjectViewWindow(GridLayout):
    def refresh_projects(self, *args):
        route = ClientConfig.SERVER_URL + "projects"
        headers = {"Accept": "application/json"}
        UrlRequest(
            route,
            req_headers=headers,
            method="GET",
            on_success=self._refresh_handler)

    def _refresh_handler(self, request, result):
        self.clear_widgets()
        for project in result:
            card = ProjectCard()
            card.title = project['project_name']
            card.image = "IMAGE"
            self.add_widget(card)
            print(project['project_name'])
        return
    pass


class ProjectCard(BoxLayout):
    title = StringProperty('')
    image = StringProperty('')
    pass


class ProjectScreen(Screen):
    project_view_window = ObjectProperty(None)
    control_bar = ObjectProperty(None)

    def on_enter(self, *args):
        Clock.schedule_once(self.project_view_window.refresh_projects)
