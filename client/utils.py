"""
A utility file containing common methods
"""
from kivy.network.urlrequest import UrlRequest

from client.client_config import ClientConfig
import json


def get_project_by_id(id, on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "projects/" + str(id)
    headers = {"Accept": "application/json"}
    UrlRequest(
        route,
        req_headers=headers,
        method="GET",
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)


def get_projects(on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "projects"
    headers = {"Accept": "application/json"}
    UrlRequest(
        route,
        req_headers=headers,
        method="GET",
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)


def add_projects(names, on_success=None, on_fail=None):
    if not isinstance(names, list):
        names = [names]

    body = []
    for n in names:
        body.append({'project_name': n})

    route = ClientConfig.SERVER_URL + "projects"
    headers = {"Content-Type": "application/json"}
    UrlRequest(
        route,
        req_headers=headers,
        method="POST",
        req_body=json.dumps(body),
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)


def delete_project(id, on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "projects/" + str(id)
    UrlRequest(
        route,
        method="DELETE",
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)
