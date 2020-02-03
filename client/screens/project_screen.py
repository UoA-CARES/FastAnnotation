import os
import json
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty
from kivy.network.urlrequest import UrlRequest
from kivy.factory import Factory

from client.client_config import ClientConfig
from client.definitions import SCREEN_DIR

# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'project_screen.kv'))


class Alert(Popup):
    alert_message = StringProperty('')
    pass


class LabelInput(BoxLayout):
    text_field = ObjectProperty(None)


class AddProjectPopup(Popup):
    def add_project(self, project_name, *args):
        # Perform Webservice Post
        # Wait ande
        route = ClientConfig.SERVER_URL + "projects"
        headers = {"Content-Type": "application/json"}
        body = {'project_name': project_name}
        UrlRequest(
            route,
            req_headers=headers,
            method="POST",
            req_body=json.dumps(body),
            on_success=self.success_callback,
            on_failure=self.failure_callback,
            on_error=self.failure_callback)

    def success_callback(self, request, result):
        self.dismiss()

    def failure_callback(self, request, result):
        pop_up = Alert()
        pop_up.title = "Error!"
        if request.resp_status == 400:
            pop_up.alert_message = "A project named '%s' already exists." % json.loads(
                request.req_body)['project_name']
        elif request.resp_status >= 500:
            pop_up.alert_message = "An unknown server error occurred."
        else:
            pop_up.alert_message = "Unknown error."
        pop_up.open()


class ControlBar(BoxLayout):
    def open_add_project_popup(self):
        pop_up = AddProjectPopup()
        pop_up.open()

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
            card.project_name = project['project_name']
            card.image = "IMAGE"
            self.add_widget(card)
            print(project['project_name'])
        return
    pass


class ProjectCard(BoxLayout):
    project_name = StringProperty('')
    image = StringProperty('')

    def delete_card(self):
        print("DELETING CARD %s" % self.project_name)


class ProjectScreen(Screen):
    project_view_window = ObjectProperty(None)
    control_bar = ObjectProperty(None)

    def on_enter(self, *args):
        Clock.schedule_once(self.project_view_window.refresh_projects)
