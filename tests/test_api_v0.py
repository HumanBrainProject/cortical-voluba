# Copyright 2019-2020 CEA
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
import celery.backends.base
import celery.result
import pytest
import requests

from testdata import DUMMY_IMAGE_LIST


@pytest.fixture(autouse=True)
def prevent_async_celery(monkeypatch):
    class AsyncResultMock(celery.result.AsyncResult):
        def __init__(self, id, get_return_value, *args, **kwargs):
            super().__init__(id, *args, **kwargs)
            self._get_return_value = get_return_value

        def get(self, *args, **kwargs):
            return self._get_return_value

    get_return_value = None

    # Prevent the Celery task from being actually called
    def mock_send_task(self, task_name, *args, **kwargs):
        return AsyncResultMock('dummy_id_for_' + task_name, get_return_value)
    monkeypatch.setattr(celery.app.base.Celery, 'send_task', mock_send_task)

    class ResultMocker:
        def set_get_return_value(self, return_value):
            nonlocal get_return_value
            get_return_value = return_value

    return ResultMocker()


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
    assert 'dummy_id_for_' in response.json['status_polling_url']


def test_create_depth_map_computation_request_errors(
        flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Malformed request errors
    response = flask_client.post('/v0/depth-map-computation/')
    assert response.status_code == 422
    assert 'errors' in response.json
    response = flask_client.post('/v0/depth-map-computation/',
                                 json={})
    assert response.status_code == 422
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
    assert 'dummy_id_for_' in response.json['status_polling_url']


def test_create_alignment_computation_request_errors(
        flask_client, requests_mock):
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)

    # Malformed request errors
    response = flask_client.post('/v0/alignment-computation/')
    assert response.status_code == 422
    assert 'errors' in response.json
    response = flask_client.post('/v0/alignment-computation/',
                                 json={})
    assert response.status_code == 422
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


class MockBackend(celery.backends.base.KeyValueStoreBackend):
    persistent = False

    def __init__(self, *args, **kwargs):
        self._store = {}
        super().__init__(*args, **kwargs)

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value):
        self._store[key] = value

    def delete(self, key):
        del self._store[key]


@pytest.mark.parametrize('computation_type', ['depth-map', 'alignment'])
def test_computation_status(monkeypatch, flask_client, computation_type):
    from cortical_voluba.celery import celery_app
    mock_backend = MockBackend(celery_app)
    monkeypatch.setattr(celery_app, 'backend', mock_backend)
    endpoint_url = '/v0/{0}-computation/dummy_id'.format(computation_type)

    # Task in PENDING state
    response = flask_client.get(endpoint_url)
    assert response.status_code == 200
    assert response.json['finished'] is False
    assert 'message' in response.json
    assert 'error' not in response.json
    assert 'results' not in response.json

    mock_backend.mark_as_started('dummy_id')
    response = flask_client.get(endpoint_url)
    assert response.status_code == 200
    assert response.json['finished'] is False
    assert 'message' in response.json
    assert 'error' not in response.json
    assert 'results' not in response.json

    mock_backend.store_result('dummy_id', {
        'message': 'toto',
    }, 'PROGRESS')
    response = flask_client.get(endpoint_url)
    assert response.status_code == 200
    assert response.json['finished'] is False
    assert 'toto' in response.json['message']
    assert 'error' not in response.json
    assert 'results' not in response.json

    mock_backend.mark_as_retry('dummy_id', None)
    response = flask_client.get(endpoint_url)
    assert response.status_code == 200
    assert response.json['finished'] is False
    assert 'message' in response.json
    assert 'error' not in response.json
    assert 'results' not in response.json

    mock_backend.mark_as_done('dummy_id', {
        'message': 'success',
        'results': 'placeholder',
    })
    response = flask_client.get(endpoint_url)
    assert response.status_code == 200
    assert response.json['finished'] is True
    assert 'message' in response.json
    assert response.json['results'] == 'placeholder'
    assert 'error' not in response.json

    mock_backend.mark_as_failure('dummy_id', Exception('toto'))
    response = flask_client.get(endpoint_url)
    assert response.status_code == 200
    assert response.json['finished'] is True
    assert 'message' in response.json
    assert response.json['error'] is True
    assert 'results' not in response.json


def test_worker_health(flask_client, prevent_async_celery):
    prevent_async_celery.set_get_return_value(True)
    response = flask_client.get('/v0/worker-health')
    assert response.status_code == 200

    prevent_async_celery.set_get_return_value(False)
    response = flask_client.get('/v0/worker-health')
    assert response.status_code == 500
    assert 'message' in response.json
