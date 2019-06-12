#!/usr/bin/env python

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
        "celery",
        "Flask",
        "Flask-Cors",
        "Flask-SQLAlchemy",
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
