=====================================
YAML File Value Overriding in Hubploy
=====================================

There are several ``.yaml`` files present in the hubploy-template repository. It can be unclear 
which settings go in which files. This topic hopes to clear that up a bit. As a reminder, here is 
the directory structure that Hubploy expects (minimized for focus on the yaml files)::

	hubploy-template/
	├── .github
	│   └── workflows
	│       ├── deploy.yaml
	│       └── image-build.yaml
	├── deployments
	│   └── hub
	│       ├── config
	│       │   ├── common.yaml
	│       │   ├── prod.yaml
	│       │   └── staging.yaml
	│       ├── hubploy.yaml
	│       └── secrets
	│           ├── aws-ecr-config.cfg
	│           ├── aws-eks-config.cfg
	│           ├── prod.yaml
	│           └── staging.yaml
	└── hub
	    ├── Chart.yaml
	    ├── requirements.lock
	    ├── requirements.yaml
	    ├── templates
	    │   ├── jupyter-notebook-config.yaml
	    │   └── nfs-pvc.yaml
	    └── values.yaml


GitHub Action Files
-------------------

The two files under ``.github/workflows/`` manage individual GitHub Actions for Hubploy. They are 
independent of most of the rest of Hubploy.


JupyterHub Deployment Files
---------------------------

The main value files are related to the JupyterHub Helm release. The lowest level of these are 
specified in ``hub/values.yaml`` via::

	jupyterhub: {}

The braces can be removed once there are yaml values in the file, but they are needed if this block
is empty. Appropriate values to put in this file are those that will span both versions of all 
JupyterHubs that you will deploy with Hubploy, as this file will be used for all of them.

The next file in the heirarchy is ``deployments/hub/config/common.yaml``. This file covers 
deployment values that are common to both the staging and production hubs that Hubploy named 
"hub," or what you had changed that folder name to. If there are multiple JupyterHubs being managed
, each one will have a ``common.yaml``. Values in this file will overwrite ``hub/values.yaml``.

The next two files in the heirarchy are also in the config folder: ``staging.yaml`` and 
``prod.yaml``. These contain values for the staging and production hubs, respectively. Values in 
these files will override the previous two. These two files do not override each other ever since they are for two different hubs.

The last files in the heirarchy are under the ``secrets`` directory. These are set in a folder that
we tell git-crypt to encrypt when pushing code to GitHub. In general, there shouldn't be anything 
in these files that overwrites the other ``staging.yaml`` and ``prod.yaml``. It is more expected 
that values in these files will overwrite default credentials or paths present in the first two 
files.

A quick summary of the heirarchy follows in descending priority (lower overwrites higher) 
but ascending generality (higher applies to more hubs)::

	hub/values.yaml
		deployments/hub/config/common.yaml
			deployments/hub/config/staging.yaml
			deployments/hub/config/prod.yaml
			deployments/hub/secrets/staging.yaml
			deployments/hub/secrets/prod.yaml


Local Hub Helm Chart Files
--------------------------

Everything under the hub folder is related to the Helm Chart. In ``Chart.yaml``, the main 
specification is what the Chart is named and what version you are on. In ``requirements.yaml``, 
the JupyterHub Helm chart is listed as the only dependency and you can pick a specific version.
``values.yaml`` is used to provide the lowest level of values for JupyterHub configuration and 
other deployment pieces that are present in the ``templates/`` folder or other dependencies 
you choose to add to the Helm chart.

