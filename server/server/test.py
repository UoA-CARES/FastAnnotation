import pytest

from server import app, db
from server.project.project import Project
from server.image.image import Image
from server.annotation.annotation import Annotation

# TODO: Some of these fixtures could go into a common test module
@pytest.fixture(scope='module')
def client():
    app.config['TESTING'] = True
    yield app.test_client()


@pytest.fixture(scope='function')
def project():
    """Provide a function-scoped project"""
    project = Project(name="test")
    db.session.add(project)
    db.session.commit()
    db.session.refresh(project)
    yield project

    # TODO clean up


@pytest.fixture(scope='function')
def project_and_image():
    """Provide a function-scoped project"""
    project, image = build_project_and_image()
    yield project, image

    # TODO Clean up


def build_project_and_image():
    project = Project(name="test")
    db.session.add(project)
    db.session.commit()
    db.session.refresh(project)
    image = Image(path='foo/bar', project=project)
    db.session.add(image)
    db.session.commit()
    db.session.refresh(image)
    return project, image


def build_project_image_annotation():
    project, image = build_project_and_image()
    # Example from https://www.immersivelimit.com/tutorials/create-coco-annotations-from-scratch/#coco-dataset-format
    annotations = {
        "annotations": [
            {
                "segmentation": [[510.66, 423.01, 511.72, 420.03, 510.45, 423.01]],
                "area": 702.1057499999998,
                "iscrowd": 0,
                "image_id": 289343,
                "bbox": [473.07, 395.93, 38.65, 28.67],
                "category_id": 18,
                "id": 1768
            },
            {
                "segmentation": {
                    "counts": [179, 27, 392, 41, 55, 20],
                    "size": [426, 640]
                },
                "area": 220834,
                "iscrowd": 1,
                "image_id": 250282,
                "bbox": [0, 34, 639, 388],
                "category_id": 1,
                "id": 900100250282
            }]
        }

    annotation = Annotation(project_id=project.id, image_id=image.id, coco=annotations)
    db.session.add(annotation)
    db.session.commit()
    db.session.refresh(annotation)
    return project, image, annotation
