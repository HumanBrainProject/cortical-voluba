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

"""VoluBA backend for non-linear depth-informed alignment of cortical patches.
"""

import os.path

import flask
import flask_cors


# Version used by setup.py and docs/conf.py (parsed with a regular expression).
#
# Release checklist (based on https://packaging.python.org/):
# 1.  Ensure that tests pass for all supported Python version (Travis CI),
#     ensure that the API documentation is complete (sphinx-apidoc --separate
#     -o docs/api cortical_voluba);
# 2.  Update the release notes;
# 3.  Run check-manifest;
# 4.  Bump the version number in this file;
# 5.  pip install -U setuptools wheel twine
# 6.  python setup.py sdist bdist_wheel
# 7.  twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# 8.  Commit the updated version number
# 9.  Tag the commit (git tag -a vX.Y.Z). The release notes for the last
#     version should be converted to plain text and included in the tag
#     message:
#     pandoc -t plain docs/release-notes.rst
# 10. Bump the version number in this file to something that ends with .dev0
#     and commit
# 11. Push the master branch and the new tag to Github
# 12. twine upload dist/*
__version__ = "0.1.0.dev0"


SOURCE_URL = 'https://github.com/HumanBrainProject/cortical-voluba'
"""URL that holds the source code of the backend.

This must be changed to point to the exact code of any modified version, in
order to comply with the GNU Affero GPL licence.
"""

class DefaultConfig:
    # The default value (None) uses an sqlite database named
    # "cortical_voluba.sqlite" in flask_app.instance_path.
    # "sqlite:///cortical_voluba.sqlite" cannot be used because it is not
    # relative to the instance path.
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CELERY_BROKER_URL = "redis://"
    # Passed as the 'origins' parameter to flask_cors.CORS, see
    # https://flask-cors.readthedocs.io/en/latest/api.html#flask_cors.CORS
    CORS_ORIGINS = r'https://voluba(-dev)?\.apps(-dev)?\.hbp\.eu'


def create_app(test_config=None):
    """Instantiate the cortical-voluba Flask application."""
    from logging.config import dictConfig
    dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
    })
    app = flask.Flask(__name__,
                      instance_path=os.environ.get('INSTANCE_PATH'),
                      instance_relative_config=True)
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
        app.config.from_envvar('CORTICAL_VOLUBA_SETTINGS', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    @app.route('/source')
    def source():
        return flask.redirect(SOURCE_URL)

    if app.config.get('CORS_ORIGINS'):
        # TODO: do I need to add supports_credentials to accept the
        # Authorization header?
        flask_cors.CORS(app, origins=app.config['CORS_ORIGINS'])

    from . import api_v0
    app.register_blueprint(api_v0.bp)

    return app
