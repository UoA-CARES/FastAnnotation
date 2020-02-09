import os
import json
from kivy.lang import Builder
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.network.urlrequest import UrlRequest
from kivy.factory import Factory
from functools import partial

from client.client_config import ClientConfig
from client.definitions import SCREEN_DIR
import client.utils as utils

# Load corresponding kivy file
Builder.load_file(os.path.join(SCREEN_DIR, 'project_screen.kv'))


class Alert(Popup):
    alert_message = StringProperty('')
    pass


class LabelInput(BoxLayout):
    text_field = ObjectProperty(None)


class DeleteProjectPopup(Popup):
    title = StringProperty("")
    message = StringProperty("")
    confirmation_callback = ObjectProperty(None)
    pass


class AddProjectPopup(Popup):
    def add_project(self, project_name):
        utils.add_projects(
            project_name,
            on_success=self._add_project_success,
            on_fail=self._add_project_failure)

    def _add_project_success(self, request, result):
        for id in result['Created Ids']:
            utils.get_project_by_id(id,
                                    on_success=self._create_card_success,
                                    on_fail=self._add_project_failure)
        self.dismiss()

    def _create_card_success(self, request, result):
        pvw = App.get_running_app().root.current_screen.project_view_window
        project = result[0]
        pvw.add_card(project['project_name'], project['project_id'], "IMAGE")

    def _add_project_failure(self, request, result):
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
    def add_card(self, name, id, image):
        card = ProjectCard()
        card.project_name = name
        card.project_id = id
        card.image = image
        self.add_widget(card)

    def refresh_projects(self):
        utils.get_projects(on_success=self._refresh_projects_success)
        route = ClientConfig.SERVER_URL + "projects"
        headers = {"Accept": "application/json"}
        UrlRequest(
            route,
            req_headers=headers,
            method="GET",
            on_success=self._refresh_projects_success)

    def _refresh_projects_success(self, request, result):
        self.clear_widgets()
        for project in result:
            self.add_card(
                project['project_name'],
                project['project_id'],
                "IMAGE")


class ProjectCard(BoxLayout):
    project_name = StringProperty('')
    project_id = NumericProperty(0)
    image = StringProperty('')

    def confirm_delete_project(self):
        pop_up = DeleteProjectPopup()
        pop_up.title = "Delete '%s' Project" % self.project_name
        pop_up.message = "Are you sure you want to Delete the '%s' project?" % self.project_name
        pop_up.confirmation_callback = self.delete_card
        pop_up.open()

    def delete_card(self):
        utils.delete_project(
            self.project_id,
            on_success=self._delete_card_success,
            on_fail=self._delete_card_failure)

    def _delete_card_success(self, request, result):
        print("Successfully deleted")
        self.parent.remove_widget(self)

    def _delete_card_failure(self, request, result):
        pop_up = Alert()
        pop_up.title = "Error!"
        if request.resp_status == 400:
            pop_up.alert_message = "An error occurred when requesting to this deletion"
        elif request.resp_status >= 500:
            pop_up.alert_message = "An unknown server error occurred."
        else:
            pop_up.alert_message = "Unknown error."
        pop_up.open()


class ProjectScreen(Screen):
    project_view_window = ObjectProperty(None)
    control_bar = ObjectProperty(None)

    def on_enter(self, *args):
        self.project_view_window.refresh_projects()
