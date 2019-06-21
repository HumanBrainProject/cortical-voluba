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
from flask import abort, current_app, jsonify, make_response, request, url_for
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


class LandmarkPairSchema(Schema):
    source_point = fields.Tuple((fields.Float, fields.Float, fields.Float),
                                required=True)
    target_point = fields.Tuple((fields.Float, fields.Float, fields.Float),
                                required=True)


class AlignmentComputationRequestSchema(Schema):
    image_service_base_url = fields.Url(required=True)
    image_name = fields.String(required=True)
    depth_map_name = fields.String(required=True)
    # TODO validate that transformation_matrix is a 4×4 or 3×4 matrix
    transformation_matrix = fields.List(fields.List(fields.Float),
                                        required=True)
    landmark_pairs = fields.Nested(LandmarkPairSchema, many=True,
                                   required=True)


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
    verify_image_on_image_service(client, segmentation_name, 'segmentation')

    logger.debug('Submitting Celery job with params=%s', params)
    task_result = tasks.depth_map_computation_task.delay(
        params,
        bearer_token=bearer_token
    )
    logger.debug('Submitted Celery job has id=%s', task_result.id)

    return jsonify({
        'status_polling_url': url_for('api_v0.depth_map_computation_status',
                                      computation_id=task_result.id),
    }), 202


@bp.route('/depth-map-computation/<computation_id>', methods=['GET'])
def depth_map_computation_status(computation_id):
    task_result = tasks.depth_map_computation_task.AsyncResult(computation_id)
    return make_computation_task_status_response(task_result)


@bp.route('/alignment-computation/', methods=['POST'])
@flask_cors.cross_origin(allow_headers=['Content-Type'])
def create_alignment_computation():
    schema = AlignmentComputationRequestSchema()
    params = schema.load(request.json)

    image_service_base_url = params['image_service_base_url']
    image_name = params['image_name']
    depth_map_name = params['depth_map_name']
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
    verify_image_on_image_service(client, image_name, 'image')
    verify_image_on_image_service(client, depth_map_name, 'image')

    logger.debug('Submitting Celery job with params=%s', params)
    task_result = tasks.alignment_computation_task.delay(
        params,
        bearer_token=bearer_token
    )
    logger.debug('Submitted Celery job has id=%s', task_result.id)

    return jsonify({
        'status_polling_url': url_for('api_v0.alignment_computation_status',
                                      computation_id=task_result.id),
    }), 202


@bp.route('/alignment-computation/<computation_id>', methods=['GET'])
def alignment_computation_status(computation_id):
    task_result = tasks.alignment_computation_task.AsyncResult(computation_id)
    return make_computation_task_status_response(task_result)


@bp.errorhandler(marshmallow.exceptions.ValidationError)
def handle_validation_error(exc):
    return jsonify({'errors': exc.messages}), 400


def verify_image_on_image_service(client, image_name, expected_type='image'):
    try:
        image_info = client.get_image_info(image_name)
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            abort(make_response(jsonify({
                'errors': [e.response.text],
            }), 401))
        logger.exception('The image service responded with an error')
        abort(make_response(jsonify({
            'errors': ['The image service responded with error {0} ({1})'
                       .format(e.response.status_code, e.response.text)],
            'debug': str(e.__dict__)
        }), 500))
    except requests.RequestException:
        logger.exception('Cannot access the image service')
        abort(make_response(jsonify({
            'errors': ['Cannot access the image service'],
        }), 500))

    if image_info is None:
        abort(make_response(jsonify({
            'errors': ["Cannot find an image named '{0}' on the image service"
                       .format(image_name)],
        }), 400))

    if (image_info['extra']['neuroglancer'].get('type', 'image')
            != expected_type):
        abort(make_response(jsonify({
            'errors': ["The image named '{0}' is not of 'image' type"
                       .format(image_name)],
        }), 400))


def make_computation_task_status_response(task_result):
    # TODO test if the task exists, return 404 if not
    # TODO set 'params': task_result.args[0] (but how can I access args??)
    state_message = task_result.state
    if (isinstance(task_result.result, dict)
            and 'message' in task_result.result):
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
    return make_response(jsonify(result), 200)
