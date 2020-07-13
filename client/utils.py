"""
A utility file containing common methods
"""
import base64
import io
import json
import os

import cv2
from numba import njit, vectorize, uint8, int32, boolean, prange
import numpy as np
import requests
from PIL import Image
from kivy.app import App
from kivy.graphics.texture import Texture
from kivy.uix.image import CoreImage
from numba import jit

from client.client_config import ClientConfig


class ApiException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code

    def __str__(self):
        return "ApiException, %s" % self.message


def background(f):
    def aux(*xs, **kws):
        app = App.get_running_app()
        future = app.thread_pool.submit(f, *xs, **kws)
        future.add_done_callback(app.alert_user)
        return future
    return aux


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


def get_image_by_id(image_id, max_dim=None):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id)
    if isinstance(max_dim, int):
        url += "?max-dim=%d" % max_dim
    headers = {"Accept": "application/json"}

    return requests.get(url, headers=headers)


def get_images_by_ids(image_ids, image_data=False, max_dim=None):
    url = ClientConfig.SERVER_URL + "images"
    url += "?image-data=%s" % str(image_data)
    if isinstance(max_dim, int):
        url += "&max-dim=%d" % max_dim
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


def get_image_annotation(image_id, max_dim=None, on_success=None, on_fail=None):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id) + "/annotation"
    if isinstance(max_dim, int):
        url += "?max-dim=%d" % max_dim
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
    return cv2.cvtColor(mat, cv2.COLOR_GRAY2RGB)


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
    if mat.shape[-1] is not 4:
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
    return cv2.cvtColor(mat, cv2.COLOR_RGBA2RGB)


def invert_coords(coords):
    return coords[::-1]


@njit(parallel=True)
def draw_boxes(mat, bounds, visible, color, thick):
    n_box = bounds.shape[0]
    height = mat.shape[0]
    for i in prange(n_box):
        if np.all(bounds[i, 2:] == 0):
            continue

        if not visible[i]:
            continue

        # Inner coordinates
        x0, y0, x1, y1 = bounds[i]

        # Flip coords to accomodate kivy
        ix0 = height - x1
        ix1 = height - x0
        iy0 = y0
        iy1 = y1

        ox0 = max(ix0 - thick, 0)
        oy0 = max(iy0 - thick, 0)
        ox1 = min(ix1 + thick, mat.shape[0])
        oy1 = min(iy1 + thick, mat.shape[1])

        mat[ox0:ox1, oy0:iy0] = color
        mat[ox0:ox1, iy1:oy1] = color

        mat[ox0:ix0, oy0:oy1] = color
        mat[ix1:ox1, oy0:oy1] = color


def collapse_bg(stack, bounds, visible, layer):
    if layer is None or layer.idx == 0:
        return stack[0]
    else:
        return _collapse_bg(stack, bounds, visible, layer.idx).copy()


def collapse_top(stack, bounds, visible, layer, bg):
    if layer is None or layer.idx == 0 or not visible[layer.idx]:
        return bg
    else:
        top = stack[layer.idx]
        top_bounds = bounds[layer.idx - 1]
        return _collapse_top(bg, top, top_bounds)


def fit_box(img):
    if not np.any(img):
        return img.shape[0], img.shape[1], 0, 0

    rows = np.any(img, axis=1)
    cols = np.any(img, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return rmin, cmin, rmax, cmax


@njit(parallel=True)
def _collapse_top(bg, top, top_bounds):
    out = bg.copy()
    rr = slice(top_bounds[0], top_bounds[2])
    cc = slice(top_bounds[1], top_bounds[3])
    out[rr, cc] = _image_add(top[rr, cc], out[rr, cc])
    return out

@njit
def _collapse_bg(stack, bounds, visible, idx):
    n_stack = stack.shape[0]
    out = stack[0].copy()
    for n in range(1, n_stack):
        if not visible[n]:
            continue

        if n is idx:
            continue

        img = stack[n]
        box = bounds[n - 1]
        rr = slice(box[0], box[2])
        cc = slice(box[1], box[3])
        out[rr, cc] = _image_add(img[rr, cc], out[rr, cc])
    return out


@vectorize([uint8(uint8, uint8)])
def _image_add(top, bot):
    return bot if top == 0 else top