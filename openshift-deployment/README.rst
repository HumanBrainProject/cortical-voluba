Deploying to an OpenShift cluster
=================================

As an example, these are the instructions for restoring the deployment on https://okd-dev.hbp.eu/.

#. You can use the deployment configuration saved in `<openshift-dev-export.yaml>`_ provided in the repository as a starting point. Edit the route contained in this file to use the correct URL.
#. Create the project named `cortical-voluba` on https://okd-dev.hbp.eu/
#. Log in using the command-line ``oc`` tool (https://okd-dev.hbp.eu/console/command-line), switch to the `cortical-voluba` project with ``oc project cortical-voluba``
#. Import the objects from your edited YAML file using ``oc create -f openshift-dev-export.yaml``
#. Re-create the Persistent Volume Claims and upload the data (see below).
#. Edit the Config Maps if needed, re-create the needed Secrets (namely ``redis/database-password``).
#. Start the build. The deployment should follow automatically.
#. Go to `Builds` -> `Builds` -> `cortical-voluba` -> `Configuration`, copy the GitHub Webhook URL and configure it into the GitHub repository (https://github.com/HumanBrainProject/cortical-voluba/settings/hooks). Make sure to set the Content Type to ``application/json``.


Deployment on okd-dev.hbp.eu
============================

The deployment configuration is saved to `<openshift-dev-export.yaml>`_ by running ``oc get -o yaml --export is,bc,dc,svc,route,pvc,cm,horizontalpodautoscaler > openshift-dev-export.yaml`` (`status` information is stripped manually).

For the record, here are the steps that were used to create this OpenShift project on https://okd-dev.hbp.eu/:

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
      - Under Routing, set `Insecure Traffic` to `Redirect`
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

   #. Add post-build tests and tweak build configuration

      #. Go to `Builds` -> `Builds` -> `cortical-voluba-flask` -> `Actions` -> `Edit`. Click on `advanced options`.
      #. Under `Image Configuration`, check `Always pull the builder image from the docker registry, even if it is present locally`
      #. Under `Post-Commit Hooks`, check `Run build hooks after image is built`. Choose `Hook Type` = `Shell Script` and enter the following Script::

           set -e
           # Without PIP_IGNORE_INSTALLED=0 the Debian version of pip would
           # re-install all dependencies in the user's home directory
           # (https://github.com/pypa/pip/issues/4222#issuecomment-417672236)
           PIP_IGNORE_INSTALLED=0 python3 -m pip install --user /source[tests]
           cd /source
           python3 -m pytest tests/

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

   #. Add Health Checks
      #. Go to `Applications` -> `Deployments` -> `cortical-voluba-flask` -> `Actions` -> `Edit Health Checks`
      #. Add a `Readiness Probe` of type `HTTP GET`, using `Path` = `/health`, setting some `Initial Delay` (e.g. 5 seconds) and `Timeout` (e.g. 10 seconds)
      #. Add a `Liveness Probe` of type `HTTP GET`, using `Path` = `/health`, setting a long `Timeout` (e.g. 60 seconds)
      #. Hit `Save`

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

      #. Go to `Builds` -> `Builds` -> `cortical-voluba-celery` -> `Actions` -> `Edit YAML`
      #. Replace the contents of the `strategy` key by::

           dockerStrategy:
             dockerfilePath: Dockerfile.celery
           type: Docker

      #. Hit `Save`

   #. Add post-build tests and tweak build configuration

      #. Go to `Builds` -> `Builds` -> `cortical-voluba-celery` -> `Actions` -> `Edit`. Click on `advanced options`.
      #. Under `Image Configuration`, check `Always pull the builder image from the docker registry, even if it is present locally`
      #. Under `Post-Commit Hooks`, check `Run build hooks after image is built`. Choose `Hook Type` = `Shell Script` and enter the following Script::

           set -e
           # Without PIP_IGNORE_INSTALLED=0 the Debian version of pip would
           # re-install all dependencies in the user's home directory
           # (https://github.com/pypa/pip/issues/4222#issuecomment-417672236)
           PIP_IGNORE_INSTALLED=0 python3 -m pip install --user /source[tests]
           cd /source
           python3 -m pytest tests/

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

      #. (optional) Add an Autoscaler so that OpenShift can automatically adapt the number of Celery workers to the number of ongoing computations: go to `Actions` -> `Add Autoscaler`, set `Max pods` to 5, and `CPU Request Target` to 50%. Validate by clicking `Save`.

   #. Create a volume to hold the static data (equivolumetric depth for BigBrain)

      #. Go to `Applications` -> `Deployments` -> `cortical-voluba-celery` -> `Configuration`
      #. Under `Volumes`, hit `Add Storage`
      #. Hit `Create Storage`
      #. Set `Name` = `static-data`, `Size` = `1 GiB`
      #. Hit `Create`
      #. Set `Mount Path` = `/static-data`
      #. Set the mount to `Read only`
      #. Hit `Add`

   #. Upload the static data (equivolumetric depth for BigBrain). We follow the method described on https://blog.openshift.com/transferring-files-in-and-out-of-containers-in-openshift-part-3/

      #. Install the OpenShift Command-Line Tools by following the instructions on https://okd-dev.hbp.eu/console/command-line
      #. Log in using the CLI (Under your name on the top right corner, hit `Copy Login Command` and paste it into a terminal)
      #. Switch to the project (``oc project cortical-voluba``)
      #. Run a dummy pod for rsync transfer with ``oc run dummy --image ylep/oc-rsync-transfer``
      #. Mount the volume against the dummy pod ``oc set volume dc/dummy --add --name=tmp-mount --claim-name=static-data --mount-path /static-data``
      #. Wait for the deployment to be complete with ``oc rollout status dc/dummy``
      #. Get the name of the dummy pod with ``oc get pods --selector run=dummy``
      #. Copy the data using ``oc rsync --compress=true --progress=true static-data/ dummy-2-7tdml:/static-data/`` (replace `dummy-2-7tdml` with the pod name from the previous step).
      #. Verify the contents of the directory with ``oc rsh dummy-2-7tdml ls -l /static-data``
      #. Delete everything related to the temporary pod with ``oc delete all --selector run=dummy``

   #. Add Health Checks (TODO: figure out how to check for celery worker, I could not figure out how to use ``celery inspect ping``).

#. Configure the Redis instance

   #. `Add to project` -> `Browse Catalog`
   #. Choose `Redis (Ephemeral)` (FIXME: production should probably use persistent storage)
   #. Under `Configuration`, leave default values
   #. Under `Binding`, choose `Create a secret...`
   #. Hit `Create`
