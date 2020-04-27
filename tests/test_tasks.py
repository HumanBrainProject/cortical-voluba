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

import os.path
from unittest.mock import ANY, patch

from testdata import DUMMY_NIFTI_GZ, DUMMY_IMAGE_LIST
from cortical_voluba import image_service


def transform_image_mock(_, resampled_image_path, work_dir):
    with open(os.path.join(work_dir, resampled_image_path), 'wb') as f:
        f.write(DUMMY_NIFTI_GZ)


class ImageServiceStub():
    def __init__(self, base_url, auth=None, timeout=10):
        self.base_url = base_url
        self._image_list = DUMMY_IMAGE_LIST.copy()

    def upload_image_and_get_name(self, image_file, *, file_name):
        name = image_service.strip_nii_extension(file_name)
        nifti_extra = {
            "fileName": file_name,
        }
        self._image_list.append({
            'extra': nifti_extra,
            'links': {
                'normalized': '/nifti/s3cr3t/'
            },
            'name': name,
        })
        return (name, nifti_extra)

    def download_compressed_nifti(self, name, output_file):
        output_file.write(DUMMY_NIFTI_GZ)

    def list_images(self):
        return self._image_list

    def get_image_info(self, name):
        image_list = self.list_images()
        for image_info in image_list:
            if image_info['name'] == name:
                return image_info


TEST_ALIGNMENT_REQUEST = {
    'image_service_base_url': 'http://h.test/b/',
    'image_name': 'img',
    'depth_map_name': 'depthmap',
    'transformation_matrix': [[1, 0, 0, 0],
                              [0, 1.1, 0, -2],
                              [0, 0, 0.9, 0],
                              [0, 0, 0, 1]],
    'landmark_pairs': [
        {
            'source_point': [0, 0, 0],
            'target_point': [1, 1, 1],
            'name': 'toto',
            'active': True,
            'colour': '#012345',
        },
        {
            'source_point': [-1, -2, -3.5],
            'target_point': [0, 0, 1.5],
        },
    ],
}


@patch('cortical_voluba.image_service.ImageServiceClient', autospec=True,
       wraps=ImageServiceStub)
@patch('cortical_voluba.alignment.estimate_deformation', autospec=True)
@patch('cortical_voluba.alignment.transform_image', autospec=True,
       side_effect=transform_image_mock)
def test_alignment_task(transform_image_mock,
                        estimate_deformation_mock,
                        image_service_client_mock,
                        monkeypatch,
                        flask_app):
    monkeypatch.setattr(image_service, 'ImageServiceClient', ImageServiceStub)
    flask_app.config['TEMPLATE_EQUIVOLUMETRIC_DEPTH'] = '/some/file'

    from cortical_voluba.tasks import alignment_computation_task
    ret = alignment_computation_task(TEST_ALIGNMENT_REQUEST,
                                     bearer_token='token')

    estimate_deformation_mock.assert_called_once_with(
        ANY,
        '/some/file',
        TEST_ALIGNMENT_REQUEST['transformation_matrix'],
        TEST_ALIGNMENT_REQUEST['landmark_pairs'],
        work_dir=ANY,
    )
    assert transform_image_mock.called

    assert 'message' in ret
    assert 'results' in ret
    assert 'image_service_base_url' in ret['results']
    assert 'transformed_image_name' in ret['results']
    assert 'transformed_image_neuroglancer_url' in ret['results']
    assert 'transformation_matrix' in ret['results']


def test_worker_health_task(flask_app, tmp_path):
    from cortical_voluba.tasks import worker_health_task

    depth_path = tmp_path / 'depth.nii.gz'
    flask_app.config['TEMPLATE_EQUIVOLUMETRIC_DEPTH'] = str(depth_path)

    ret = worker_health_task()
    assert ret is False

    depth_path.touch()
    ret = worker_health_task()
    assert ret is True
