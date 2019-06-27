# Copyright 2019 CEA
# Copyright 2017 Forschungszentrum Jülich GmbH
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

import json
import logging
import nibabel
import numpy
import os.path
import subprocess

from flask import current_app


ITK_TO_NIFTI_COORDINATES = numpy.array(
    [[-1, 0, 0, 0],
     [0, -1, 0, 0],
     [0, 0, 1, 0],
     [0, 0, 0, 1]]
)
NIFTI_TO_ITK_COORDINATES = ITK_TO_NIFTI_COORDINATES


logger = logging.getLogger(__name__)


def transform_points(points, matrix):
    points = numpy.atleast_2d(points)
    homogeneous_points = numpy.r_[points.T, numpy.ones((1, len(points)))]
    return numpy.dot(matrix, homogeneous_points)[:-1].T


def write_itk_affine_transform(mat, file_name):
    assert numpy.all(mat[3] == [0, 0, 0, 1])
    if file_name[-4:] != '.txt':
        raise ValueError('File name of ITK transform must end with .txt')
    # As per https://github.com/ANTsX/ANTs/wiki/ITK-affine-transform-conversion
    with open(file_name, "wt") as f:
        f.write("#Insight Transform File V1.0\n")
        f.write("#Transform 0\n")
        f.write("Transform: AffineTransform_double_3_3\n")
        f.write("Parameters: {0} {1}\n".format(
            # ndarray.flat iterates in row-major ("C" order), like
            # itk::AffineTransform expects
            " ".join(str(x) for x in mat[:3, :3].flat),
            " ".join(str(x) for x in mat[:3, 3])
        ))
        f.write("FixedParameters: 0 0 0\n")


def estimate_deformation(depth_map_path, transformation_matrix, landmark_pairs,
                         work_dir):
    template_depth_map_path = (
        current_app.config['TEMPLATE_EQUIVOLUMETRIC_DEPTH']
    )
    incoming_to_template_affine = numpy.asarray(transformation_matrix)
    assert incoming_to_template_affine.shape == (4, 4)
    if numpy.any(incoming_to_template_affine[3] != [0, 0, 0, 1]):
        raise ValueError('The last row of the transformation matrix must be '
                         '[0, 0, 0, 1]')
    template_points = numpy.array([pair["source_point"]
                                   for pair in landmark_pairs])
    incoming_points = numpy.array([pair["target_point"]
                                   for pair in landmark_pairs])
    incoming_points_in_template_space = transform_points(
        incoming_points, incoming_to_template_affine)
    logger.debug('Affine transformation from incoming image to template '
                 'space:\n%s', incoming_to_template_affine)
    logger.debug('Template points:\n%s', template_points)
    logger.debug('Incoming points:\n%s', incoming_points)
    logger.debug('Incoming points in template space:\n%s',
                 incoming_points_in_template_space)

    template_to_incoming_affine = numpy.linalg.inv(incoming_to_template_affine)
    # TODO check if Nibabel behaves the same as ITK when the qform is missing
    incoming_nibabel = nibabel.load(depth_map_path)
    incoming_qform = incoming_nibabel.get_qform()
    incoming_voxel_size = incoming_nibabel.header.get_zooms()

    write_itk_affine_transform(
        NIFTI_TO_ITK_COORDINATES
        @ incoming_qform
        @ numpy.diag([1 / vs for vs in incoming_voxel_size] + [1])
        @ template_to_incoming_affine
        @ ITK_TO_NIFTI_COORDINATES,
        os.path.join(work_dir, 'template_to_incoming_affine.txt')
    )
    if current_app.config.get('DEBUG_ALIGNMENT'):
        command = [
            'antsApplyTransforms', '--verbose',
            '--float',
            '--input', depth_map_path,
            '--reference-image', template_depth_map_path,
            '--interpolation', 'Linear',
            '--default-value', '0',
            '--output', 'incoming_depth_map_in_template.nii.gz',
            '--transform', 'template_to_incoming_affine.txt',
        ]
        logger.debug('Running %s with cwd=%s', command, work_dir)
        subprocess.check_call(command, cwd=work_dir)

    command = [
        'antsRegistration',
        '--verbose', '1',
        '--float', '1',
        '--dimensionality', '3',
        '--initial-moving-transform', '[template_to_incoming_affine.txt,1]',
        '--metric', 'MeanSquares[{0},{1}]'.format(depth_map_path,
                                                  template_depth_map_path),
        # TODO add landmark-based metric
        '--transform', 'SyN[0.1,3,0]',
        '--convergence', '[200x100x100,1e-6,10]',
        '--shrink-factors', '4x2x1',
        '--smoothing-sigmas', '2x1x0vox',
        '--output', 'cortical',
    ]
    logger.debug('Running %s with cwd=%s', command, work_dir)
    subprocess.check_call(command, cwd=work_dir)


def transform_image(input_image_path, resampled_image_path, work_dir):
    command = [
        'antsApplyTransforms',
        '--dimensionality', '3',
        '--float', '1',
        '--verbose', '1',
        '--input', input_image_path,
        '--reference-image', input_image_path,
        '--interpolation', 'Linear',
        '--default-value', '0',
        '--output', resampled_image_path,
        '--transform', 'cortical1InverseWarp.nii.gz',
    ]
    logger.debug('Running %s with cwd=%s', command, work_dir)
    subprocess.check_call(command, cwd=work_dir)
