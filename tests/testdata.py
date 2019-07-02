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

import gzip


DUMMY_IMAGE_LIST = [
    {
        "extra": {
            "data": {},
            "fileName": "seg.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {
                "type": "segmentation",
            },
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/seg",
        },
        "name": "seg",
        "visibility": "private",
    },
    {
        "extra": {
            "data": {},
            "fileName": "image.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {
                "type": "image",
            },
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/img",
        },
        "name": "img",
        "visibility": "private",
    },
    {
        "extra": {
            "data": {},
            "fileName": "depth_map.nii.gz",
            "fileSize": 149665752,
            "fileSizeUncompressed": 1296926752,
            "neuroglancer": {
                "type": "image",
            },
            "nifti": {},
            "uploaded": "2019-06-04T10:22:49.543194Z",
            "warnings": [],
        },
        "links": {
            "normalized": "/nifti/s3cr3t/depthmap",
        },
        "name": "depthmap",
        "visibility": "private",
    },
]


DUMMY_NIFTI_GZ = gzip.compress(b'dummy-nifti-gz')
