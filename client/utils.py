"""
A utility file containing common methods
"""
import base64
import io
import json
import os
import zipfile
from tkinter import filedialog
from urllib.request import urlretrieve

import cv2
import numpy as np
import requests
from PIL import Image
from kivy.app import App
from kivy.graphics.texture import Texture
from kivy.uix.image import CoreImage
from numba import njit, vectorize, uint8, prange

from client.client_config import ClientConfig
from definitions import ROOT_DIR


class DynamicTable:
    def __init__(self, initial_capacity=10, growth_amount=10):
        self.capacity = initial_capacity
        self.growth_amount = growth_amount
        self._next_col = 0
        self._active_cols = []
        self._col_map = {}
        self._row_dict = {}

    def add_row(self, name, dtype, cell_shape):
        shape = (self.capacity,) + cell_shape
        row = np.zeros(shape=shape, dtype=dtype)
        if name in self._row_dict:
            raise KeyError("Row named '%s' already exists" % name)
        self._row_dict[name] = row

    def get_row(self, name):
        return self._row_dict[name][slice(self._next_col)]

    def add_col(self, name, row_data):
        if name in self._col_map:
            raise KeyError("Column named '%s' already exists" % name)
        self._active_cols.append(name)
        self._col_map[name] = self._next_col
        for k in row_data.keys():
            self._row_dict[k][self._next_col] = row_data[k]
        self._next_col += 1
        if self._next_col >= self.capacity:
            self._resize()

    def get_col(self, name):
        row_data = {}
        idx = self._col_map[name]
        for k in self._row_dict.keys():
            row_data[k] = self._row_dict[k][idx]
        return row_data

    def del_col(self, name):
        self._active_cols.remove(name)
        self._clean()

    def get_all(self):
        row_data = {}
        for k in self._row_dict.keys():
            row_data[k] = self.get_row(k)
        return row_data

    def columns(self):
        return self._active_cols

    def rows(self):
        return list(self._row_dict.keys())

    def _clean(self):
        deleted_idxs = [self._col_map[x] for x in self._col_map.keys() if x not in self._active_cols]

        for k in self._row_dict.keys():
            self._row_dict[k] = np.delete(self._row_dict[k], deleted_idxs, 0)

        self._col_map = {}
        self._next_col = len(self._active_cols)
        self.capacity -= 1
        for i in range(len(self._active_cols)):
            self._col_map[self._active_cols[i]] = i

    def _resize(self):
        if len(self._active_cols) < len(self._col_map.keys()):
            self._clean()
        self.capacity = self.capacity + self.growth_amount
        for row in self._row_dict.values():
            new_shape = list(row.shape)
            new_shape[0] = self.capacity
            row.resize(new_shape, refcheck=False)
        print("Resizing to %d. Total Size: %s" % (self.capacity, '{:,}'.format(self._get_size())))

    def _get_size(self):
        total = 0
        for row in self._row_dict.values():
            total += np.product(row.shape)
        return total


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


def get_image_by_id(image_id):
    url = ClientConfig.SERVER_URL + "images/" + str(image_id)
    headers = {"Accept": "application/json"}

    return requests.get(url, headers=headers)


def download_image(image_id):
    url = ClientConfig.SERVER_URL + "files/image/" + str(image_id)

    resp = requests.get(url)
    if resp.status_code == 404:
        raise ApiException(
            "Image does not exist with id %d." %
            image_id, resp.status_code)
    elif resp.status_code != 200:
        raise ApiException(
            "Failed to retrieve image with id %d." %
            image_id, resp.status_code)

    nparr = np.frombuffer(resp.content, np.uint8)
    mat = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
    return mat

def download_annotations(image_id):
    url = ClientConfig.SERVER_URL + "files/image/" + str(image_id) + "/annotations"

    resp = requests.get(url)
    if resp.status_code == 404:
        raise ApiException(
            "Image does not exist with id %d." %
            image_id, resp.status_code)
    elif resp.status_code != 200:
        raise ApiException(
            "Failed to retrieve image with id %d." %
            image_id, resp.status_code)

    z = zipfile.ZipFile(io.BytesIO(resp.content))

    output = {}
    for filename in z.namelist():
        annotation_id, _ = os.path.splitext(filename)
        nparr = np.frombuffer(z.read(filename), np.uint8)
        mat = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
        output[int(annotation_id)] = mat

    return output


def download_annotation(annotation_id):
    url = ClientConfig.SERVER_URL + "files/annotation/" + str(annotation_id)
    resp = requests.get(url)
    if resp.status_code == 404:
        raise ApiException(
            "Annotation does not exist with id %d." %
            annotation_id, resp.status_code)
    elif resp.status_code != 200:
        raise ApiException(
            "Failed to retrieve annotation with id %d." %
            annotation_id, resp.status_code)

    nparr = np.frombuffer(resp.content, np.uint8)
    mat = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    mat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
    return mat


def get_images_by_ids(image_ids):
    url = ClientConfig.SERVER_URL + "images"
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


def export_dataset(project_id):
    url = ClientConfig.SERVER_URL + "projects/" + str(project_id) + "/dataset"
    directory = filedialog.asksaveasfilename(title="Export dataset as zip",
                                             initialdir=ROOT_DIR,
                                             filetypes=[("ZIP Files", "*.zip")],
                                             defaultextension=".zip")
    if directory is None:
        return
    return urlretrieve(url, directory)

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
        if bounds[i, 2] == 0 and bounds[i, 3] == 0:
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


def collapse_bg(stack, bounds, visible, idx):
    if bounds.shape[0] < 2:
        return stack[0]
    else:
        return _collapse_bg(stack, bounds, visible, idx).copy()


def collapse_top(stack, bounds, visible, idx, bg):
    stack_idx = idx + 1
    if idx < 0 or not visible[stack_idx]:
        return bg
    else:
        top = stack[stack_idx]
        top_bounds = bounds[idx]
        return _collapse_top(bg, top, top_bounds)


def fit_box(img):
    if not np.any(img):
        return img.shape[0], img.shape[1], 0, 0

    rows = np.any(img, axis=1)
    cols = np.any(img, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return rmin, cmin, rmax, cmax


def is_valid_bounds(bounds):
    bounds = np.array(bounds)
    if np.sum(bounds) <= 0:
        return False
    return np.all(bounds[:2] < bounds[2:])


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

        if n is idx + 1:
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