Deployment on openshift-dev.hbp.eu
==================================

The deployment configuration is saved to `openshift-dev-export.yaml` by running
``oc get -o yaml --export is,bc,dc,svc,route,pvc``. See
https://collab.humanbrainproject.eu/#/collab/38996/nav/270508 for instructions
for restoring a working deployment using this snapshot.

For the record, here are the steps that were used to create this OpenShift project:

1. Create the project / navigate to the project

2. Configure the Flask instance
   1. Add to Project -> Browse Catalog
   2. Choose Python (does not matter, configuration will be changed later). Hit Next
   3. In Step 2 (Configuration), hit `advanced options` and enter these values:
      - `cortical-voluba-flask` as Name
      - `https://github.com/HumanBrainProject/cortical-voluba.git` as Git Repository
      - `dev` as Git Reference
      - Under Routing, enter `cortical-voluba.apps-dev.hbp.eu` as Hostname
      - Under Routing, check `Secure route`
      - Under `Build Configuration`, uncheck `Launch the first build when the build configuration is created`
   4. Hit `Create` at the bottom of the page
   5. Follow the instructions to configure the GitHub webhook
   6. Change the build configuration to use the `Docker` build strategy:
      1. Go to `Builds` -> `Builds` -> `cortical-voluba-flask` -> `Actions` -> `Edit YAML`
      2. Replace the contents of the `strategy` key by::

           dockerStrategy:
             dockerfilePath: Dockerfile.flask
           type: Docker

      3. Hit `Save`
   7. Trigger the build by hitting `Start Build`
   8. Configure the Flask instance
      1. Go to `Applications` -> `Deployments` -> `cortical-voluba-flask` -> `Configuration`
      2. Under `Volumes`, hit `Add Config Files`
      3. Click `Create Config Map`
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

      4. Hit `Create`
      5. Back in the `Add Config Files` page, choose the newly created `instance-dir` as `Source`
      6. Set `Mount Path` = `/instance`
      7. Hit `Add`
      8. Go to the `Environment` tab and add these variables:
         - `INSTANCE_PATH` = `/instance`
         - `REDIS_PASSWORD` from Secret `redis/database-password`

3. Configure the Celery instance
   1. Add to Project -> Browse Catalog
   2. Choose Python (does not matter, configuration will be changed later). Hit Next
   3. In Step 2 (Configuration), hit `advanced options` and enter these values:
      - `cortical-voluba-celery` as Name
      - `https://github.com/HumanBrainProject/cortical-voluba.git` as Git Repository
      - `dev` as Git Reference
      - uncheck `Create a route to the application`
      - Under `Build Configuration`, uncheck `Launch the first build when the build configuration is created`
   4. Hit `Create` at the bottom of the page
   5. Follow the instructions to configure the GitHub webhook
   6. Change the build configuration to use the `Docker` build strategy:
      1. Go to `Builds` -> `Builds` -> `cortical-voluba-flask` -> `Actions` -> `Edit YAML`
      2. Replace the contents of the `strategy` key by::

           dockerStrategy:
             dockerfilePath: Dockerfile.celery
           type: Docker

      3. Hit `Save`
   7. Trigger the build by hitting `Start Build`
   8. Configure the Celery instance
      1. Go to `Applications` -> `Deployments` -> `cortical-voluba-celery` -> `Configuration`
      2. Under `Volumes`, hit `Add Config Files`
      3. Set `Source` = `instance-dir`, `Mount Path` = `/instance`
      4. Hit `Add`
      5. Go to the `Environment` tab and add these variables:
         - `INSTANCE_PATH` = `/instance`
         - `REDIS_PASSWORD` from Secret `redis/database-password`
   9. Create a volume to hold the static data (equivolumetric depth for BigBrain)
      1. Go to `Applications` -> `Deployments` -> `cortical-voluba-flask` -> `Configuration`
      2. Under `Volumes`, hit `Add Storage`
      3. Hit `Create Storage`
      4. Set `Name` = `static-data`, `Size` = `1 GiB`
      5. Hit `Create`
      6. Set `Mount Path` = `/static-data`
      7. For the moment *do not* set `Read only` (we will need to connect to a Celery container for writing the data into the Volume).
      8. Hit `Add`
   10. Upload the static data (equivolumetric depth for BigBrain). We follow the method described on https://blog.openshift.com/transferring-files-in-and-out-of-containers-in-openshift-part-3/
       1. Install the OpenShift Command-Line Tools by following the instructions on https://openshift-dev.hbp.eu/console/command-line
       2. Log in using the CLI (Under your name on the top right corner, hit `Copy Login Command` and paste it into a terminal)
       3. Switch to the project (``oc project cortical-voluba``)
       4. Use `oc get pods` to get the name of the running Celery pod
       5. Copy the data using ``oc rsync static-data/ cortical-voluba-celery-5-z4l2n:/static-data/`` (replace `cortical-voluba-celery-5-z4l2n` with the pod name from the previous step).
       6. Verify the contents of the directory with ``oc rsh cortical-voluba-celery-5-z4l2n ls -l /static-data``
       7. The `static-data` volume mount can now be switched to read-only: go to `Applications` -> `Deployments` -> `cortical-voluba-celery` -> `Actions` -> `Edit YAML`, then add a key `readOnly: true` to the element of the `volumeMounts` dictionary::

            - mountPath: /static-data
              name: static-data
              readOnly: true

4. Configure the Redis instance
   1. `Add to project` -> `Browse Catalog`
   2. Choose `Redis (Ephemeral)` (FIXME: production should probably use persistent storage)
   3. Under `Configuration`, leave default values
   4. Under `Binding`, choose `Create a secret...`
   5. Hit `Create`
