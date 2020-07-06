import numpy as np

import client.utils as utils
from client.model.instance_annotator_model import ImageState, AnnotationState, LabelState
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

        resp = utils.get_images_by_ids(result["ids"], image_data=False)
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

            resp = utils.get_image_by_id(image_id, max_dim=ClientConfig.EDITOR_MAX_DIM)
            if resp.status_code == 404:
                raise ApiException(
                    "Image does not exist with id %d." %
                    image_id, resp.status_code)
            elif resp.status_code != 200:
                raise ApiException(
                    "Failed to retrieve image with id %d." %
                    image_id, resp.status_code)

            result = resp.json()
            img_bytes = utils.decode_image(result["image_data"])
            image_model.id = result["id"]
            image_model.name = result["name"]
            image_model.is_locked = result["is_locked"]
            image_model.image = utils.bytes2mat(img_bytes)
            image_model.shape = image_model.image.shape

            resp = utils.get_image_annotation(image_id, max_dim=ClientConfig.EDITOR_MAX_DIM)
            if resp.status_code != 200:
                raise ApiException(
                    "Failed to retrieve annotations for the image with id %d." %
                    image_id, resp.status_code)

            result = resp.json()
            annotations = {}
            i = 0
            for row in result["annotations"]:
                # TODO: Add actual annotation names to database
                annotation_name = row["name"]
                class_name = row["class_name"]
                mask = utils.decode_mask(row["mask_data"], row["shape"][:2])

                bbox = row["bbox"]
                print("CLIENT: incoming bbox")
                print("\t%s" % str(bbox))

                annotations[annotation_name] = AnnotationState(
                    annotation_name=annotation_name,
                    class_name=class_name,
                    mat=utils.mask2mat(mask),
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

        # TODO: These arent stored in the database yet

        data = [
            LabelState("Trunk", [120, 80, 1, 255]),
            LabelState("Cane", [150, 250, 1, 255]),
            LabelState("Shoot", [1, 130, 200, 255]),
            LabelState("Node", [255, 100, 190, 255]),
            LabelState("Wire", [255, 128, 1, 255]),
            LabelState("Post", [128, 128, 1, 255])
        ]

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
                self.fetch_image(image_id) #MEM: 9.0 -> 10.7 (+1.7GB)

        if not self.model.images.contains(image_id):
            return

        if not self.model.active.contains(image_id):
            self.model.active.append(image_id)
            print(self.model.active._list)

        self.model.tool.set_current_image_id(image_id)

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
            for layer in image_canvas.layer_stack.get_all_layers():
                annotation_name = layer.layer_name
                mask = layer.mask

                print("CLIENT: outgoing bbox")
                print("\t%s" % str(layer.bbox_bounds))

                annotation = AnnotationState(annotation_name=annotation_name,
                                             class_name=layer.class_name,
                                             mat=utils.mask2mat(mask),
                                             bbox=layer.bbox_bounds)
                annotations[annotation_name] = annotation
                i += 1

            image_model.annotations = annotations

            resp = utils.add_image_annotation(iid, image_model.annotations)
            if resp.status_code == 200:
                result = resp.json()
                errors = []
                for row in result["results"]:
                    errors.append(row["error"]["message"])
                errors = '\n'.join(errors)
                msg = "The following errors occurred while saving annotations to the image with id %d:\n" % iid
                msg += errors
                raise ApiException(message=msg, code=resp.status_code)
            elif resp.status_code != 201:
                msg = "Failed to save annotations to the image with id %d." % iid
                raise ApiException(message=msg, code=resp.status_code)

            resp = utils.update_image_meta_by_id(iid, lock=False)
            if resp.status_code != 200:
                msg = "Failed to unlock the image with id %d." % iid
                raise ApiException(message=msg, code=resp.status_code)

            image_model.is_locked = False
            image_model.unsaved = False

            self.model.images.add(iid, image_model)

    def update_tool_state(self,
                          pen_size=None,
                          alpha=None,
                          eraser=None,
                          current_iid=None,
                          current_label=None,
                          current_layer=None):
        if pen_size is not None:
            self.model.tool.set_pen_size(pen_size)
        if alpha is not None:
            self.model.tool.set_alpha(alpha)
        if eraser is not None:
            self.model.tool.set_eraser(eraser)
        if current_iid is not None:
            self.model.tool.set_current_image_id(current_iid)
        if current_layer is not None:
            self.model.tool.set_current_layer_name(current_layer)
            # If current layer changes update current_label aswell
            iid = self.model.tool.get_current_image_id()
            with self.model.images.get(iid) as img:
                if img is not None:
                    annotation = img.annotations.get(current_layer, None)
                    if annotation is not None:
                        self.model.tool.set_current_label_name(annotation.class_name)
        if current_label is not None:
            self.model.tool.set_current_label_name(current_label)

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
            iid,
            is_locked=None,
            is_open=None,
            unsaved=None):

        with self.model.images.get(iid) as image:
            if image is None:
                return

            if is_locked is not None:
                image.is_locked = is_locked

            if is_open is not None:
                image.is_open = is_open

            if unsaved is not None:
                print("Controller: Marking as unsaved")
                image.unsaved = unsaved

            self.model.images.add(iid, image)

    def add_blank_layer(self, iid):
        with self.model.images.get(iid) as img:
            layer_name = img.get_unique_annotation_name()
            class_name = self.model.tool.get_current_label_name()
            mask = np.zeros(shape=img.shape, dtype=np.uint8)
            bbox = (0, 0, 0, 0)
            annotation = AnnotationState(layer_name, class_name, mask, bbox)
            img.annotations[layer_name] = annotation
            img.unsaved = True
            self.model.images.add(iid, img)
            self.model.tool.set_current_layer_name(layer_name)
            print("Controller: Adding blank layer (%s)" % layer_name)

    def delete_layer(self, iid, layer_name):
        with self.model.images.get(iid) as img:
            img.annotations.pop(layer_name, None)
            img.unsaved = True
            self.model.images.add(iid, img)
            if self.model.tool.get_current_layer_name() is layer_name:
                self.model.tool.set_current_layer_name(None)
            print("Controller: Deleting layer (%s)" % layer_name)
