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

import flask
from flask import current_app, jsonify, request, url_for
import flask_cors
import marshmallow
from marshmallow import Schema, fields
import requests
from werkzeug.local import LocalProxy

from cortical_voluba import image_service
from cortical_voluba import tasks


logger = LocalProxy(lambda: current_app.logger)

bp = flask.Blueprint('api_v0', __name__, url_prefix='/v0')


class DepthMapComputationRequestSchema(Schema):
    image_service_base_url = fields.Url(required=True)
    segmentation_name = fields.String(required=True)


@bp.route('/depth-map-computation/', methods=['POST'])
@flask_cors.cross_origin(allow_headers=['Content-Type'])
def create_depth_map_computation():
    schema = DepthMapComputationRequestSchema()
    params = schema.load(request.json)

    image_service_base_url = params['image_service_base_url']
    segmentation_name = params['segmentation_name']
    authorization_header = request.headers.get('Authorization')

    if authorization_header and authorization_header.startswith('Bearer '):
        bearer_token = authorization_header[len('Bearer '):]
        auth = image_service.BearerTokenAuth(bearer_token)
    else:
        return jsonify({
            'errors': ['Missing Bearer token Authorization header'],
        }), 401

    client = image_service.ImageServiceClient(image_service_base_url,
                                              auth=auth)
    try:
        image_info = client.get_image_info(segmentation_name)
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            return jsonify({
                'errors': [e.response.text],
            }), 401
        logger.exception('The image service responded with an error')
        return jsonify({
            'errors': ['The image service responded with error {0} ({1})'
                       .format(e.response.status_code, e.response.text)],
            'debug': str(e.__dict__)
        }), 500
    except requests.RequestException:
        logger.exception('Cannot access the image service')
        return jsonify({
            'errors': ['Cannot access the image service'],
        }), 500

    if image_info is None:
        return jsonify({
            'errors': ["Cannot find an image named '{0}' on the image service"
                       .format(segmentation_name)],
        }), 400

    if image_info['extra']['neuroglancer'].get('type') != 'segmentation':
        return jsonify({
            'errors': ["The image named '{0}' is not a segmentation"
                       .format(segmentation_name)],
        }), 400

    task_result = tasks.depth_map_computation_task.delay(params)

    return jsonify({
        'status_polling_url': url_for('api_v0.depth_map_computation_status',
                                      computation_id=task_result.id),
    }), 202


@bp.route('/depth-map-computation/<computation_id>', methods=['GET'])
def depth_map_computation_status(computation_id):
    task_result = tasks.depth_map_computation_task.AsyncResult(computation_id)
    # TODO test if the task exists, return 404 if not
    # TODO set 'params': task_result.args[0] (but how can I access args??)
    state_message = task_result.state
    if 'message' in task_result.result:
        state_message += ' ({0})'.format(task_result.result['message'])
    if not task_result.ready():
        result = {
            'finished': True,
            'message': state_message,
        }
    elif task_result.successful():
        result = {
            'finished': True,
            'message': state_message,
            'results': task_result.result['results'],
        }
    elif task_result.failed():
        result = {
            'finished': True,
            'message': state_message,
            'error': True,
        }
    return jsonify(result), 200


@bp.route('/alignment-computation/', methods=['POST'])
@flask_cors.cross_origin(allow_headers=['Content-Type'])
def create_alignment_computation():
    return 'Not implemented yet', 501


@bp.route('/alignment-computation/<computation_id>', methods=['GET'])
def alignment_computation_status(computation_id):
    return 'Not implemented yet', 501


@bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(exc):
    return jsonify({'errors': exc.messages}), 400
