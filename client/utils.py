"""
A utility file containing common methods
"""
import requests
import base64
import io
import json
import os

from PIL import Image
import cv2
import numpy as np
from kivy.graphics.texture import Texture
from kivy.uix.image import CoreImage
from kivy.clock import mainthread

from client.client_config import ClientConfig


class ApiException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code

    def __str__(self):
        return "ApiException, %s" % self.message


def get_project_by_id(id):
    url = ClientConfig.SERVER_URL + "projects/" + str(id)
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers)


def get_projects():
    url = ClientConfig.SERVER_URL + "projects"
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers)


def add_projects(names):
    if not isinstance(names, list):
        names = [names]

    body = []
    for n in names:
        body.append({'name': n})

    payload = json.dumps({"projects": body})
    url = ClientConfig.SERVER_URL + "projects"
    headers = {"Content-Type": "application/json"}
    return requests.post(url, headers=headers, data=payload)


def delete_project(id):
    url = ClientConfig.SERVER_URL + "projects/" + str(id)
    return requests.delete(url)


def add_project_images(project_id, image_paths):
    if not isinstance(image_paths, list):
        image_paths = [image_paths]

    body = []
    for path in image_paths:
        filename = os.path.basename(path)

        ext = "." + str(filename.split('.')[-1])
        filename = '.'.join(filename.split('.')[:-1])

        body.append({'name': filename, 'ext': ext,
                     'image_data': encode_image(path)})

    payload = json.dumps({'images': body})
    url = ClientConfig.SERVER_URL + "projects/" + str(project_id) + "/images"
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}
    return requests.post(url, headers=headers, data=payload)


def get_project_images(project_id, filter_details=None):
    if not filter_details:
        filter_details = {}

    payload = json.dumps(filter_details)
    url = ClientConfig.SERVER_URL + "projects/" + \
        str(project_id) + "/images"
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}

    return requests.get(url, headers=headers, data=payload)


def update_image_meta_by_id(image_id, name=None, lock=None, labeled=None):
    image_meta = {}
    if name is not None:
        image_meta["name"] = str(name)
    if lock is not None:
        image_meta["is_locked"] = bool(lock)
    if labeled is not None:
        image_meta["is_labeled"] = bool(labeled)

    payload = json.dumps(image_meta)

    url = ClientConfig.SERVER_URL + "images/" + str(image_id)
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}

    return requests.put(url, headers=headers, data=payload)


def get_image_by_id(image_id):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id)
    headers = {"Accept": "application/json"}

    return requests.get(url, headers=headers)


def get_images_by_ids(image_ids):
    url = ClientConfig.SERVER_URL + "images"
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}
    body = {"ids": image_ids}

    payload = json.dumps(body)

    return requests.get(url, headers=headers, data=payload)


def get_image_metas_by_ids(image_ids):
    url = ClientConfig.SERVER_URL + "images?image-data=False"
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}
    body = {"ids": image_ids}
    payload = json.dumps(body)

    return requests.get(url, headers=headers, data=payload)


def add_image_annotation(image_id, annotations):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id) + "/annotation"
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}
    payload = {"image_id": image_id, "annotations": []}
    for annotation in annotations.values():
        body = {
            'name': annotation.annotation_name,
            'mask_data': encode_mask(mat2mask(annotation.mat)),
            'bbox': np.array(annotation.bbox).tolist(),
            'class_name': annotation.class_name,
            'shape': annotation.mat.shape}
        payload["annotations"].append(body)

    payload = json.dumps(payload)

    return requests.post(url, headers=headers, data=payload)


def delete_image_annotation(image_id, on_success=None, on_fail=None):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id) + "/annotation"
    return requests.delete(url)


def get_image_annotation(image_id, on_success=None, on_fail=None):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id) + "/annotation"
    headers = {"Accept": "application/json"}
    return requests.get(url, headers=headers)


# ======================
# === Helper methods ===
# ======================

def encode_image(img_path):
    with open(img_path, "rb") as img_file:
        encoded_image = base64.b64encode(img_file.read())
    return encoded_image.decode('utf-8')


def decode_image(b64_str):
    img_bytes_b64 = b64_str.encode('utf-8')
    return base64.b64decode(img_bytes_b64)


# Takes Boolean mask -> bytes
def encode_mask(mask):
    encoded_mask = base64.b64encode(mask.tobytes(order='C'))
    return encoded_mask.decode('utf-8')


# Takes bytes -> Boolean Mask
def decode_mask(b64_str, shape):
    mask_bytes = base64.b64decode(b64_str.encode("utf-8"))
    flat = np.fromstring(mask_bytes, bool)
    return np.reshape(flat, newshape=shape[:2], order='C')


def mask2mat(mask):
    mat = mask.astype(np.uint8) * 255
    return cv2.cvtColor(mat, cv2.COLOR_GRAY2BGR)


def mat2mask(mat):
    return np.sum(mat.astype(bool), axis=2, dtype=bool)


def bytes2mat(bytes):
    nparr = np.fromstring(bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def mat2bytes(mat, ext):
    buf = cv2.imencode(ext, mat)
    return buf[1].tostring()


def bytes2texture(bytes, ext):
    data = io.BytesIO(bytes)
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
    mat = cv2.flip(mat, 0)
    mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGBA)
    buf = mat.tostring()
    tex = Texture.create(size=(mat.shape[1], mat.shape[0]), colorfmt='rgba')
    tex.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
    return tex


def texture2mat(texture):
    pil_image = Image.frombytes(
        mode='RGBA',
        size=texture.size,
        data=texture.pixels)

    mat = np.array(pil_image)
    mat = cv2.flip(mat, 0)
    return cv2.cvtColor(mat, cv2.COLOR_RGBA2BGR)
