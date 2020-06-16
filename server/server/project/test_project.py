from server.project.project import Project
from server.test import client, project

def test_get_one(client, project):
    response = client.get(f'/projects/{project.id}')
    assert response.status_code == 200


def test_get_one_not_found(client):
    # Project ids start at 1, so 0 should never be in the DB
    assert Project.query.get(0) is None, "Test precondition failed. There should be no project with id of 0 in the " \
                                          "DB. Was this manually added? "
    response = client.get('/projects/0')
    assert response.status_code == 404


def test_create(client):
    name = "foo"
    description = "This is a short description"
    response = client.post('/projects', json=dict(name=name, description=description))
    assert(response.status_code == 201)
    # Check that the project was actually created.

    project = Project.query.get(response.json['id'])
    assert project is not None
    assert project.name == name


def test_update(client, project):
    params = dict(name="This is an updated name", description="This is an updated description")
    put_response = client.put(f'/projects/{project.id}', json=params)
    assert put_response.status_code == 200
    # Check whether updated object is superset of the update params
    assert put_response.json.items() >= params.items()
    # Check that the project was actually updated
    get_response = client.get(f'/projects/{project.id}')
    assert get_response.status_code == 200
    assert put_response.json == get_response.json

