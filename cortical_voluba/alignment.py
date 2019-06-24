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

import shutil
import time


def estimate_deformation(depth_map_path, transformation_matrix, landmark_pairs,
                         work_dir):
    time.sleep(5)


def transform_image(input_image_path, resampled_image_path, work_dir):
    shutil.copy(input_image_path, resampled_image_path)  # MOCK
    time.sleep(2)
