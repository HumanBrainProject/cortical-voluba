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

import datetime
import os.path
import tempfile
import shutil
import subprocess
import sys

import celery.utils.log
from flask import current_app
import requests
from werkzeug.utils import secure_filename

from cortical_voluba import alignment
from cortical_voluba.celery import celery_app
from cortical_voluba import image_service

logger = celery.utils.log.get_task_logger(__name__)


def datetime_now_str():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat()


def escape_virtual_env(env):
    # Test if we are running inside of a virtual environment
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        env = env.copy()
        logger.debug('Escaping virtual environment (prefix=%s, old PATH=%s)',
                     sys.prefix, env['PATH'])
        path_components = [
            d for d in env['PATH'].split(os.pathsep)
            if (os.path.realpath(d)
                != os.path.join(os.path.realpath(sys.prefix), 'bin'))
        ]
        env['PATH'] = os.pathsep.join(path_components)
        try:
            del env['PYTHONHOME']
        except KeyError:
            pass
        try:
            del env['VIRTUAL_ENV']
        except KeyError:
            pass
        logger.debug('Escaped virtual environment. PATH is now %s',
                     env['PATH'])
        return env
    else:
        return env


@celery_app.task(bind=True)
def depth_map_computation_task(self, params, *, bearer_token):
    work_dir = tempfile.mkdtemp(prefix='depth_map_')
    try:
        image_service_base_url = params['image_service_base_url']
        segmentation_name = params['segmentation_name']
        auth = image_service.BearerTokenAuth(bearer_token)
        client = image_service.ImageServiceClient(image_service_base_url,
                                                  auth=auth)
        segmentation_basename = secure_filename(segmentation_name)
        segmentation_path = os.path.join(
            work_dir, segmentation_basename + '.nii.gz')
        segmentation_S16_path = os.path.join(
            work_dir, segmentation_basename + '_S16.nii.gz')
        depth_map_path = os.path.join(
            work_dir,
            segmentation_basename + '-equivolumetric-depth.nii.gz'
        )

        self.update_state(state='PROGRESS', meta={
            'message': 'downloading segmentation',
        })
        logger.info('downloading segmentation to %s', segmentation_path)
        with open(segmentation_path, 'wb') as f:
            client.download_compressed_nifti(segmentation_name, f)

        self.update_state(state='PROGRESS', meta={
            'message': 'converting segmentation',
        })
        system_env = escape_virtual_env(os.environ)
        command = [current_app.config['BV_ENV_PATH'],
                   'AimsFileConvert',
                   '--type', 'S16',
                   '--input', segmentation_path,
                   '--output', segmentation_S16_path]
        logger.debug('Running %s', command)
        subprocess.check_call(command, env=system_env)

        self.update_state(state='PROGRESS', meta={
            'message': 'computing the depth map',
        })
        logger.info('computing the depth map into %s', depth_map_path)
        command = [current_app.config['BV_ENV_PATH'],
                   'python', '-m', 'capsul.run',
                   'highres_cortex.capsul.isovolume',
                   'classif=' + segmentation_S16_path,
                   'verbosity=1',
                   'equivolumetric_depth=' + depth_map_path]
        logger.debug('Running %s', command)
        subprocess.check_call(command, env=system_env)

        self.update_state(state='PROGRESS', meta={
            'message': 'Removing NaNs and clamping depth values',
        })
        logger.info('Removing NaNs and clamping depth values in %s',
                    depth_map_path)
        command = [current_app.config['BV_ENV_PATH'],
                   'AimsRemoveNaN',
                   '-np', '--value', '0.5',
                   '-i', depth_map_path,
                   '-o', depth_map_path]
        logger.debug('Running %s', command)
        subprocess.check_call(command, env=system_env)
        command = [current_app.config['BV_ENV_PATH'],
                   'AimsThreshold',
                   '-m', 'be', '--clip',
                   '-t', '0',
                   '-u', '1',
                   '--input', depth_map_path,
                   '--output', depth_map_path]
        logger.debug('Running %s', command)
        subprocess.check_call(command, env=system_env)

        self.update_state(state='PROGRESS', meta={
            'message': 'uploading the depth map',
        })
        logger.info('uploading the depth map')
        depth_map_filename = (
            segmentation_basename + '-equivolumetric-depth.nii.gz'
        )
        try:
            with open(depth_map_path, 'rb') as f:
                client.preflight_image(f, file_name=depth_map_filename)
        except requests.HTTPError as e:
            if e.response.status_code == 409:
                depth_map_filename = (
                    segmentation_basename + '-equivolumetric-depth-'
                    + datetime_now_str() + '.nii.gz'
                )
            else:
                raise
        with open(depth_map_path, 'rb') as f:
            depth_map_name, _ = client.upload_image_and_get_name(
                f, file_name=depth_map_filename)

        try:
            depth_map_info = client.get_image_info(depth_map_name)
            if depth_map_info:
                depth_map_neuroglancer_url = (
                    'precomputed://'
                    + depth_map_info['links']['normalized']
                )
        except Exception:
            logger.exception('Failed to retrieve Neuroglancer URL of the '
                             'depth map named %s', depth_map_name)
            depth_map_neuroglancer_url = None

        return {
            'message': 'success',
            'results': {
                'image_service_base_url': image_service_base_url,
                'depth_map_name': depth_map_name,
                'depth_map_neuroglancer_url': depth_map_neuroglancer_url,
            },
        }
    finally:
        shutil.rmtree(work_dir)


