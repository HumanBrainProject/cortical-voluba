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

"""Interface to the Chumni image service developed in Jülich.

Based on the current `image service documentation`_.

.. _`image service documentation`: https://docs.google.com/document/d/1Gl30DyjntnVqtZ354OEc7SegdSnUjox2flUJb04MwaA/edit?usp=sharing
.. default-role:: any
"""

import cgi
import gzip
import os
from urllib.parse import urljoin

import requests
import requests.auth


PREFLIGHT_DATA_LENGTH = 2048  # first 2kiB of Nifti are enough to read header
"""Number of bytes sent for a preflight request."""

# By default we let requests choose the best chunk size.
_DOWNLOAD_CHUNK_SIZE = None


def strip_nii_extension(file_name):
    """Strip either .nii or .nii.gz from the provided string.

    This function applies the same rule as Chumni to determine the base name of
    a file. If the suffix is not recognized, None is returned.

    :param str file_name: full file name with extension
    :rtype: str or None
    """
    if file_name.endswith('.nii.gz'):
        return file_name[:-len('.nii.gz')]
    if file_name.endswith('.nii'):
        return file_name[:-len('.nii')]


def guess_file_size(fileobj):
    """Try to discover the file size of a file-like object.

    The file size in bytes is returned, or `None` it cannot be determined.

    :param io.IOBase fileobj: a Python file-like object
    :rtype: int or None

    """
    try:
        file_size = os.stat(fileobj.fileno()).st_size
    except (OSError, AttributeError):
        # the file object does not have a working fileno() method, or
        # os.stat() failed
        file_size = None
    return file_size


