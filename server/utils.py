import base64
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

import cv2
import numpy as np
from server.server_config import ServerConfig


def encode_mask(mask):
    encoded_mask = base64.b64encode(mask.tobytes(order='C'))
    return encoded_mask.decode('utf-8')


def decode_mask(b64_str, shape):
    mask_bytes = base64.b64decode(b64_str.encode("utf-8"))
    flat = np.fromstring(mask_bytes, bool)
    return np.reshape(flat, newshape=shape[:2], order='C')


def downscale_mat(mat, max_dim):
    new_dim = np.array(mat.shape[:2])
    long_dim = np.max(new_dim)
    scale = max_dim / long_dim

    if scale > 1.0:
        return mat

    new_dim = new_dim * scale
    new_dim = new_dim.astype(int)
    return cv2.resize(mat, tuple(reversed(new_dim)))


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


def save_mask(mask, filepath, resize_shape=None):
    folder = os.path.dirname(filepath)
    Path(folder).mkdir(parents=True, exist_ok=True)
    mask = mask.astype(np.uint8) * 255
    if resize_shape is not None:
        cv2.resize(mask, resize_shape[1::-1])
    cv2.imwrite(filepath, mask)


def save_info(shape, bbox, class_name, filepath, resize_shape=None):
    create_info_file(filepath)

    if resize_shape is not None:
        scale = resize_shape[0] / shape[0]
        shape = resize_shape
        bbox = np.array(bbox) * scale
        bbox = bbox.astype(int)

    root = ET.parse(filepath).getroot()

    obj = root.find('size')
    obj.find('width').text = str(shape[0])
    obj.find('height').text = str(shape[1])
    obj.find('depth').text = str(shape[2])

    obj = root.find('object')
    obj.find("name").text = class_name

    obj.find("bndbox/xmin").text = str(bbox[0])
    obj.find("bndbox/ymin").text = str(bbox[1])
    obj.find("bndbox/xmax").text = str(bbox[2])
    obj.find("bndbox/ymax").text = str(bbox[3])


    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
    xmlstr = os.linesep.join([s for s in xmlstr.splitlines() if s.strip()])
    with open(filepath, 'w') as f:
        f.write(xmlstr)


def load_info(filepath):
    root = ET.parse(filepath).getroot()
    obj = root.find('size')
    width = int(obj.find("width").text)
    height = int(obj.find("height").text)
    depth = int(obj.find("depth").text)

    obj = root.find('object')
    class_name = obj.find("name").text

    xmin = int(obj.find("bndbox/xmin").text)
    ymin = int(obj.find("bndbox/ymin").text)
    xmax = int(obj.find("bndbox/xmax").text)
    ymax = int(obj.find("bndbox/ymax").text)

    info = {
        "bbox": (xmin, ymin, xmax, ymax),
        "source_shape": (width, height, depth),
        "class_name": class_name
    }
    return info


def resize_info(info, shape):
    if info["source_shape"] == shape:
        return info

    scale = shape[0] / info["source_shape"][0]
    new_bbox = np.array(info["bbox"]) * scale

    info["source_shape"] = shape
    info["bbox"] = tuple(new_bbox.astype(int))
    return info


def create_info_file(filepath):
    folder = os.path.dirname(filepath)
    Path(folder).mkdir(parents=True, exist_ok=True)
    with open(ServerConfig.XML_TEMPLATE_PATH) as f_in:
        with open(filepath, "w") as f_out:
            for line in f_in:
                f_out.write(line)