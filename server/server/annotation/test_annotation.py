import pytest

from server.test import client, build_project_image_annotation, project_and_image


@pytest.fixture(scope='function')
def project_image_annotation():
    project, image, annotation = build_project_image_annotation()
    yield project, image, annotation
    # TODO cleanup


def test_get_one(client, project_image_annotation):
    project, image, annotation = project_image_annotation
    response = client.get(f'/projects/{project.id}/images/{image.id}/annotations/{annotation.id}')
    assert response.status_code == 200
    assert response.json.get('id') == annotation.id
    assert response.json.get('coco') == annotation.coco


def test_create_one(client, project_and_image):
    project, image = project_and_image
    annotation = {
        'annotations': [
            {
                "segmentation": [[510.66, 423.01, 511.72, 420.03, 510.45, 423.01]],
                "area": 702.1057499999998,
                "iscrowd": 0,
                "image_id": 289343,
                "bbox": [473.07, 395.93, 38.65, 28.67],
                "category_id": 18,
                "id": 1768
            }
        ]
    }
    params = dict(coco=annotation)
    response = client.post(f'/projects/{project.id}/images/{image.id}/annotations', json=params)
    assert response.status_code == 201
    assert response.json.items() >= params.items()
    assert response.json.get('id') is not None


# TODO test update one