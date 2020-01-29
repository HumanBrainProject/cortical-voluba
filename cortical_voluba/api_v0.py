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

import logging

from flask import jsonify, make_response, request, url_for
import flask_smorest
from flask_smorest import abort
import marshmallow
from marshmallow import Schema, fields
from marshmallow.validate import Length
import requests

from cortical_voluba import image_service
from cortical_voluba import tasks


logger = logging.getLogger(__name__)

bp = flask_smorest.Blueprint(
    'api_v0', __name__, url_prefix='/v0',
    description='Draft API of the cortical-voluba backend',
)

EXAMPLE_IMAGE_SERVICE_URL = 'https://zam10143.zam.kfa-juelich.de/chumni/'


class DepthMapComputationRequestSchema(Schema):
    class Meta:
        ordered = True
    image_service_base_url = fields.Url(
        schemes={'http', 'https'}, required=True,
        description='Base URL of the image service.',
        example='https://zam10143.zam.kfa-juelich.de/chumni/',
    )
    segmentation_name = fields.String(
        required=True,
        description='The `name` attribute returned by Chumni as part of its '
                    'UserDatasetEntry structure (returned by its /list '
                    'endpoint). This is the name of the segmentation Nifti '
                    'file, without trailing `.nii` or `.nii.gz`.',
    )


class AuthorizationHeadersSchema(Schema):
    Authorization = fields.String(
        required=True,
        description='Bearer token of the currently logged in user, will be '
                    'passed as-is to the image service',
    )


class DepthMapComputationResponseSchema(Schema):
    status_polling_url = fields.Url(
        required=True,
        description='A URL for polling the status of the depth map '
                    'computation. This URL is relative to the base URL of the '
                    'backend.',
    )


class LandmarkPairSchema(Schema):
    class Meta:
        ordered = True
    source_point = fields.List(
        fields.Float, validate=Length(equal=3), required=True,
        description='Coordinates of the point in source space.',
    )
    target_point = fields.List(
        fields.Float, validate=Length(equal=3), required=True,
        description='Coordinates of the point in target space.',
    )
    active = fields.Boolean(
        default=True, missing=True,
        description='Landmark pairs for which active is false are not used '
                    'for the estimation of the transformation matrix.',
    )
    name = fields.String(
        required=False,
        description='Optional identifier of the landmark pair.',
    )


class DepthMapComputationResultSchema(Schema):
    class Meta:
        ordered = True
    image_service_base_url = fields.Url(
        schemes={'http', 'https'}, required=True,
        description='Base URL of the image service where the depth map image '
                    'was uploaded.',
        example=EXAMPLE_IMAGE_SERVICE_URL,
    )
    depth_map_name = fields.String(
        required=True,
        description='The `name` under which the depth map image was uploaded '
                    'onto the image service.',
    )
    depth_map_neuroglancer_url = fields.Url(
        required=True,
        description='A URL that can be passed to Neuroglancer to display the '
                    'depth map. It will include the Neuroglancer datasource '
                    'prefix (i.e. `precomputed://`).',
    )


class ComputationTaskStatusResponseSchema(Schema):
    class Meta:
        ordered = True
    finished = fields.Boolean(
        required=True,
        description='A flag that indicates if the depth map computation has '
                    'come to an end, i.e. if set to false, the status will '
                    'not change and no further polling is necessary.',
    )
    message = fields.String(
        required=True,
        description='A status message that can be displayed to the user. It '
                    'contains status feedback suitable for display to the '
                    'user (typically it could be “Downloading segmentation”, '
                    'then “Computing depth map”, then “Uploading depth map”, '
                    'finally “Finished”). If error is true, it is a user-'
                    'readable error message.',
    )
    error = fields.Boolean(
        required=False,
        description='Flag set to true if there was an error, in that case the '
                    'depth map is unavailable and message contains an error '
                    'message',
    )


class DepthMapComputationTaskStatusResponseSchema(
        ComputationTaskStatusResponseSchema):
    results = fields.Nested(
        DepthMapComputationResultSchema,
        required=False,
        description='Result of the computation. Present only if `finished` is '
                    'true and `error` is false.',
    )


class AlignmentComputationRequestSchema(Schema):
    class Meta:
        ordered = True
    image_service_base_url = fields.Url(
        schemes={'http', 'https'}, required=True,
        description='Base URL of the image service.',
        example='https://zam10143.zam.kfa-juelich.de/chumni/',
    )
    image_name = fields.String(
        required=True,
        description='The `name` under which the user-visible cortical patch '
                    'image is known to the image service.',
    )
    depth_map_name = fields.String(
        required=True,
        description='The `name` under which the depth map image is known '
                    'to the image service.',
    )
    # TODO: use linear_voluba.api.TransformationMatrixField
    transformation_matrix = fields.List(
        fields.List(
            fields.Float,
            validate=Length(equal=4)
        ), validate=Length(min=3, max=4), required=True,
        description='The 4×4 affine transformation matrix from the incoming '
                    'volume to the template space, in millimetres, in the '
                    'same format as returned by the `/least-squares` affine '
                    'backend.',
    )
    landmark_pairs = fields.Nested(
        LandmarkPairSchema,
        many=True, unknown=marshmallow.EXCLUDE, required=True,
        description='The list of landmark pairs, in the same format as '
                    'consumed by the `/least-squares` affine backend. Note '
                    'that `source_point` refers to the template volume, while '
                    '`target_point` refers to the incoming volume.',
    )


class AlignmentComputationResponseSchema(Schema):
    status_polling_url = fields.Url(
        required=True,
        description='A URL for polling the status of the alignment '
                    'computation. This URL is relative to the base URL of the '
                    'backend.',
    )


