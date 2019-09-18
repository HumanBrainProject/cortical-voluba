VoluBA backend for non-linear depth-informed alignment of cortical patches

.. image:: https://api.travis-ci.com/HumanBrainProject/cortical-voluba.svg?branch=master
   :target: https://travis-ci.com/HumanBrainProject/cortical-voluba
   :alt: Travis Build Status


Public deployments
==================

A test deployment (following the ``dev`` branch) is deployed on https://cortical-voluba.apps-dev.hbp.eu. |uptime-dev|  The corresponding front-end is https://voluba-dev.apps-dev.hbp.eu/.

The public deployments are managed by OpenShift clusters, the relevant configuration is described in `<openshift-deployment/>`_.


Development
===========

The backend uses `highres-cortex`_ and `ANTs`_, both of which must be available the ``PATH``. You can use `<docker-highres-cortex/script.sh>`_ to build a Docker image containing highres-cortex (a pre-built image is available on Docker Hub: `ylep/highres-cortex <https://hub.docker.com/r/ylep/highres-cortex>`_). You can use `<docker-highres-cortex-ants/Dockerfile>`_ to add the relevant ANTs tools (a pre-built image is available on Docker Hub: `ylep/highres-cortex-ants <https://hub.docker.com/r/ylep/highres-cortex-ants>`_).

The compute-intensive alignment runs on a task queue that uses `Celery <http://www.celeryproject.org/>`_. It needs to be configured with a broker (Redis was tested successfully), see `First steps with Celery`_. The queue runner needs to be started separately::

Useful commands for development:

.. code-block:: shell

  git clone https://github.com/HumanBrainProject/cortical-voluba.git

  # Install in a virtual environment
  cd cortical-voluba
  python3 -m venv venv/
  . venv/bin/activate
  pip install -e .[dev]

  export FLASK_APP=hbp_spatial_backend
  flask run  # run a local development server
  celery --app=cortical_voluba worker --loglevel=info  # run the task queue

  # Tests
  pytest  # run tests
  pytest --cov=hbp_spatial_backend --cov-report=html  # detailed test coverage report
  tox  # run tests under all supported Python versions

  # Please install pre-commit if you intend to contribute
  pip install pre-commit
  pre-commit install  # install the pre-commit hook


Contributing
============

This repository uses `pre-commit`_ to ensure that all committed code follows minimal quality standards. Please install it and configure it to run as a pre-commit hook in your local repository (see above).


.. |uptime-dev| image:: https://img.shields.io/uptimerobot/ratio/7/m783468854-2ce9835116702e502b149972?style=flat-square
   :alt: Weekly uptime ratio of the development instance
.. _highres-cortex: https://github.com/neurospin/highres-cortex
.. _ANTs: http://stnava.github.io/ANTs/
.. _Celery: http://www.celeryproject.org/
.. _`First steps with Celery`: http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
.. _pre-commit: https://pre-commit.com/
