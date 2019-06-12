# Copyright 2019  CEA
# Author: Yann Leprince <yann.leprince@cea.fr>

"""VoluBA backend for non-linear depth-informed alignment of cortical patches.
"""

# Version used by setup.py and docs/conf.py (parsed with a regular expression).
#
# Release checklist (based on https://packaging.python.org/):
# 1.  Ensure that tests pass for all supported Python version (Travis CI),
#     ensure that the API documentation is complete (sphinx-apidoc --separate
#     -o docs/api cortical_voluba);
# 2.  Update the release notes;
# 3.  Run check-manifest;
# 4.  Bump the version number in this file;
# 5.  pip install -U setuptools wheel twine
# 6.  python setup.py sdist bdist_wheel
# 7.  twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# 8.  Commit the updated version number
# 9.  Tag the commit (git tag -a vX.Y.Z). The release notes for the last
#     version should be converted to plain text and included in the tag
#     message:
#     pandoc -t plain docs/release-notes.rst
# 10. Bump the version number in this file to something that ends with .dev0
#     and commit
# 11. Push the master branch and the new tag to Github
# 12. twine upload dist/*
__version__ = "0.1.0.dev0"
