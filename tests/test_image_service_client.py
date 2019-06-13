# Copyright (c) 2019 CEA
# Author: Yann Leprince <yann.leprince@ylep.fr>

import gzip
import io

import pytest
import requests

import cortical_voluba.image_service as image_service
from cortical_voluba.image_service import ImageServiceClient


DUMMY_IMAGE_LIST = [
    {
        "extra": {
            "data": {},
            "fileName": "imagename.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {},
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/imagename",
        },
        "name": "imagename",
        "visibility": "private",
    }
]

DUMMY_NIFTI_EXTRA = {
    "fileName": "imagename.nii.gz",
    "fileSize": 149665752,
    "fileSizeUncompressed": 1296926752,
    "neuroglancer": {},
    "nifti": {},
    "warnings": [],
}


@pytest.mark.parametrize('base_url', [
    'http://h.test/b/',
    'http://h.test/b',
])
def test_list_images(base_url, requests_mock):
    client = ImageServiceClient(base_url)

    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)
    ret = client.list_images()
    assert ret == DUMMY_IMAGE_LIST

    requests_mock.get('http://h.test/b/list', status_code=401)
    with pytest.raises(requests.HTTPError):
        client.list_images()


def test_list_images_by_name(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)
    d = client.list_images_by_name()
    assert d == {'imagename': DUMMY_IMAGE_LIST[0]}

    requests_mock.get('http://h.test/b/list', status_code=401)
    with pytest.raises(requests.HTTPError):
        client.list_images_by_name()


def test_get_image_info(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)
    d = client.get_image_info('imagename')
    assert d == DUMMY_IMAGE_LIST[0]

    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)
    d = client.get_image_info('nonexistent')
    assert d is None


def test_delete_image(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.delete('http://h.test/b/nifti/s3cr3t/imagename')
    client.delete_image('/nifti/s3cr3t/imagename')
    client.delete_image('nifti/s3cr3t/imagename')
    client.delete_image('http://h.test/b/nifti/s3cr3t/imagename')

    requests_mock.delete('http://h.test/b/nifti/s3cr3t/imagename',
                         status_code=401)
    with pytest.raises(requests.HTTPError):
        client.delete_image('http://h.test/b/nifti/s3cr3t/imagename')


def test_delete_image_by_name(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/list', json=DUMMY_IMAGE_LIST)
    requests_mock.delete('http://h.test/b/nifti/s3cr3t/imagename')
    client.delete_image_by_name('imagename')
    with pytest.raises(RuntimeError):
        client.delete_image_by_name('nonexistent')

    requests_mock.delete('http://h.test/b/nifti/s3cr3t/imagename',
                         status_code=401)
    with pytest.raises(requests.HTTPError):
        client.delete_image_by_name('imagename')


def test_download_nifti(requests_mock, monkeypatch):
    # Work around a bug in requests_mock (hangs forever if chunk_size=None).
    monkeypatch.setattr(image_service, '_DOWNLOAD_CHUNK_SIZE', 4096)
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/download/imagename.nii',
                      content=b'Nifti contents')
    buf = io.BytesIO()
    client.download_nifti('imagename', buf)
    assert buf.getvalue() == b'Nifti contents'


def test_download_compressed_nifti(requests_mock, monkeypatch):
    # Work around a bug in requests_mock (hangs forever if chunk_size=None).
    monkeypatch.setattr(image_service, '_DOWNLOAD_CHUNK_SIZE', 4096)
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/download/imagename.nii.gz',
                      content=gzip.compress(b'Nifti contents'))
    buf = io.BytesIO()
    client.download_compressed_nifti('imagename', buf)
    assert gzip.decompress(buf.getvalue()) == b'Nifti contents'

    requests_mock.get('http://h.test/b/download/imagename.nii.gz',
                      status_code=404)
    requests_mock.get('http://h.test/b/download/imagename.nii',
                      content=b'Nifti contents')
    buf = io.BytesIO()
    client.download_compressed_nifti('imagename', buf)
    assert gzip.decompress(buf.getvalue()) == b'Nifti contents'


def test_download_original_file(requests_mock, monkeypatch):
    # Work around a bug in requests_mock (hangs forever if chunk_size=None).
    monkeypatch.setattr(image_service, '_DOWNLOAD_CHUNK_SIZE', 4096)
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/download/imagename',
                      content=b'Nifti contents',
                      headers={'Content-Disposition':
                               'attachment; filename="imagename.nii"'})
    buf = io.BytesIO()
    file_name = client.download_original_file('imagename', buf)
    assert buf.getvalue() == b'Nifti contents'
    assert file_name == 'imagename.nii'

    client = ImageServiceClient('http://h.test/b/')
    requests_mock.get('http://h.test/b/download/imagename',
                      content=gzip.compress(b'Nifti contents'),
                      headers={'Content-Disposition':
                               'attachment; filename=imagename.nii.gz'})
    buf = io.BytesIO()
    file_name = client.download_original_file('imagename', buf)
    assert gzip.decompress(buf.getvalue()) == b'Nifti contents'
    assert file_name == 'imagename.nii.gz'


def test_upload_image(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.post('http://h.test/b/upload', json=DUMMY_NIFTI_EXTRA)

    image_buf = io.BytesIO(b'Nifti contents')
    image_buf.name = 'imagename.nii'
    nifti_extra = client.upload_image(image_buf)
    assert nifti_extra == DUMMY_NIFTI_EXTRA

    image_buf = io.BytesIO(b'Nifti contents')
    nifti_extra = client.upload_image(image_buf, file_name='imagename.nii')
    assert nifti_extra == DUMMY_NIFTI_EXTRA

    image_buf = io.BytesIO(b'Nifti contents')
    nifti_extra = client.upload_image(image_buf, file_name='imagename.nii',
                                      segmentation=True)
    assert nifti_extra == DUMMY_NIFTI_EXTRA


def test_preflight_image(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.post('http://h.test/b/preflight', json=DUMMY_NIFTI_EXTRA)
    image_buf = io.BytesIO(b'Nifti contents')
    nifti_extra = client.preflight_image(image_buf, file_name='imagename.nii')
    assert nifti_extra == DUMMY_NIFTI_EXTRA


def test_upload_image_and_get_name(requests_mock):
    client = ImageServiceClient('http://h.test/b/')
    requests_mock.post('http://h.test/b/upload', json=DUMMY_NIFTI_EXTRA)

    image_buf = io.BytesIO(b'Nifti contents')
    name, nifti_extra = client.upload_image_and_get_name(
        image_buf, file_name='imagename.nii')
    assert name == 'imagename'
    assert nifti_extra == DUMMY_NIFTI_EXTRA

    image_buf = io.BytesIO(gzip.compress(b'Nifti contents'))
    name, nifti_extra = client.upload_image_and_get_name(
        image_buf, file_name='imagename.nii.gz')
    assert name == 'imagename'
    assert nifti_extra == DUMMY_NIFTI_EXTRA
