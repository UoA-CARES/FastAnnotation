import numpy as np
import client.utils as utils
from client.utils import ApiException

from client.model.instance_annotator_model import ImageState, AnnotationState, LabelState


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

        resp = utils.get_image_metas_by_ids(result["ids"])
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

        image_model = self.model.images.get(image_id)
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
        img_bytes = utils.decode_image(result["image_data"])
        image_model.id = result["id"]
        image_model.name = result["name"]
        image_model.is_locked = result["is_locked"]
        image_model.image = utils.bytes2mat(img_bytes)
        image_model.shape = image_model.image.shape

        resp = utils.get_image_annotation(image_id)
        if resp.status_code != 200:
            raise ApiException(
                "Failed to retrieve annotations for the image with id %d." %
                image_id, resp.status_code)

        result = resp.json()
        annotations = []
        i = 0
        for row in result["annotations"]:
            # TODO: Add actual annotation names to database
            annotation_name = "PLACEHOLDER %d" % i
            class_name = row["class_name"]
            mask = utils.decode_mask(row["mask_data"], row["shape"][:2])
            bbox = row["bbox"]
            bbox[2] = bbox[2] - bbox[0]
            bbox[3] = bbox[3] - bbox[1]
            annotations.append(AnnotationState(annotation_name=annotation_name,
                                               class_name=class_name,
                                               mask=mask,
                                               bbox=bbox))
            i += 1

        image_model.annotations = annotations
        self.model.images.add(image_id, image_model)

    def fetch_class_labels(self, project_id):
        """
        Fetch the class labels for this project.
        :param project_id: The ID for this project.
        :return:
        """

        # TODO: These arent stored in the database yet

        data = [
            LabelState("Trunk", [120, 80, 0]),
            LabelState("Cane", [150, 250, 0]),
            LabelState("Shoot", [0, 130, 200]),
            LabelState("Node", [255, 100, 190]),
            LabelState("Wire", [255, 128, 0]),
            LabelState("Post", [128, 128, 0])
        ]

        for label in data:
            self.model.labels.add(label.name, label)

    def open_image(self, image_id):
        """
        Add a fully loaded image to the active open images.
        :param image_id: The ID of a valid image
        :return:
        """

        image_model = self.model.images.get(image_id)

        if not image_model or not image_model.image:
            self.fetch_image(image_id)

        if not self.model.active.contains(image_id):
            self.model.active.append(image_id)

    def save_image(self, image_canvas):
        """
        Save the changes from the image_canvas to the model and reflect these changes back to the server.
        :param image_canvas: The ImageCanvas object
        :return:
        """

        iid = image_canvas.image_id
        image_model = self.model.images.get(iid)

        if not image_model:
            raise ValueError(
                "Image Canvas points to image id %d, which is not valid." %
                iid)

        # Build annotations
        annotations = []
        i = 0
        for layer in image_canvas.layer_stack.layer_list:
            annotation_name = "PLACEHOLDER %d" % i
            mask = utils.texture2mat(layer.get_fbo().texture)
            mask = np.all(mask.astype(bool), axis=2)

            annotation = AnnotationState(annotation_name=annotation_name,
                                         class_name=layer.class_name,
                                         mask=mask,
                                         bbox=layer.bbox_bounds)
            annotations.append(annotation)
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

        self.model.images.add(iid, image_model)

