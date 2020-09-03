import cv2
import numpy as np
import io
import zipfile
from client.utils import mat2bytes
import requests
import json


def random_image(shape):
    rgb = np.zeros(shape=shape, dtype=np.uint8)
    rgb[:] = np.random.choice(range(256), size=3)
    return rgb


def upload_annotations(N, shape=(3000, 1500, 3)):
    url = "http://localhost:5001/files/image/0/annotations"

    data = io.BytesIO()
    ext = '.jpg'
    with zipfile.ZipFile(data, mode='w') as z:
        for i in range(10):
            img_bytes = mat2bytes(random_image(shape), ext)
            z.writestr(str(i) + ext, img_bytes)
    data.seek(0)
    payload = {"test": 123}

    return requests.post(url, files={'file': data, 'info': json.dumps(payload).encode('utf-8')})


if __name__ == '__main__':
    rgb = np.random.randint(255, size=(900, 800, 3), dtype=np.uint8)

    cv2.imwrite("test.png", rgb)
    test_rgb = cv2.imread("test.png")
    pass
