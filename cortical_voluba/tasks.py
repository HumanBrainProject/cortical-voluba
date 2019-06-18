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

import celery.utils.log
from celery import shared_task


logger = celery.utils.log.get_task_logger(__name__)


@shared_task(bind=True, track_started=True)
def depth_map_computation_task(self, params):
    self.update_state(state='PROGRESS', meta={
        'message': 'downloading segmentation',
    })
    return {
        'message': 'finished (dummy)',
        'results': {
            'image_service_base_url': params['image_service_base_url'],
            'depth_map_name': None,
            'depth_map_neuroglancer_url': None,
        },
    }
