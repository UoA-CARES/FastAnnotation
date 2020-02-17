import json
from datetime import datetime

from kivy.app import App
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.SCREEN_DIR,
        'project_select_screen.kv'))


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
        total = project['labeled_count'] + project['unlabeled_count']
        pvw.add_card(
            project['project_name'],
            project['project_id'],
            "IMAGE",
            total,
            project['labeled_count'],
            project['last_uploaded'])

    def _add_project_failure(self, request, result):
        pop_up = Alert()
        pop_up.title = "Error!"
        if request.resp_status == 400:
            pop_up.alert_message = "A project named '%s' already exists." % json.loads(
                request.req_body)[0]['project_name']
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


class ProjectViewWindow(TileView):
    def add_card(
            self,
            name,
            id,
            image,
            total_images,
            labeled_images,
            last_update_time):
        card = ProjectCard()
        card.project_name = name
        card.project_id = id
        card.image = image
        card.total_images = total_images
        card.labeled_images = labeled_images
        card.last_update_time = datetime.fromtimestamp(last_update_time)
        self.add_widget(card)
        card.format_last_updated_label()

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
            total = project['labeled_count'] + project['unlabeled_count']
            self.add_card(
                project['project_name'],
                project['project_id'],
                "IMAGE",
                total,
                project['labeled_count'],
                project['last_uploaded'])


class ProjectCard(BoxLayout):
    project_name = StringProperty('')
    project_id = NumericProperty(0)
    image = StringProperty('')
    total_images = NumericProperty(0)
    labeled_images = NumericProperty(0)
    last_update_time = ObjectProperty(None)
    last_update_label = ObjectProperty(None)

    def confirm_delete_project(self):
        pop_up = DeleteProjectPopup()
        pop_up.title = "Delete '%s' Project" % self.project_name
        pop_up.message = "Are you sure you want to Delete the '%s' project?" % self.project_name
        pop_up.confirmation_callback = self.delete_card
        pop_up.open()

    def format_last_updated_label(self, *args):
        delta = datetime.utcnow() - self.last_update_time
        seconds = delta.total_seconds()

        if seconds < 0:
            seconds = 0

        time_dict = {}
        time_dict['year'] = seconds // ClientConfig.SECONDS_PER_YEAR
        time_dict['month'] = (
            seconds %
            ClientConfig.SECONDS_PER_YEAR) // ClientConfig.SECONDS_PER_MONTH
        time_dict['day'] = (
            seconds %
            ClientConfig.SECONDS_PER_MONTH) // ClientConfig.SECONDS_PER_DAY
        time_dict['hour'] = (
            seconds %
            ClientConfig.SECONDS_PER_DAY) // ClientConfig.SECONDS_PER_HOUR
        time_dict['minute'] = (
            seconds %
            ClientConfig.SECONDS_PER_HOUR) // ClientConfig.SECONDS_PER_MINUTE
        time_dict['second'] = seconds % ClientConfig.SECONDS_PER_MINUTE

        time = 0
        time_unit = "seconds"
        for key in time_dict:
            if time_dict[key] > 0:
                time = time_dict[key]
                time_unit = key
                if time_dict[key] > 1:
                    time_unit += "s"
                break

        self.last_update_label.text = 'Updated [b][color=%s]%d %s[/color][/b] ago' % (
            ClientConfig.CLIENT_HIGHLIGHT_1, time, time_unit)

    def delete_card(self):
        utils.delete_project(
            self.project_id,
            on_success=self._delete_card_success,
            on_fail=self._delete_card_failure)

    def _delete_card_success(self, request, result):
        print("Successfully deleted")
        pvw = App.get_running_app().root.current_screen.project_view_window
        pvw.remove_widget(self)

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


class ProjectSelectScreen(Screen):
    project_view_window = ObjectProperty(None)
    control_bar = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def on_enter(self, *args):
        self.project_view_window.refresh_projects()

    def enter_project(self, name, id, *args):
        self.app.current_project_name = name
        self.app.current_project_id = id

        self.app.sm.current = "ProjectTool"
