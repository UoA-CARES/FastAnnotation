import pytest

from server import db
from server.project.project import Project

from server.image.image import Image
from server.test import client, project, build_project_and_image, project_and_image





def test_get_one(client, project_and_image):
    print(project_and_image)
    project, image = project_and_image
    response = client.get(f'/projects/{project.id}/images/{image.id}')
    assert response.status_code == 200
    data = response.json
    assert data.get('path') == image.path
    assert data.get('id') == image.id


def test_get_one_not_found(client, project_and_image):
    assert Image.query.get(0) is None, "Test precondition failed. There should be no image with id of 0 in the " \
                                          "DB. Was this manually added? "
    project, image = project_and_image
    response = client.get(f'/projects/{project.id}/images/0')
    assert response.status_code == 404


def test_create(client, project):
    params = dict(path="snap/crackle")
    project_id = project.id
    post_response = client.post(f'/projects/{project.id}/images', json=params)
    assert post_response.status_code == 201
    image = post_response.json
    assert params.items() <= image.items()

    get_response = client.get(f"/projects/{project_id}/images/{image.get('id')}")
    assert get_response.status_code == 200
    assert get_response.json.items() == image.items()


