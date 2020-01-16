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

import cortical_voluba


def test_config():
    assert not cortical_voluba.create_app().testing
    assert cortical_voluba.create_app(test_config={'TESTING': True}).testing


def test_wsgi_app():
    from cortical_voluba.wsgi import application
    assert application is not None


def test_root_route(flask_client):
    response = flask_client.get('/')
    assert response.status_code == 302


def test_source_route(flask_client):
    response = flask_client.get('/source')
    assert response.status_code == 302


def test_health_route(flask_client):
    response = flask_client.get('/health')
    assert response.status_code == 200


def test_echo_route():
    from cortical_voluba import create_app
    app = create_app({'TESTING': True, 'ENABLE_ECHO': False})
    with app.test_client() as client:
        response = client.get('/echo')
    assert response.status_code == 404

    app = create_app({'TESTING': True, 'ENABLE_ECHO': True})
    with app.test_client() as client:
        response = client.get('/echo')
    assert response.status_code == 200


def test_CORS():
    from cortical_voluba import create_app
    app = create_app({'TESTING': True, 'CORS_ORIGINS': None})
    with app.test_client() as client:
        response = client.get('/')
    assert 'Access-Control-Allow-Origin' not in response.headers
    app = create_app({'TESTING': True, 'CORS_ORIGINS': '*'})
    with app.test_client() as client:
        response = client.get('/')
    assert 'Access-Control-Allow-Origin' in response.headers
    assert response.headers['Access-Control-Allow-Origin'] == '*'


def test_proxy_fix():
    app = cortical_voluba.create_app(test_config={
        'TESTING': True,
        'PROXY_FIX': {
            'x_for': 1,
            'x_proto': 1,
            'x_host': 1,
            'x_port': 1,
            'x_prefix': 1,
        },
    })
    called = False
    @app.route('/test')
    def test():
        nonlocal called
        from flask import request
        assert request.url == 'https://h.test:1234/toto/test'
        assert request.access_route[0] == '1.2.3.4'
        called = True
        return ''
    client = app.test_client()
    client.get('/test', headers={
        'X-Forwarded-For': '1.2.3.4',
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Host': 'h.test',
        'X-Forwarded-Port': '1234',
        'X-Forwarded-Prefix': '/toto',
    })
    assert called


def test_openapi_spec(flask_app, flask_client):
    response = flask_client.get('/openapi.json')
    assert response.status_code == 200
    assert response.json['openapi'] == flask_app.config['OPENAPI_VERSION']
    assert 'info' in response.json
    assert 'title' in response.json['info']
    assert 'version' in response.json['info']
    # assert 'license' in response.json['info']
    assert 'servers' in response.json
    for server_info in response.json['servers']:
        assert server_info['url'] != '/'


def test_openapi_spec_development_mode():
    from cortical_voluba import create_app
    app = create_app({'TESTING': True, 'ENV': 'development'})
    with app.test_client() as client:
        response = client.get('/openapi.json')
    assert response.json['servers'][0]['url'] == '/'
