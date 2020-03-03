"""
A utility file containing common methods
"""
import base64
import io
import json
import os
import struct

from PIL import Image
import cv2
import numpy as np
from kivy.graphics.texture import Texture
from kivy.network.urlrequest import UrlRequest
from kivy.uix.image import CoreImage

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


def delete_project(id, on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "projects/" + str(id)
    UrlRequest(
        route,
        method="DELETE",
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

        body.append({'name': filename, 'type': ext,
                     'image': encode_image(path)})

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


def get_project_images(project_id, on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "projects/" + \
        str(project_id) + "/images"
    headers = {"Accept": "application/json"}
    UrlRequest(
        route,
        req_headers=headers,
        method="GET",
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)


def get_image_by_id(image_id, on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "images/" + str(image_id)
    headers = {"Accept": "application/json"}
    UrlRequest(
        route,
        req_headers=headers,
        method="GET",
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)


def get_image_meta_by_id(image_id, on_success=None, on_fail=None):
    route = ClientConfig.SERVER_URL + "images/" + str(image_id) + "/meta"
    headers = {"Accept": "application/json"}
    UrlRequest(
        route,
        req_headers=headers,
        method="GET",
        on_success=on_success,
        on_failure=on_fail,
        on_error=on_fail)


def encode_image(img_path):
    with open(img_path, "rb") as img_file:
        encoded_image = base64.b64encode(img_file.read())
    return encoded_image.decode('utf-8')


def decode_image(b64_str):
    img_bytes_b64 = b64_str.encode('utf-8')
    return base64.b64decode(img_bytes_b64)


def bytes2mat(bytes):
    nparr = np.fromstring(bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def mat2bytes(mat, ext):
    buf = cv2.imencode(ext, mat)
    return buf[1].tostring()


def bytes2texture(bytes, ext):
    data = io.BytesIO(bytes)
    # pil_image = Image.open(io.BytesIO(bytes))
    # tex = Texture.create(size=pil_image.size, colorfmt='bgr')
    # tex.blit_buffer(bytes, colorfmt='bgr', bufferfmt='ubyte')
    return CoreImage(data, ext=ext).texture


def texture2bytes(texture):
    pil_image = Image.frombytes(
        mode='RGBA',
        size=texture.size,
        data=texture.pixels)
    pil_image = pil_image.convert('RGB')
    b = io.BytesIO()
    pil_image.save(b, 'jpeg')
    return b.getvalue()


def mat2texture(mat):
    buf = mat.tostring()
    tex = Texture.create(size=(mat.shape[1], mat.shape[0]), colorfmt='bgr')
    tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
    return tex


def texture2mat(texture):
    pil_image = Image.frombytes(
        mode='RGBA',
        size=texture.size,
        data=texture.pixels)

    mat = np.array(pil_image)
    return cv2.cvtColor(mat, cv2.COLOR_RGBA2BGR)