class AlignmentComputationResultSchema(Schema):
    class Meta:
        ordered = True
    image_service_base_url = fields.Url(
        schemes={'http', 'https'}, required=True,
        description='Base URL of the image service where the transformed '
                    'image was uploaded.',
        example=EXAMPLE_IMAGE_SERVICE_URL,
    )
    transformed_image_name = fields.String(
        required=True,
        description='The `name` under which the transformed image was '
                    'uploaded onto the image service.',
    )
    transformed_image_neuroglancer_url = fields.Url(
        required=True,
        description='A URL that can be passed to Neuroglancer to display the '
                    'transformed image. It will include the Neuroglancer '
                    'datasource prefix (i.e. `precomputed://`).',
    )
    # TODO: use linear_voluba.api.TransformationMatrixField
    transformation_matrix = fields.List(
        fields.List(
            fields.Float,
            validate=Length(equal=4)
        ), validate=Length(min=3, max=4), required=True,
        description='The affine transformation matrix that must be applied to '
                    'display the transformed image in the template space. It '
                    'is a 4×4 affine transformation matrix, in millimetres, '
                    'in the same format as returned by the `/least-squares` '
                    'affine backend.',
    )


class AlignmentComputationTaskStatusResponseSchema(
        ComputationTaskStatusResponseSchema):
    results = fields.Nested(
        AlignmentComputationResultSchema,
        required=False,
        description='Result of the computation. Present only if `finished` is '
                    'true and `error` is false.',
    )


class ErrorResponseSchema(Schema):
    class Meta:
        ordered = True
        unknown = marshmallow.INCLUDE
        strict = False
    code = fields.Integer(required=False)
    status = fields.String(required=False)
    message = fields.String(required=False)
    errors = fields.Dict(keys=fields.String(), required=False)


@bp.route('/depth-map-computation/', methods=['POST'])
@bp.arguments(DepthMapComputationRequestSchema, location='json')
@bp.doc(security=[{'chumni_auth': []}])
# The error responses come first, the schemas are only used for
# documentation
@bp.response(ErrorResponseSchema, code=400)
@bp.response(ErrorResponseSchema, code=401)
# Code 422 is raised by webargs for request validation errors
@bp.response(ErrorResponseSchema, code=422,
             description='Semantically invalid request')
# The successful response must be the last response decorator, its schema
# is used for serializing the response.
@bp.response(DepthMapComputationResponseSchema, code=202)
def create_depth_map_computation(params):
    """Compute the depth map from a cortical segmentation.

    Trigger computation of the depth map for an image, given a cortical
    segmentation of the volume that has been uploaded previously to the image
    service.
    """
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


class DepthMapComputationPollPathSchema(Schema):
    computation_id = fields.String(
        required=True,
        description='Computation id returned by /v0/depth-map-computation/',
    )


@bp.route('/depth-map-computation/<computation_id>', methods=['GET'])
@bp.arguments(DepthMapComputationPollPathSchema, location='path')
@bp.response(DepthMapComputationTaskStatusResponseSchema, code=200)
def depth_map_computation_status(path_args, *, computation_id):
    """Poll the status of a depth map computation task."""
    assert computation_id == path_args['computation_id']
    task_result = tasks.depth_map_computation_task.AsyncResult(computation_id)
    return make_computation_task_status_response(task_result)


@bp.route('/alignment-computation/', methods=['POST'])
@bp.arguments(AlignmentComputationRequestSchema)
@bp.doc(security=[{'chumni_auth': []}])
# The error responses come first, the schemas are only used for
# documentation
@bp.response(ErrorResponseSchema, code=400)
@bp.response(ErrorResponseSchema, code=401)
# Code 422 is raised by webargs for request validation errors
@bp.response(ErrorResponseSchema, code=422,
             description='Semantically invalid request')
# The successful response must be the last response decorator, its schema
# is used for serializing the response.
@bp.response(AlignmentComputationResponseSchema, code=202)
def create_alignment_computation(params):
    """Compute the alignment of a cortical patch."""
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


class AlignmentComputationPollPathSchema(Schema):
    computation_id = fields.String(
        required=True,
        description='Computation id returned by /v0/alignment-computation/',
    )


@bp.route('/alignment-computation/<computation_id>', methods=['GET'])
@bp.arguments(AlignmentComputationPollPathSchema, location='path')
@bp.response(AlignmentComputationTaskStatusResponseSchema, code=200)
def alignment_computation_status(path_args, *, computation_id):
    """Poll the status of a depth map computation task."""
    assert computation_id == path_args['computation_id']
    task_result = tasks.alignment_computation_task.AsyncResult(computation_id)
    return make_computation_task_status_response(task_result)


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
            'finished': False,
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


@bp.route('/worker-health', methods=['GET'])
@bp.response(ErrorResponseSchema, code=500)
@bp.response(code=200)
def worker_health():
    """Test health of the workers.

    This endpoint allows to test if the workers (the process that perform the
    actual computations asynchronously) can be contacted and are able to
    respond. In case of success, an empty HTTP 200 response is sent.

    The response will be sent only once the worker has responded, so that **in
    case of a broken connection to the worker, this endpoint will hang
    forever**.

    This endpoint also performs a basic sanity check on the workers (as of now,
    it tests if the equivolumetric depth map of the template is accessible). If
    this check fails, a 500 HTTP status will be returned along with a
    descriptive error message.
    """
    async_result = tasks.worker_health_task.delay()
    result = async_result.get()
    if result:
        return '', 200
    else:
        return {
            'message': 'The Celery worker cannot access the template'
                       'equivolumetric depth.',
        }, 500
