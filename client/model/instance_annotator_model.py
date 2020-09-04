import uuid
from copy import deepcopy
from threading import Lock, RLock

import numpy as np


class BlockItem:
    def __init__(self, parent, key):
        self.parent = parent
        self.key = key

    def __enter__(self):
        self.parent._lock.acquire()
        return self.parent._cache.get(self.key, None)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.parent._lock.release()


class BlockingList:
    _lock = Lock()

    def __init__(self):
        self._list = []

    def copy(self):
        with self._lock:
            return deepcopy(self._list)

    def contains(self, value):
        with self._lock:
            return value in self._list

    def append(self, value):
        with self._lock:
            self._list.append(value)

    def get(self, index):
        with self._lock:
            return deepcopy(self._list[index])

    def remove(self, value):
        with self._lock:
            self._list.remove(value)

    def clear(self):
        with self._lock:
            self._list.clear()


class BlockingCache:
    _lock = RLock()

    def __init__(self):
        self._cache = {}

    def keys(self):
        with self._lock:
            return list(self._cache.keys())

    def contains(self, key):
        with self._lock:
            return key in self._cache

    def add(self, key, obj):
        with self._lock:
            self._cache[key] = obj

    def get(self, key):
        return BlockItem(self, key)

    def delete(self, key):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache = {}


class InstanceAnnotatorModel:
    """
    A model representation of the data used in the Instance Annotator Screen
    """

    def __init__(self):
        self.images = ImageCache()
        self.labels = LabelCache()
        self.active = ActiveImages()
        self.tool = ToolState()


class ToolState:
    """
    A thread-safe object containing state related to the Instance Annotator Tool
    """

    PEN_SIZE_KEY = "pen_size"
    ALPHA_KEY = "alpha"
    CURRENT_IMAGE_KEY = "current_iid"
    CURRENT_LABEL_KEY = "current_label"
    CURRENT_LAYER_KEY = "current_layer"

    def __init__(
            self,
            pen_size=1,
            alpha=0.0,
            current_image_id=-1,
            current_label_name="",
            current_layer_name=""):
        self._cache = BlockingCache()
        self._cache.add(self.PEN_SIZE_KEY, pen_size)
        self._cache.add(self.ALPHA_KEY, alpha)
        self._cache.add(self.CURRENT_IMAGE_KEY, current_image_id)
        self._cache.add(self.CURRENT_LABEL_KEY, current_label_name)
        self._cache.add(self.CURRENT_LAYER_KEY, current_layer_name)

    def get_pen_size(self):
        with self._cache.get(self.PEN_SIZE_KEY) as value:
            return value

    def set_pen_size(self, value):
        self._cache.add(self.PEN_SIZE_KEY, value)

    def get_alpha(self):
        with self._cache.get(self.ALPHA_KEY) as value:
            return value

    def set_alpha(self, value):
        self._cache.add(self.ALPHA_KEY, value)

    def get_current_image_id(self):
        with self._cache.get(self.CURRENT_IMAGE_KEY) as iid:
            return iid

    def set_current_image_id(self, value):
        self._cache.add(self.CURRENT_IMAGE_KEY, value)

    def get_current_label_name(self):
        with self._cache.get(self.CURRENT_LABEL_KEY) as label:
            return label

    def set_current_label_name(self, value):
        self._cache.add(self.CURRENT_LABEL_KEY, value)

    def get_current_layer_name(self):
        with self._cache.get(self.CURRENT_LAYER_KEY) as layer:
            return layer

    def set_current_layer_name(self, value):
        self._cache.add(self.CURRENT_LAYER_KEY, value)


class ActiveImages(BlockingList):
    """
    A list of active ids associated to images currently in use by the Instance Annotator
    """


class ImageCache(BlockingCache):
    """
    A thread-safe cache of images that can be annotated by the Instance Annotator
    """

    def is_open(self, image_id):
        with self._lock:
            if image_id in self._cache:
                return self._cache[image_id].is_open
            return False


class ImageState:
    """
    State associated with an image
    """

    def __init__(self,
                 id=0,
                 name="",
                 is_open=False,
                 is_locked=False,
                 is_labeled=False,
                 unsaved=False,
                 image=None,
                 annotations=None):
        self.id = id
        self.name = name
        self.unsaved = unsaved
        self.is_open = is_open
        self.is_locked = is_locked
        self.is_labeled = is_labeled

        # State for opened images, should be none if unopened
        self.image = image
        self.shape = (0, 0, 0)  # (width, height, depth)
        self.annotations = annotations

    def get_unique_annotation_name(self):
        name = uuid.uuid1().hex
        return str(name)

    def detect_collisions(self, pos):
        collisions = []
        for annotation in self.annotations.values():
            if annotation.collision(pos):
                collisions.append(annotation)
        return collisions


class AnnotationState:
    """
    State associated with an annotation
    """

    def __init__(
            self,
            annotation_name,
            class_name,
            mat,
            bbox,
            mask_enabled=True,
            bbox_enabled=True):
        self.annotation_name = annotation_name
        self.class_name = class_name
        self.mat = mat  # A RGB mat with 1,1,1 at labeled locations and 0,0,0 otherwise
        self.bbox = bbox  # (x1, y1, w, h)
        self.mask_enabled = mask_enabled
        self.bbox_enabled = bbox_enabled

    def collision(self, pos):
        """
        Detects whether a point collides with this annotations bounding box
        :param pos:  position in the form (x,y)
        :return True if collision occurs, False otherwise:
        """
        bl = np.array(self.bbox[:2])
        tr = bl + np.array(self.bbox[2:])
        return np.all(np.logical_and(bl < pos, pos < tr))


class LabelCache(BlockingCache):
    """
    A thread-safe cache of class labels used by the Instance Annotator
    """

    BG_CLASS = "BG"

    def get_class_name(self, color):
        with self._lock:
            for k in self._cache.keys():
                if np.all(self._cache[k].get_rgb() == color):
                    return k
        return None

    def get_default_name(self):
        with self._lock:
            k = None
            for k in self._cache.keys():
                if k is self.BG_CLASS:
                    continue
                break
            return k


class LabelState:
    """
    State associated with a class label
    """

    def __init__(self, name, color):
        self.name = name
        self.color = (np.array(color) / 255).tolist()

    def get_rgb(self):
        return np.clip(np.array(self.color) * 255, 0, 255).astype(np.uint8)[:3]
