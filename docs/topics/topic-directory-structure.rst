======================================
Hubploy's Expected Directory Structure
======================================

Hubploy expects the directory structure shown in the 
`hubploy template repository <https://github.com/yuvipanda/hubploy-template>`_. The folders must be
set up in this fashion::

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
	│       ├── image
	│       │   ├── ipython_config.py
	│       │   ├── postBuild
	│       │   └── requirements.txt
	│       └── secrets
	│           ├── aws-ecr-config.cfg
	│           ├── aws-eks-config.cfg
	│           ├── prod.yaml
	│           └── staging.yaml
	├── hub
	│   ├── Chart.yaml
	│   ├── requirements.lock
	│   ├── requirements.yaml
	│   ├── templates
	│   │   ├── jupyter-notebook-config.yaml
	│   │   └── nfs-pvc.yaml
	│   └── values.yaml
	├── LICENSE
	├── README.rst
	└── requirements.txt


.github Folder
--------------

This folder houses the GitHub Workflow files that you can use for Continuous Integration with 
Hubploy. ``deploy.yaml`` will attempt to build the staging or production JupyterHub upon updates 
to the respective GitHub branch. ``image-build.yaml`` will attempt to build the JupyterHub image 
upon updates to only the production branch.

These files have references to a Docker image that uses Hubploy. You can change this image. Some 
options are listed in :doc:`../howto/hubploy-setup-dev-environment`.


Deployments Folder
------------------

The deployments folder can hold multiple subfolders, but each must have the same structure as the 
hub folder. Renaming the hub folder is part of the recommended workflow for deploying a JupyterHub.
Each subfolder directly under deployments needs a different name so that Hubploy can distinguish 
between them in Hubploy commands.

Each JupyterHub is deployed with YAML files. The YAML files listed under deployments must have 
these names.

Hubploy takes in secrets for credentialing via the ``.cfg`` files. You can rename these freely, 
just be sure to put the proper names into ``hubploy.yaml``.

The image folder can have additional files depending on how you are building the image. See more 
in the image building how-to. If you are not specifying ``images`` in your ``hubploy.yaml`` file,
the ``images/`` folder can be deleted.


Hub Folder
----------

The hub folder houses a local `Helm Chart`_. This chart and folder can be renamed, but the name 
needs to be present in Hubploy commands, the files in the ``.github`` folder, and in ``Chart.yaml``
. Modification of the files in here should be done as you would change a Helm Chart.


.. _Helm Chart: https://helm.sh/docs/intro/using_helm/
