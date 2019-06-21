# Copyright 2019 CEA
# Author: Yann Leprince <yann.leprince@cea.fr>
#
# This file is part of cortical-voluba.
#
# cortical-voluba is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# cortical-voluba is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with cortical-voluba. If not, see <https://www.gnu.org/licenses/>.

import copy

import celery.app.base
import celery.result
import pytest
import requests


@pytest.fixture(autouse=True)
def prevent_async_celery(monkeypatch):
    # Prevent the Celery task from being actually called
    def mock_send_task(self, task_name, *args, **kwargs):
        return celery.result.AsyncResult('dummy_id_for_' + task_name)
    monkeypatch.setattr(celery.app.base.Celery, 'send_task', mock_send_task)


DUMMY_IMAGE_LIST = [
    {
        "extra": {
            "data": {},
            "fileName": "seg.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {
                "type": "segmentation",
            },
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/seg",
        },
        "name": "seg",
        "visibility": "private",
    },
    {
        "extra": {
            "data": {},
            "fileName": "image.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {
                "type": "image",
            },
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/img",
        },
        "name": "img",
        "visibility": "private",
    },
    {
        "extra": {
            "data": {},
            "fileName": "depth_map.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {
                "type": "image",
            },
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/depthmap",
        },
        "name": "depthmap",
        "visibility": "private",
    },
]


def test_create_depth_map_computation(flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Well-behaved request
    response = flask_client.post(
        '/v0/depth-map-computation/',
        headers={'Authorization': 'Bearer test'},
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'seg',
        },)
    assert response.status_code == 202
    assert 'status_polling_url' in response.json


def test_create_depth_map_computation_request_errors(
        flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Malformed request errors
    response = flask_client.post('/v0/depth-map-computation/')
    assert response.status_code == 400
    assert 'errors' in response.json
    response = flask_client.post('/v0/depth-map-computation/',
                                 json={})
    assert response.status_code == 400
    assert 'errors' in response.json

    # Unauthenticated request error
    response = flask_client.post(
        '/v0/depth-map-computation/',
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'seg',
        })
    assert response.status_code == 401
    assert 'errors' in response.json


def test_create_depth_map_computation_image_errors(
        flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Incorrect image referenced on the image service
    response = flask_client.post(
        '/v0/depth-map-computation/',
        headers={'Authorization': 'Bearer test'},
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'nonexistent',
        },)
    assert response.status_code == 400
    assert 'errors' in response.json

    response = flask_client.post(
        '/v0/depth-map-computation/',
        headers={'Authorization': 'Bearer test'},
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'img',
        },)
    assert response.status_code == 400
    assert 'errors' in response.json


def test_create_depth_map_computation_image_service_errors(
        flask_client, requests_mock):
    # Forwarding of image service errors to the client
    requests_mock.get('http://h.test/b/list', status_code=401)

    response = flask_client.post(
        '/v0/depth-map-computation/',
        headers={'Authorization': 'Bearer wrong'},
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'seg',
        },)
    assert response.status_code == 401
    assert 'errors' in response.json

    requests_mock.get('http://h.test/b/list', status_code=404)
    response = flask_client.post(
        '/v0/depth-map-computation/',
        headers={'Authorization': 'Bearer dummy'},
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'seg',
        },)
    assert response.status_code == 500
    assert 'errors' in response.json

    requests_mock.get('http://h.test/b/list', exc=requests.ConnectionError)
    response = flask_client.post(
        '/v0/depth-map-computation/',
        headers={'Authorization': 'Bearer dummy'},
        json={
            'image_service_base_url': 'http://h.test/b/',
            'segmentation_name': 'seg',
        },)
    assert response.status_code == 500
    assert 'errors' in response.json


TEST_ALIGNMENT_REQUEST = {
    'image_service_base_url': 'http://h.test/b/',
    'image_name': 'img',
    'depth_map_name': 'depthmap',
    'transformation_matrix': [[1, 0, 0, 0],
                              [0, 1.1, 0, -2],
                              [0, 0, 0.9, 0],
                              [0, 0, 0, 1]],
    'landmark_pairs': [
        {
            'source_point': [0, 0, 0],
            'target_point': [1, 1, 1],
            'name': 'toto',
            'active': True,
            'colour': '#012345',
        },
        {
            'source_point': [-1, -2, -3.5],
            'target_point': [0, 0, 1.5],
        },
    ],
}


def test_create_alignment_computation(flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Well-behaved request
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer test'},
        json=TEST_ALIGNMENT_REQUEST)
    assert response.status_code == 202
    assert 'status_polling_url' in response.json


def test_create_alignment_computation_request_errors(
        flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Malformed request errors
    response = flask_client.post('/v0/alignment-computation/')
    assert response.status_code == 400
    assert 'errors' in response.json
    response = flask_client.post('/v0/alignment-computation/',
                                 json={})
    assert response.status_code == 400
    assert 'errors' in response.json

    # Unauthenticated request error
    response = flask_client.post(
        '/v0/alignment-computation/',
        json=TEST_ALIGNMENT_REQUEST)
    assert response.status_code == 401
    assert 'errors' in response.json


def test_create_alignment_computation_image_errors(
        flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Incorrect image referenced on the image service
    erroneous_request = copy.deepcopy(TEST_ALIGNMENT_REQUEST)
    erroneous_request['image_name'] = 'nonexistent'
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer test'},
        json=erroneous_request)
    assert response.status_code == 400
    assert 'errors' in response.json

    erroneous_request = copy.deepcopy(TEST_ALIGNMENT_REQUEST)
    erroneous_request['image_name'] = 'seg'
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer test'},
        json=erroneous_request)
    assert response.status_code == 400
    assert 'errors' in response.json

    erroneous_request = copy.deepcopy(TEST_ALIGNMENT_REQUEST)
    erroneous_request['depth_map_name'] = 'nonexistent'
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer test'},
        json=erroneous_request)
    assert response.status_code == 400
    assert 'errors' in response.json

    erroneous_request = copy.deepcopy(TEST_ALIGNMENT_REQUEST)
    erroneous_request['depth_map_name'] = 'seg'
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer test'},
        json=erroneous_request)
    assert response.status_code == 400
    assert 'errors' in response.json


def test_create_alignment_computation_image_service_errors(
        flask_client, requests_mock):
    # Forwarding of image service errors to the client
    requests_mock.get('http://h.test/b/list', status_code=401)

    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer wrong'},
        json=TEST_ALIGNMENT_REQUEST)
    assert response.status_code == 401
    assert 'errors' in response.json

    requests_mock.get('http://h.test/b/list', status_code=404)
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer dummy'},
        json=TEST_ALIGNMENT_REQUEST)
    assert response.status_code == 500
    assert 'errors' in response.json

    requests_mock.get('http://h.test/b/list', exc=requests.ConnectionError)
    response = flask_client.post(
        '/v0/alignment-computation/',
        headers={'Authorization': 'Bearer dummy'},
        json=TEST_ALIGNMENT_REQUEST)
    assert response.status_code == 500
    assert 'errors' in response.json
