from datetime import datetime

import dateutil.parser
from kivy.app import App
from kivy.clock import mainthread
from kivy.uix.screenmanager import Screen

import client.utils as utils
from client.screens.common import *
from client.utils import ApiException
from client.utils import background

# Load corresponding kivy file
Builder.load_file(
    os.path.join(
        ClientConfig.DATA_DIR,
        'project_select_screen.kv'))


class DeleteProjectPopup(Popup):
    title = StringProperty("")
    message = StringProperty("")
    confirmation_callback = ObjectProperty(None)


class AddProjectPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    @background
    def add_project(self, project_name):
        resp = utils.add_projects(project_name)

        if resp.status_code == 200:
            result = resp.json()
            msg = []
            for row in result["results"]:
                msg.append(row["error"]["message"])
            msg = '\n'.join(msg)
            raise ApiException(
                message="The following errors occurred while trying to add project '%s':\n %s" %
                (project_name, msg), code=resp.status_code)
        elif resp.status_code != 201:
            raise ApiException("Failed to add project '%s'." % project_name)

        result = resp.json()
        pvw = App.get_running_app().root.current_screen.project_view_window
        for row in result['projects']:
            total = row['labeled_count'] + row['unlabeled_count']
            pvw.add_card(
                row['name'],
                row['id'],
                "IMAGE",
                total,
                row['labeled_count'],
                row['last_uploaded'])
        self.dismiss()


class ProjectSelectScreen(Screen):
    project_view_window = ObjectProperty(None)
    control_bar = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.app = App.get_running_app()

    def on_enter(self, *args):
        self.project_view_window.refresh_projects()


class ControlBar(BoxLayout):
    @mainthread
    def open_add_project_popup(self):
        pop_up = AddProjectPopup()
        pop_up.open()

    def trigger_project_refresh(self):
        self.parent.parent.ids.project_view_window.refresh_projects()


class ProjectViewWindow(TileView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    @mainthread
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
        card.last_update_time = last_update_time
        self.add_widget(card)
        card.format_last_updated_label()

    @mainthread
    def remove_card(self, card):
        self.remove_widget(card)

    @background
    def refresh_projects(self):
        resp = utils.get_projects()
        if resp.status_code != 200:
            raise ApiException(
                "Failed to refresh project list",
                resp.status_code)

        result = resp.json()
        self.clear_widgets()
        for project in result["projects"]:
            total = project['labeled_count'] + project['unlabeled_count']
            self.add_card(
                project['name'],
                project['id'],
                "IMAGE",
                total,
                project['labeled_count'],
                dateutil.parser.parse(project['last_uploaded']))


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

    def format_last_updated_label(self):
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

    @background
    def delete_card(self):
        pid = self.project_id
        resp = utils.delete_project(pid)
        if resp.status_code != 200:
            raise ApiException(
                "Failed to delete project with id %d" %
                pid, resp.status_code)

        pvw = App.get_running_app().root.current_screen.project_view_window
        pvw.remove_card(self)
