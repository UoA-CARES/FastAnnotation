"""
A utility file containing common methods
"""
import base64
import json
import os

from kivy.network.urlrequest import UrlRequest

from client.client_config import ClientConfig


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


def add_project_images(project_id, image_paths, on_success=None, on_fail=None):
    if not isinstance(image_paths, list):
        image_paths = [image_paths]

    body = []
    for path in image_paths:
        filename = os.path.basename(path)

        ext = "." + str(filename.split('.')[-1])
        filename = '.'.join(filename.split('.')[:-1])

        with open(path, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read())

        body.append({'name': filename, 'type': ext, 'image': encoded_image.decode('utf-8')})

    route = ClientConfig.SERVER_URL + "projects/" + str(project_id) + "/images"
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
