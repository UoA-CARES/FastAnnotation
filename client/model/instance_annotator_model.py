from threading import Lock
from copy import deepcopy


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
            self._list = []


class BlockingCache:
    _lock = Lock()

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
        with self._lock:
            return deepcopy(self._cache.get(key, None))

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
                 image=None,
                 annotations=None):
        self.id = id
        self.name = name
        self.is_open = is_open
        self.is_locked = is_locked

        # State for opened images, should be none if unopened
        self.image = image
        self.shape = (0, 0, 0)  # (width, height, depth)
        self.annotations = annotations


class AnnotationState:
    """
    State associated with an annotation
    """

    def __init__(self, annotation_name, class_name, mask, bbox):
        self.annotation_name = annotation_name
        self.class_name = class_name
        self.mask = mask  # binary bool matrix
        self.bbox = bbox  # (x1, x2, w, h)


class LabelCache(BlockingCache):
    """
    A thread-safe cache of class labels used by the Instance Annotator
    """


class LabelState:
    """
    State associated with a class label
    """

    def __init__(self, name, color):
        self.name = name
        self.color = color  # (r,g,b)
