VoluBA backend for non-linear depth-informed alignment of cortical patches

A test instance of the front-end is deployed on https://voluba-dev.apps-dev.hbp.eu/

First-time initialization::

  pip install -e .
  export FLASK_APP=cortical_voluba
  flask initdb


Development server::

  export FLASK_APP=cortical_voluba
  flask run


The compute-intensive alignment runs on uses a distributed task queue that uses
`Celery_ <http://www.celeryproject.org/>`_. It needs to be configured with a
broker (Redis was tested successfully), see `First steps with Celery`_.
The queue runner needs to be started separately::

  celery -A cortical_voluba worker --loglevel=info


.. _Celery: http://www.celeryproject.org/
.. _`First steps with Celery`: http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
