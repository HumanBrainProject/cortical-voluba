# Copyright 2019–2020 CEA
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

import importlib
import logging
import logging.config
import os
import re

import flask
import flask_smorest

# __version__ and SOURCE_URL are used by setup.py and docs/conf.py (they are
# parsed with a regular expression, so keep the syntax simple).
__version__ = "0.1.0.dev0"


SOURCE_URL = 'https://github.com/HumanBrainProject/cortical-voluba'
"""URL that holds the source code of the backend.

This should be changed to point to the code of any modified version.
"""


class DefaultConfig:
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    # Passed as the 'origins' parameter to flask_cors.CORS, see
    # https://flask-cors.readthedocs.io/en/latest/api.html#flask_cors.CORS
    CORS_ORIGINS = r'https://voluba(-dev)?\.apps(-dev)?\.hbp\.eu'
    # Set the full path to bv_env if it is not in the system PATH
    BV_ENV_PATH = 'bv_env'
    # Set to True to enable the /echo endpoint (for debugging)
    ENABLE_ECHO = False
    # Set up werkzeug.middleware.proxy_fix.ProxyFix with the provided keyword
    # arguments, see
    # https://werkzeug.palletsprojects.com/en/0.15.x/middleware/proxy_fix/
    PROXY_FIX = None
    # Version of the linear_voluba api (used in the OpenAPI spec)
    API_VERSION = __version__
    OPENAPI_VERSION = '3.0.2'  # OpenAPI version to generate
    OPENAPI_URL_PREFIX = '/'
    OPENAPI_REDOC_PATH = 'redoc'
    OPENAPI_REDOC_VERSION = '2.0.0-rc.20'
    OPENAPI_SWAGGER_UI_PATH = 'swagger-ui'
    OPENAPI_SWAGGER_UI_VERSION = '3.24.2'
    #
    # Other configuration keys without a default value:
    # TEMPLATE_EQUIVOLUMETRIC_DEPTH : the full path to the pre-computed
    #     equivolumetric depth for the template (normally
    #     BigBrain_equivolumetric_depth.nii.gz).


# This function has a magic name which is recognized by flask as a factory for
# the main app.
def create_app(test_config=None):
    """Instantiate the cortical-voluba Flask application."""
    # logging configuration inspired by
    # http://flask.pocoo.org/docs/1.0/logging/#basic-configuration
    if test_config is None or not test_config.get('TESTING'):
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': False,  # preserve Gunicorn loggers
            'formatters': {'default': {
                'format': '[%(asctime)s] [%(process)d] %(levelname)s '
                'in %(module)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S %z',
            }},
            'handlers': {'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            }},
            'root': {
                'level': 'DEBUG',
                'handlers': ['wsgi']
            }
        })

    # If we are running under Gunicorn, set up the root logger to use the same
    # handler as the Gunicorn error stream.
    if logging.getLogger('gunicorn.error').handlers:
        root_logger = logging.getLogger()
        root_logger.handlers = logging.getLogger('gunicorn.error').handlers
        root_logger.setLevel(logging.getLogger('gunicorn.error').level)

    # Hide Kubernetes health probes from the logs
    access_logger = logging.getLogger('gunicorn.access')
    exclude_useragent_re = re.compile(r'kube-probe')
    access_logger.addFilter(
        lambda record: not (
            record.args['h'].startswith('10.')
            and record.args['m'] == 'GET'
            and record.args['U'] == '/health'
            and exclude_useragent_re.search(record.args['a'])
        )
    )

    app = flask.Flask(__name__,
                      instance_path=os.environ.get('INSTANCE_PATH'),
                      instance_relative_config=True)
    app.config.from_object(DefaultConfig)
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
        app.config.from_envvar('CORTICAL_VOLUBA_SETTINGS', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure that the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/')
    def root():
        return flask.redirect('/redoc')

    @app.route('/source')
    def source():
        return flask.redirect(SOURCE_URL)

    # Return success if the app is ready to serve requests. Used in OpenShift
    # health checks.
    @app.route("/health")
    def health():
        return '', 200

    if app.config.get('ENABLE_ECHO'):
        @app.route('/echo')
        def echo():
            app.logger.info('ECHO:\n'
                            'Headers\n'
                            '=======\n'
                            '%s', flask.request.headers)
            return ''

    if app.config.get('CORS_ORIGINS'):
        import flask_cors
        flask_cors.CORS(app, origins=app.config['CORS_ORIGINS'],
                        allow_headers=['Authorization', 'Content-Type'])

    # Celery must be initialized before the tasks module is imported, i.e.
    # before the API modules.
    with app.app_context():
        # We must instantiate a new Celery app each time a Flask app is
        # instantiated, because the Celery app and tasks are tied to the Flask
        # app (they read from flask_app.config).
        from . import celery
        celery.celery_app = celery.create_celery_app(app)
        # Every time a new Celery app is instantiated, the tasks need to be
        # re-created because they must use the correct app at import time.
        from . import tasks
        importlib.reload(tasks)

    if app.config['ENV'] == 'development':
        local_server = [
            {
                'url': '/',
            },
        ]
    else:
        local_server = []

    smorest_api = flask_smorest.Api(app, spec_kwargs={
        'servers': local_server + [
            {
                'url': 'https://cortical-voluba.apps-dev.hbp.eu/',
                'description': 'Development instance running the *dev* '
                               'branch',
            },
        ],
        'info': {
            'title': 'cortical-voluba',
            'description': '''\
Voluba backend for non-linear depth-informed alignment of cortical patches.

For more information, see the **source code repository:** <{SOURCE_URL}>.
'''.format(SOURCE_URL=SOURCE_URL),
            # 'license': {
            #     'name': 'Apache 2.0',
            #     'url': 'https://www.apache.org/licenses/LICENSE-2.0.html',
            # },
        },
    })
    from . import api_v0
    smorest_api.register_blueprint(api_v0.bp)

    if app.config.get('PROXY_FIX'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, **app.config['PROXY_FIX'])

    return app
