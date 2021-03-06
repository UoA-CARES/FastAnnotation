import cv2
import numpy as np
import time

import client.utils as utils
from client.model.instance_annotator_model import ImageState, AnnotationState, LabelState
from client.model.instance_annotator_model import LabelCache
from client.utils import ApiException, ClientConfig


class InstanceAnnotatorController:
    def __init__(self, model):
        self.model = model

    def fetch_image_metas(self, project_id, filter_details):
        """
        Fetch the meta information for all un-opened images in this project
        :param project_id: The ID for this project
        :param filter_details: A dict of filter params used to order the images
        :return:
        """
        resp = utils.get_project_images(project_id, filter_details)

        if resp.status_code != 200:
            raise ApiException(
                "Failed to retrieve project image ids.",
                resp.status_code)

        result = resp.json()

        resp = utils.get_images_by_ids(result["ids"])
        if resp.status_code != 200:
            raise ApiException(
                "Failed to retrieve image meta information.",
                resp.status_code)

        result = resp.json()
        for row in result["images"]:
            if self.model.images.is_open(row["id"]):
                continue

            state = ImageState(id=row["id"],
                               name=row["name"],
                               is_locked=row["is_locked"],
                               is_open=False)
            self.model.images.add(row["id"], state)

    def fetch_image(self, image_id):
        """
        Fetch the image and annotation data for this image.
        :param image_id: The ID for this image.
        :return:
        """

        with self.model.images.get(image_id) as image_model:
            if not image_model:
                image_model = ImageState()

            resp = utils.update_image_meta_by_id(image_id, lock=True)
            if resp.status_code != 200:
                raise ApiException(
                    "Failed to lock image with id %d" %
                    image_id, resp.status_code)

            resp = utils.get_image_by_id(image_id)
            if resp.status_code == 404:
                raise ApiException(
                    "Image does not exist with id %d." %
                    image_id, resp.status_code)
            elif resp.status_code != 200:
                raise ApiException(
                    "Failed to retrieve image with id %d." %
                    image_id, resp.status_code)

            result = resp.json()

            image_model.id = result["id"]
            image_model.name = result["name"]
            image_model.is_locked = result["is_locked"]

            image_model.image = utils.download_image(image_id)
            image_model.shape = image_model.image.shape

            resp = utils.get_image_annotation(image_id)
            if resp.status_code != 200:
                raise ApiException(
                    "Failed to retrieve annotations for the image with id %d." %
                    image_id, resp.status_code)

            result = resp.json()
            annotations = {}
            i = 0
            try:
                mask_dict = utils.download_annotations(image_id)
            except ApiException:
                pass
            else:
                for row in result["annotations"]:
                    # TODO: Add actual annotation names to database
                    annotation_name = row["name"]
                    class_name = row["class_name"]
                    mat = mask_dict.get(row["id"], None)
                    if mat is None:
                        raise ApiException("Failed to download annotation with id %d." % row["id"], resp.status_code)

                    bbox = row["bbox"]
                    print("CLIENT: incoming bbox")
                    print("\t%s" % str(bbox))

                    annotations[annotation_name] = AnnotationState(
                        annotation_name=annotation_name,
                        class_name=class_name,
                        mat=mat,
                        bbox=bbox)

                    i += 1
            image_model.annotations = annotations
            self.model.images.add(image_id, image_model)

    def fetch_class_labels(self, project_id):
        """
        Fetch the class labels for this project.
        :param project_id: The ID for this project.
        :return:
        """
        print("Fetching Class Labels")

        # TODO: These labels are project specific and should be editable by the user and stored in the database.

        data = [LabelState(LabelCache.BG_CLASS, [0, 0, 0, 255])]
        resp = utils.get_project_labels(project_id)
        for label in resp.json()["labels"]:
            data.append(LabelState(label["name"], [label["r"], label["g"], label["b"], 255]))

        for label in data:
            self.model.labels.add(label.name, label)

    def open_image(self, image_id):
        """
        Add a fully loaded image to the active open images.
        :param image_id: The ID of a valid image
        :return:
        """

        with self.model.images.get(image_id) as image_model:
            if image_model is None or image_model.image is None:
                self.fetch_image(image_id)  # MEM: 9.0 -> 10.7 (+1.7GB)

        if not self.model.images.contains(image_id):
            return

        if not self.model.active.contains(image_id):
            self.model.active.append(image_id)
            print(self.model.active._list)

        self.model.tool.set_current_image_id(image_id)
        self.model.tool.set_current_layer_name(None)

    def save_image(self, image_canvas):
        """
        Save the changes from the image_canvas to the model and reflect these changes back to the server.

        NOTE: Ensure the ImageCanvas has run prepare_to_save() on the mainthread before running this operation
        :param image_canvas: The ImageCanvas object
        :return:
        """

        iid = image_canvas.image_id
        with self.model.images.get(iid) as image_model:
            if image_model is None:
                raise ValueError(
                    "Image Canvas points to image id %d, which is not valid." %
                    iid)

            # Build annotations
            annotations = {}
            i = 0
            pw = image_canvas.painter.paint_window
            for name in pw.get_all_names():
                if not name:
                    continue
                box = pw.get_bound(name)
                mat = pw.get_mask(name).copy()
                color = pw.get_color(name)
                class_name = self.model.labels.get_class_name(color)
                if class_name is None:
                    class_name = self.model.labels.get_default_name()
                annotation = AnnotationState(annotation_name=name,
                                             class_name=class_name,
                                             mat=mat,
                                             bbox=box)
                annotations[name] = annotation
                print("CLIENT: outgoing bbox")
                print("\t%s" % str(box))

            image_model.annotations = annotations

            resp = utils.upload_annotations(iid, image_model.annotations)
            if resp.status_code != 201:
                msg = "Failed to save annotations to the image with id %d." % iid
                raise ApiException(message=msg, code=resp.status_code)

            resp = utils.update_image_meta_by_id(iid, lock=False, labeled=image_model.is_labeled)
            if resp.status_code != 200:
                msg = "Failed to unlock the image with id %d." % iid
                raise ApiException(message=msg, code=resp.status_code)

            self.model.images.add(iid, image_model)
            self.update_image_meta(iid, unsaved=False, is_locked=False)

    def update_tool_state(self,
                          pen_size=None,
                          alpha=None,
                          current_iid=None,
                          current_label='',
                          current_layer=''):
        if pen_size is not None:
            self.model.tool.set_pen_size(pen_size)
        if alpha is not None:
            self.model.tool.set_alpha(alpha)
        if current_iid is not None:
            self.model.tool.set_current_image_id(current_iid)
        if current_layer != '':
            self.model.tool.set_current_layer_name(current_layer)
            # If current layer changes update current_label aswell
            iid = self.model.tool.get_current_image_id()
            with self.model.images.get(iid) as img:
                if img is not None and img.annotations is not None:
                    annotation = img.annotations.get(current_layer, None)
                    if annotation is not None:
                        self.model.tool.set_current_label_name(
                            annotation.class_name)
        if current_label != '':
            self.model.tool.set_current_label_name(current_label)

    def load_annotations(self, iid=None, annotations=None):
        if iid is None:
            iid = self.model.tool.get_current_image_id()

        with self.model.images.get(iid) as image:
            if image is None or image.annotations is None:
                return
            image.annotations = annotations
            self.model.images.add(iid, image)

    def update_annotation(
            self,
            iid=None,
            layer_name=None,
            bbox=None,
            texture=None,
            label_name=None,
            mask_enabled=None,
            bbox_enabled=None):
        # Populate iid and layer_name with current values if None
        if iid is None:
            iid = self.model.tool.get_current_image_id()
        if layer_name is None:
            layer_name = self.model.tool.get_current_layer_name()

        with self.model.images.get(iid) as image:
            if image is None or image.annotations is None:
                return
            annotation = image.annotations.get(layer_name, None)
            if annotation is None:
                return

            if bbox is not None:
                annotation.bbox = bbox

            if texture is not None:
                annotation.mat = utils.texture2mat(texture)

            if label_name is not None:
                annotation.class_name = label_name

            if mask_enabled is not None:
                annotation.mask_enabled = bool(mask_enabled)

            if bbox_enabled is not None:
                annotation.bbox_enabled = bool(bbox_enabled)

            image.annotations[layer_name] = annotation
            self.model.images.add(iid, image)

    def update_image_meta(
            self,
            iid=None,
            is_locked=None,
            is_labeled=None,
            is_open=None,
            unsaved=None):

        diff = False

        if iid is None:
            iid = self.model.tool.get_current_image_id()

        with self.model.images.get(iid) as image:
            if image is None:
                return

            if is_locked is not None:
                diff = diff or image.is_locked is not is_locked
                image.is_locked = is_locked

            if is_labeled is not None:
                diff = diff or image.is_labeled is not is_labeled
                image.is_labeled = is_labeled

            if is_open is not None:
                image.is_open = is_open

            if unsaved is not None:
                print("Controller: Marking as unsaved")
                image.unsaved = unsaved

            self.model.images.add(iid, image)

            if diff:
                resp = utils.update_image_meta_by_id(iid, lock=image.is_locked, labeled=image.is_labeled)
                if resp.status_code != 200:
                    raise ApiException(
                        "Failed to update image with id %d" %
                        iid, resp.status_code)

    def add_blank_layer(self, iid):
        with self.model.images.get(iid) as img:
            layer_name = img.get_unique_annotation_name()
            class_name = self.model.tool.get_current_label_name()
            mask = np.zeros(shape=img.shape, dtype=np.uint8)
            bbox = (0, 0, 0, 0)
            annotation = AnnotationState(layer_name, class_name, mask, bbox)
            img.annotations[layer_name] = annotation
            self.model.images.add(iid, img)
            self.model.tool.set_current_layer_name(layer_name)
            print("Controller: Adding blank layer (%s)" % layer_name)
        self.update_image_meta(iid, unsaved=True)

    def delete_layer(self, iid, layer_name):
        with self.model.images.get(iid) as img:
            img.annotations.pop(layer_name, None)
            self.model.images.add(iid, img)
            if self.model.tool.get_current_layer_name() is layer_name:
                self.model.tool.set_current_layer_name(None)
            print("Controller: Deleting layer (%s)" % layer_name)

        self.update_image_meta(iid, unsaved=True)
