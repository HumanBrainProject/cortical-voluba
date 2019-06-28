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


def test_source_link(flask_client):
    response = flask_client.get('/source')
    assert response.status_code == 302


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


def test_echo():
    app = cortical_voluba.create_app(test_config={
        'TESTING': True,
    })
    assert app.test_client().get('/echo').status_code == 404
    app = cortical_voluba.create_app(test_config={
        'TESTING': True,
        'ENABLE_ECHO': True,
    })
    assert app.test_client().get('/echo').status_code == 200
