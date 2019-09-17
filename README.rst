VoluBA backend for non-linear depth-informed alignment of cortical patches

A test instance of this back-end (following the ``dev`` branch) is deployed on https://cortical-voluba.apps-dev.hbp.eu/. The corresponding front-end is https://voluba-dev.apps-dev.hbp.eu/.

Running a local development server::

  pip install -e .
  export FLASK_APP=cortical_voluba
  flask run


The compute-intensive alignment runs on uses a distributed task queue that uses
`Celery <http://www.celeryproject.org/>`_. It needs to be configured with a
broker (Redis was tested successfully), see `First steps with Celery`_.
The queue runner needs to be started separately::

  celery --app=cortical_voluba worker --loglevel=info


Contributing
============

This repository uses `pre-commit`_ to ensure that all committed code follows minimal quality standards. Please install it and configure it to run as a pre-commit hook in your local repository::

  pip install pre-commit
  pre-commit install


.. _Celery: http://www.celeryproject.org/
.. _`First steps with Celery`: http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
.. _pre-commit: https://pre-commit.com/