class BearerTokenAuth(requests.auth.AuthBase):
    """Attaches a Bearer Token to the given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer ' + self.token
        return r


class LowLevelImageServiceClient:
    """Client to an instance of the Chumni image service.

    For a higher-level interface see the child class `ImageServiceClient`.

    :param str base_url: base URL of the image service
    :param requests.auth.AuthBase auth: optional authentication callable to
           identify the user of the image service (normally
           `BearerTokenAuth`).
    """
    def __init__(self, base_url, auth=None):
        self.base_url = base_url
        if self.base_url[-1] != '/':
            self.base_url += '/'
        self.auth = auth

    def list_images(self):
        """List the images contained in the image service.

        The JSON object that Chumni returns is returned directly: it is a list
        of JSON dictionaries of type ``UserDatasetEntry``.

        :rtype: list
        :returns: list of ``UserDatasetEntry`` dictionaries
        :raises requests.RequestException: for HTTP or communication errors
        """
        r = requests.get(self.base_url + 'list',
                         auth=self.auth)
        r.raise_for_status()
        return r.json()

    def upload_image(self, image_file, *,
                     file_name=None, segmentation=False, preflight=False):
        """Upload an image to the image service.

        :param io.IOBase image_file: a binary-mode file object containing the
               Nifti data to be uploaded
        :param str file_name: the file name to be sent to the image service. It
               must include the correct suffix (.nii or .nii.gz) corresponding
               to the contained data. The value ``image_file.name`` will be
               used by default, or if None is passed.
        :param bool segmentation: if True, the image is considered to contain
               integer labels referring to objects of a segmentation.
        :param bool preflight: if True, send a fast preflight request instead
               of a full upload. Only the first 2KiB of the data are sent. The
               image service will test if it can handle the file and return
               the usual ``NiftiExtra`` structure (the ``data`` sub-dictionary
               will be missing because only the header is sent). Nothing is
               stored on the image service.
        :rtype: dict
        :returns: dictionary of type ``NiftiExtra``
        :raises requests.RequestException: for HTTP or communication errors
        """
        if preflight:
            image_data = image_file.read(PREFLIGHT_DATA_LENGTH)
        else:
            image_data = image_file

        if file_name is None:
            file_name = os.path.basename(image_file.name)

        files = {
            'image': (file_name,
                      image_data,
                      'application/gzip' if file_name.endswith('.gz')
                      else 'application/octet-stream')
        }
        headers = {}
        if segmentation:
            headers['X-CHUNMA-SEGMENTATION'] = 'true'
        file_size = guess_file_size(image_file)
        if file_size is not None:
            headers['X-CHUNMA-FILESIZE'] = str(file_size)

        endpoint = 'preflight' if preflight else 'upload'
        r = requests.post(self.base_url + endpoint,
                          files=files,
                          headers=headers,
                          auth=self.auth)
        r.raise_for_status()
        return r.json()

    def preflight_image(self, image_file, **kwargs):
        """Send a fast preflight request to test the upload.

        This is a shortcut for calling `upload_image` with ``preflight=True``.
        """
        return self.upload_image(image_file, **kwargs, preflight=True)

    def delete_image(self, normalized_url):
        """Delete an image from the image service.

        :param str normalized_url: URL of the normalized Neuroglancer dataset
        :raises requests.RequestException: for HTTP or communication errors
        """
        # The URL provided by the image service looks like an absolute URL (it
        # has a leading slash), but it is in fact relative to the base_url.
        normalized_url = normalized_url.lstrip('/')
        r = requests.delete(urljoin(self.base_url, normalized_url),
                            auth=self.auth)
        r.raise_for_status()

    def download_nifti(self, name, output_file):
        """Download the image as uncompressed Nifti.

        :param str name: the name of the image on the image service
        :param io.IOBase image_file: a binary-mode file object to which the
               uncompressed Nifti data will be written
        :raises requests.RequestException: for HTTP or communication errors
        """
        r = requests.get(self.base_url + 'download/' + name + '.nii',
                         auth=self.auth, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(_DOWNLOAD_CHUNK_SIZE):
            output_file.write(chunk)

    def download_compressed_nifti(self, name, output_file):
        """Download the image as compressed Nifti.

        :param str name: the name of the image on the image service
        :param io.IOBase image_file: a binary-mode file object to which the
               gzip-compressed Nifti data will be written
        :raises requests.RequestException: for HTTP or communication errors
        """
        r = requests.get(self.base_url + 'download/' + name + '.nii.gz',
                         auth=self.auth, stream=True)
        if r.status_code == 404:
            # As of 2019-06-06 the server only provides this endpoint if the
            # file was uploaded as compressed Nifti.
            self.download_nifti(name,
                                gzip.GzipFile(fileobj=output_file, mode='wb'))
        else:
            r.raise_for_status()
            for chunk in r.iter_content(_DOWNLOAD_CHUNK_SIZE):
                output_file.write(chunk)

    def download_original_file(self, name, output_file):
        """Download the image in its original Nifti format (compressed or not).

        The filename is returned by this method if it is returned by the
        server, and can be used to determine if the Nifti file is
        gzip-compressed or not.

        :param str name: the name of the image on the image service
        :param io.IOBase image_file: a binary-mode file object to which the
               Nifti data will be written
        :rtype: str
        :returns: the file name as returned by the server (if available)
        :raises requests.RequestException: for HTTP or communication errors

        """
        r = requests.get(self.base_url + 'download/' + name,
                         auth=self.auth, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=_DOWNLOAD_CHUNK_SIZE):
            output_file.write(chunk)
        # FIXME: we should the 'filename*' header attribute of RFC6266.
        if 'Content-Disposition' in r.headers:
            cd = cgi.parse_header(r.headers['Content-Disposition'])
            filename = cd[1].get('filename')
            if filename:
                return os.path.basename(filename)


class ImageServiceClient(LowLevelImageServiceClient):
    """Client to an instance of the Chumni image service.

    :param str base_url: base URL of the image service
    :param requests.auth.AuthBase auth: optional authentication callable to
           identify the user of the image service (normally
           `BearerTokenAuth`).
    """
    def list_images_by_name(self):
        """List the images contained in the image service.

        :rtype: dict
        :returns: a dictionary, where keys are the names of the images, and
                  values are ``UserDatasetEntry`` dictionaries
        :raises requests.RequestException: for HTTP or communication errors
        """
        image_list = self.list_images()
        return {i['name']: i for i in image_list}

    def get_image_info(self, name):
        """Get the metadata of an image given its name.

        None is returned if there is no image of that name.

        :rtype: dict or None
        :returns: a dictionary of type ``UserDatasetEntry``
        :raises requests.RequestException: for HTTP or communication errors
        """
        image_list = self.list_images()
        for image_info in image_list:
            if image_info['name'] == name:
                return image_info

    def delete_image_by_name(self, name):
        """Delete an image given its base name.

        Nothing is returned in case of sucess. In case of failure a
        `requests.HTTPError` is raised.

        :param str name: the base name of the image as known by the image
               service (original file name with .nii or .nii.gz stripped away)
        :raises requests.RequestException: for HTTP or communication errors
        :raises RuntimeError: if the image cannot be found on the server

        """
        image_info = self.get_image_info(name)
        if image_info is None:
            raise RuntimeError('No such image on the server')
        normalized_url = image_info['links']['normalized']
        self.delete_image(normalized_url)

    def upload_image_and_get_name(self, *args, **kwargs):
        """Upload an image and return its name.

        This method behaves exactly like
        `LowLevelImageServiceClient.upload_image`, except for its return type.

        :rtype: tuple
        :returns: a pair ``(name, nifti_extra)`` where ``name`` is a `str` that
                  identifies the dataset, and ``nifti_extra`` is a `dict` of
                  type ``NiftiExtra``.
        """
        nifti_extra = self.upload_image(*args, **kwargs)
        name = strip_nii_extension(nifti_extra['fileName'])
        return (name, nifti_extra)
