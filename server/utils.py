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


def save_mask(mask, filepath):
    folder = os.path.dirname(filepath)
    Path(folder).mkdir(parents=True, exist_ok=True)
    mask = mask.astype(np.uint8) * 255
    mask = cv2.flip(mask, 0)
    cv2.imwrite(filepath, mask)


def load_mask(filepath):
    mask = cv2.imread(filepath)
    mask = np.all(mask.astype(bool), axis=2)
    return mask


def save_info(info, filepath):
    create_info_file(filepath)

    root = ET.parse(filepath).getroot()

    shape = info["source_shape"]
    obj = root.find('size')
    obj.find('width').text = str(shape[0])
    obj.find('height').text = str(shape[1])
    obj.find('depth').text = str(shape[2])

    bbox = info["bbox"]
    obj = root.find('object')
    obj.find("name").text = info["class_name"]

    obj.find("bndbox/ymin").text = str(bbox[0])
    obj.find("bndbox/xmin").text = str(bbox[1])
    obj.find("bndbox/ymax").text = str(bbox[2])
    obj.find("bndbox/xmax").text = str(bbox[3])

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


def create_info_file(filepath):
    folder = os.path.dirname(filepath)
    Path(folder).mkdir(parents=True, exist_ok=True)
    with open(ServerConfig.XML_TEMPLATE_PATH) as f_in:
        with open(filepath, "w") as f_out:
            for line in f_in:
                f_out.write(line)