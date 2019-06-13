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
from flask import current_app, g, jsonify, request, Response
import flask_cors

bp = flask.Blueprint('api_v0', __name__, url_prefix='/v0')


@bp.route('/depth-map-computation/', methods=['POST'])
@flask_cors.cross_origin(allow_headers=['Content-Type'])
def create_depth_map_computation():
    return 'Not implemented yet', 501


@bp.route('/depth-map-computation/<computation_id>', methods=['GET'])
def get_depth_map_computation(computation_id):
    return 'Not implemented yet', 501


@bp.route('/alignment-computation/', methods=['POST'])
@flask_cors.cross_origin(allow_headers=['Content-Type'])
def create_alignment_computation():
    return 'Not implemented yet', 501


@bp.route('/alignment-computation/<computation_id>', methods=['GET'])
def get_alignment_computation(computation_id):
    return 'Not implemented yet', 501
