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

from celery import Celery
from flask import current_app

from . import create_app as create_flask_app


__all__ = ['create_celery_app']


def create_celery_app(flask_app):
    """Initialize the Celery instance in the global variable 'celery_app'."""
    app = Celery(
        flask_app.import_name,
        backend=flask_app.config['CELERY_RESULT_BACKEND'],
        broker=flask_app.config['CELERY_BROKER_URL']
    )
    app.conf.update(flask_app.config)

    class ContextTask(app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    app.Task = ContextTask

    return app


celery_app = None

# If current_app is defined, it means that the Flask app already exists, so
# create_app() will take care of running:
#
#     celery_app = create_celery_app(flask_app)
#
# If not, it means that cortical_voluba.celery is imported outside of the Flask
# app (probably by the celery command-line tool) so we need to instantiate the
# Flask app.
if not current_app:
    create_flask_app()
