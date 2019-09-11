Deployment on openshift-dev.hbp.eu
==================================

The deployment configuration is saved to `openshift-dev-export.yaml` by running
``oc get -o yaml --export is,bc,dc,svc,route,pvc``. See
https://collab.humanbrainproject.eu/#/collab/38996/nav/270508 for instructions
for restoring a working deployment using this snapshot.

For the record, here are the steps that were used to create this OpenShift project:

#. Create the project / navigate to the project
#. Configure the Flask instance

   #. Add to Project -> Browse Catalog
   #. Choose Python (does not matter, configuration will be changed later). Hit Next
   #. In Step 2 (Configuration), hit `advanced options` and enter these values:

      - `cortical-voluba-flask` as Name
      - `https://github.com/HumanBrainProject/cortical-voluba.git` as Git Repository
      - `dev` as Git Reference
      - Under Routing, enter `cortical-voluba.apps-dev.hbp.eu` as Hostname
      - Under Routing, check `Secure route`
      - Under `Build Configuration`, uncheck `Launch the first build when the build configuration is created`

   #. Hit `Create` at the bottom of the page
   #. Follow the instructions to configure the GitHub webhook
   #. Change the build configuration to use the `Docker` build strategy:

      #. Go to `Builds` -> `Builds` -> `cortical-voluba-flask` -> `Actions` -> `Edit YAML`
      #. Replace the contents of the `strategy` key by::

           dockerStrategy:
             dockerfilePath: Dockerfile.flask
           type: Docker

      #. Hit `Save`

   #. Trigger the build by hitting `Start Build`
   #. Configure the Flask instance

      #. Go to `Applications` -> `Deployments` -> `cortical-voluba-flask` -> `Configuration`
      #. Under `Volumes`, hit `Add Config Files`
      #. Click `Create Config Map`

         - `Name` = `instance-dir`
         - `Key` = `config.py`
         - `Value`::

             import os
             CELERY_BROKER_URL = 'redis://:' + os.environ['REDIS_PASSWORD'] + '@redis:6379/0'
             CELERY_RESULT_BACKEND = CELERY_BROKER_URL
             CORS_ORIGINS = r'https://voluba(-dev)?\.apps(-dev)?\.hbp\.eu'
             PROXY_FIX = {
                 'x_for': 1,
                 'x_host': 1,
                 'x_port': 1,
                 'x_proto': 1,
             }
             TEMPLATE_EQUIVOLUMETRIC_DEPTH = '/static-data/BigBrain_equivolumetric_depth.nii.gz'

      #. Hit `Create`
      #. Back in the `Add Config Files` page, choose the newly created `instance-dir` as `Source`
      #. Set `Mount Path` = `/instance`
      #. Hit `Add`
      #. Go to the `Environment` tab and add these variables:

         - `INSTANCE_PATH` = `/instance`
         - `REDIS_PASSWORD` from Secret `redis/database-password`

#. Configure the Celery instance

   #. Add to Project -> Browse Catalog
   #. Choose Python (does not matter, configuration will be changed later). Hit Next
   #. In Step 2 (Configuration), hit `advanced options` and enter these values:

      - `cortical-voluba-celery` as Name
      - `https://github.com/HumanBrainProject/cortical-voluba.git` as Git Repository
      - `dev` as Git Reference
      - uncheck `Create a route to the application`
      - Under `Build Configuration`, uncheck `Launch the first build when the build configuration is created`

   #. Hit `Create` at the bottom of the page
   #. Follow the instructions to configure the GitHub webhook
   #. Change the build configuration to use the `Docker` build strategy:

      #. Go to `Builds` -> `Builds` -> `cortical-voluba-flask` -> `Actions` -> `Edit YAML`
      #. Replace the contents of the `strategy` key by::

           dockerStrategy:
             dockerfilePath: Dockerfile.celery
           type: Docker

      #. Hit `Save`

   #. Trigger the build by hitting `Start Build`
   #. Configure the Celery instance

      #. Go to `Applications` -> `Deployments` -> `cortical-voluba-celery` -> `Configuration`
      #. Under `Volumes`, hit `Add Config Files`
      #. Set `Source` = `instance-dir`, `Mount Path` = `/instance`
      #. Hit `Add`
      #. Go to the `Environment` tab and add these variables:

         - `INSTANCE_PATH` = `/instance`
         - `REDIS_PASSWORD` from Secret `redis/database-password`

   #. Create a volume to hold the static data (equivolumetric depth for BigBrain)

      #. Go to `Applications` -> `Deployments` -> `cortical-voluba-flask` -> `Configuration`
      #. Under `Volumes`, hit `Add Storage`
      #. Hit `Create Storage`
      #. Set `Name` = `static-data`, `Size` = `1 GiB`
      #. Hit `Create`
      #. Set `Mount Path` = `/static-data`
      #. For the moment *do not* set `Read only` (we will need to connect to a Celery container for writing the data into the Volume).
      #. Hit `Add`

   #. Upload the static data (equivolumetric depth for BigBrain). We follow the method described on https://blog.openshift.com/transferring-files-in-and-out-of-containers-in-openshift-part-3/

      #. Install the OpenShift Command-Line Tools by following the instructions on https://openshift-dev.hbp.eu/console/command-line
      #. Log in using the CLI (Under your name on the top right corner, hit `Copy Login Command` and paste it into a terminal)
      #. Switch to the project (``oc project cortical-voluba``)
      #. Use `oc get pods` to get the name of the running Celery pod
      #. Copy the data using ``oc rsync static-data/ cortical-voluba-celery-5-z4l2n:/static-data/`` (replace `cortical-voluba-celery-5-z4l2n` with the pod name from the previous step).
      #. Verify the contents of the directory with ``oc rsh cortical-voluba-celery-5-z4l2n ls -l /static-data``
      #. The `static-data` volume mount can now be switched to read-only: go to `Applications` -> `Deployments` -> `cortical-voluba-celery` -> `Actions` -> `Edit YAML`, then add a key `readOnly: true` to the element of the `volumeMounts` dictionary::

           - mountPath: /static-data
             name: static-data
             readOnly: true

#. Configure the Redis instance

   #. `Add to project` -> `Browse Catalog`
   #. Choose `Redis (Ephemeral)` (FIXME: production should probably use persistent storage)
   #. Under `Configuration`, leave default values
   #. Under `Binding`, choose `Create a secret...`
   #. Hit `Create`