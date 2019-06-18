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

import importlib

import pytest


def test_instantiate_celery_app_outside_of_flask():
    # A single Python process is used by pytest, thus we force Python to import
    # the module again, so that initialization happens outside of create_app().
    import cortical_voluba.celery
    importlib.reload(cortical_voluba.celery)
    assert cortical_voluba.celery.celery_app is not None


@pytest.mark.usefixtures('flask_app')
def test_instantiate_celery_app_in_flask():
    import cortical_voluba.celery
    assert cortical_voluba.celery.celery_app is not None