@celery_app.task(bind=True)
def alignment_computation_task(self, params, *, bearer_token):
    work_dir = tempfile.mkdtemp(prefix='alignment_')
    try:
        image_service_base_url = params['image_service_base_url']
        image_name = params['image_name']
        depth_map_name = params['depth_map_name']
        auth = image_service.BearerTokenAuth(bearer_token)
        client = image_service.ImageServiceClient(image_service_base_url,
                                                  auth=auth)
        image_basename = secure_filename(image_name)
        depth_map_basename = secure_filename(depth_map_name)
        image_path = os.path.join(
            work_dir, image_basename + '.nii.gz')
        depth_map_path = os.path.join(
            work_dir, depth_map_basename + '.nii.gz')

        self.update_state(state='PROGRESS', meta={
            'message': 'downloading depth map',
        })
        logger.info('downloading depth map to %s', depth_map_path)
        with open(depth_map_path, 'wb') as f:
            client.download_compressed_nifti(depth_map_name, f)

        self.update_state(state='PROGRESS', meta={
            'message': 'downloading image',
        })
        logger.info('downloading image to %s', image_path)
        with open(image_path, 'wb') as f:
            client.download_compressed_nifti(image_name, f)

        self.update_state(state='PROGRESS', meta={
            'message': 'computing alignment (MOCK)',
        })
        alignment.estimate_deformation(depth_map_path,
                                       params['transformation_matrix'],
                                       params['landmark_pairs'],
                                       work_dir=work_dir)

        self.update_state(state='PROGRESS', meta={
            'message': 'resampling the image (MOCK)',
        })
        resampled_image_path = os.path.join(
            work_dir, depth_map_basename + '-resampled.nii.gz')
        alignment.transform_image(image_path, resampled_image_path,
                                  work_dir=work_dir)

        self.update_state(state='PROGRESS', meta={
            'message': 'uploading the resampled image',
        })
        logger.info('uploading the resampled image')
        resampled_image_filename = (
            image_basename + '-transformed-'
            + datetime_now_str() + '.nii.gz'
        )
        with open(resampled_image_path, 'rb') as f:
            resampled_image_name, _ = client.upload_image_and_get_name(
                f, file_name=resampled_image_filename)

        try:
            resampled_image_info = client.get_image_info(resampled_image_name)
            if resampled_image_info:
                resampled_image_neuroglancer_url = (
                    'precomputed://'
                    + resampled_image_info['links']['normalized']
                )
        except Exception:
            logger.exception('Failed to retrieve Neuroglancer URL of the '
                             'depth map named %s', resampled_image_name)
            resampled_image_neuroglancer_url = None

        return {
            'message': 'success',
            'results': {
                'image_service_base_url': image_service_base_url,
                'transformed_image_name': resampled_image_name,
                'transformed_image_neuroglancer_url':
                resampled_image_neuroglancer_url,
            },
        }
    finally:
        shutil.rmtree(work_dir)
