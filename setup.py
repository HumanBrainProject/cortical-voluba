#!/usr/bin/env python

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

import codecs
import os.path
import re
import sys

import setuptools


here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# Remember keep synchronized with the list of dependencies in tox.ini
tests_require = [
    "pytest",
    "requests-mock",
]

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest-runner"] if needs_pytest else []


setuptools.setup(
    name="cortical-voluba",
    version=find_version("cortical_voluba", "__init__.py"),
    description="VoluBA backend for non-linear depth-informed alignment of cortical patches",
    long_description=read("README.rst"),
    long_description_content_type='text/x-rst',
    author="Yann Leprince",
    author_email="yann.leprince@cea.fr",
    keywords="neuroimaging",
    packages=["cortical_voluba"],
    install_requires=[
        "Flask",
        "Flask-Cors",
        "celery",
        "redis",
        "marshmallow ~= 3.0.0rc6",
    ],
    python_requires="~= 3.5",
    extras_require={
        "dev": tests_require + [
            "check-manifest",
            "flake8",
            "pep8-naming",
            "pytest-cov",
            "readme_renderer",
            "sphinx",
            "tox",
        ],
    },
    setup_requires=pytest_runner,
    tests_require=tests_require,
)
