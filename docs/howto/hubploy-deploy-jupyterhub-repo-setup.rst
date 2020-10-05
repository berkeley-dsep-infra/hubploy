=============================================================
How to Setup a Repository to Deploy a JupyterHub with Hubploy
=============================================================

This is a guide on how to deploy a JupyterHub with Hubploy. 

General Procedure:

* `Step 0: Setup Prerequisites`_
* `Step 1: Get the hubploy-template Repository`_
* `Step 2: Install Hubploy`_
* `Step 3: Configure the Hub`_
* `Step 4: Build and Push the Image`_
* `Step 5: Deploy the Staging Hub`_
* `Step 6: Deploy the Production Hub`_
* `Step 7: Setup git-crypt for Secrets`_
* `Step 8: GitHub Workflows`_


Step 0: Setup Prerequisites
===========================

Hubploy does not manage your cloud resources - only your *Kubernetes* resources. You should use 
some other means to create your cloud resources. Example infrastructure deployments can be found 
at the `terraform-deploy repository <https://github.com/pangeo-data/terraform-deploy>`_. At a 
minimum, Hubloy expects a Kubernetes cluster. Many installations want to use a shared file system 
for home directories, so in those cases you want to hvae that managed outside Hubploy as well.

You also need the following tools installed:

#. Your cloud vendor's commandline tool.

   * `Google Cloud SDK <https://cloud.google.com/sdk/>`_ for Google Cloud
   * `AWS CLI <https://aws.amazon.com/cli/>`_ for AWS
   * `Azure CLI <https://docs.microsoft.com/en-us/cli/azure/>`_ for Azure

#. A local install of `helm 3 <https://helm.sh/docs/intro/install/>`_. Helm 2 is also supported, 
   but requires the same version of Helm to be present locally and on the cluster. If you are sing 
   Helm 2, you can find both versions with ``helm version``.

#. A `docker environment <https://docs.docker.com/install/>`_ that you can use. This is only 
   needed when building images.


Step 1: Get the ``hubploy-template`` Repository
=================================================

There are a couple different options for acquiring the content in `this repository`_. 

* Use the repository as a template. Click the "Use this template" button on the GitHub 
  repository's page, then input your own repo name. You can then use ``git clone`` as normal to 
  get your repository onto your local machine.

* Fork the repository. 

* Clone it directly with ``git clone https://github.com/yuvipanda/hubploy-template.git``. The 
  disadvantage here is that you probably won't have permissions to push changes and will have to 
  only develop locally. Not recommended.


Step 2: Install Hubploy
=======================

.. code:: bash

   python3 -m venv .
   source bin/activate
   python3 -m pip install -r requirements.txt

This installs hubploy and its dependencies.


Step 3: Configure the Hub
=========================

Rename the Hub
--------------

Each directory inside ``deployments/`` represents an installation of JupyterHub. The default is 
called ``myhub``, but *please* rename it to something more descriptive. ``git commit`` the result 
as well.

.. code:: bash

   git mv deployments/myhub deployments/<your-hub-name>
   git commit


Fill in the Minimum Config Details
----------------------------------

You need to find all things marked TODO and fill them in. In particular,

#. ``hubploy.yaml`` needs information about where your docker registry & kubernetes cluster is, 
   and paths to access keys as well. These access key files should be in the deployment's
   ``secret/`` folder.
#. ``secrets/prod.yaml`` and ``secrets/staging.yaml`` require secure random keys you can generate 
   and fill in.

If you are deploying onto AWS infrastructure, your access key file should look like the aws
credentials file (usually found at ``~/.aws/credentials``). However, the profile you use *must*
be named ``default``.

If you want to try deploying to staging now, that is fine! Hub Customization can come later as you 
try things out.


Hub Customizations
------------------

You can customize your hub in two major ways:

#. Customize the hub image. `repo2docker`_ is used to build the image, so you can put any of the
   `supported configuration files`_ under ``deployments/<hub-image>/image``. You *must* make a git 
   commit after modifying this for ``hubploy build <hub-name> --push --check-registry`` to work, 
   since it uses the commit hash as the image tag.

#. Customize hub configuration with various YAML files.

   * ``hub/values.yaml`` is common to *all* hubs that exist in this repo (multiple hubs can live 
     under ``deployments/``).

   * ``deployments/<hub-name>/config/common.yaml`` is where most of the config specific to each 
     hub should go. Examples include memory / cpu limits, home directory definitions, etc

   * ``deployments/<hub-name>/config/staging.yaml`` and 
     ``deployments/<hub-name>/config/prod.yaml`` 
     are files specific to the staging & prod versions of the hub. These should be *as minimal as 
     possible*. Ideally, only DNS entries, IP addresses, should be here.

   * ``deployments/<hub-name>/secrets/staging.yaml`` and 
     ``deployments/<hub-name>/secrets/prod.yaml`` 
     should contain information that mustn't be public. This would be proxy / hub secret 
     tokens, any authentication tokens you have, etc. These files *must* be protected by something 
     like `git-crypt <https://github.com/AGWA/git-crypt>`_ or 
     `sops <https://github.com/mozilla/sops>`_.


You can customize the staging hub, deploy it with ``hubploy deploy <hub-name> hub staging``, and 
iterate until you like how it behaves.


Step 4: Build and Push the Image
================================

#. Make sure tha appropriate docker credential helper is installed, so hubploy can push to the 
   registry you need.

   For AWS, you need `docker-ecr-credential-helper <https://github.com/awslabs/
   amazon-ecr-credential-helper>`_
   For Google Cloud, you need the `gcloud commandline tool <https://cloud.google.com/sdk/>`_

#. Make sure you are in your repo's root directory, so hubploy can find the directory structure it 
   expects.

#. Build and push the image to the registry

   .. code:: bash

      hubploy build <hub-name> --push --check-registry

   This should check if the user image for your hub needs to be rebuilt, and if so, it’ll build 
   and push it.


Step 5: Deploy the Staging Hub
==============================

Each hub will always have two versions - a *staging* hub that isn’t used by actual users, and a *
production* hub that is. These two should be kept as similar as possible, so you can fearlessly 
test stuff on the staging hub without feaer that it is going to crash & burn when deployed to 
production.

To deploy to the staging hub,

.. code:: bash

   hubploy deploy <hub-name> hub staging

This should take a while, but eventually return successfully. You can then find the public IP of 
your hub with:

.. code:: bash

   kubectl -n <hub-name>-staging get svc public-proxy

If you access that, you should be able to get in with any username & password.

The defaults provision each user their own EBS / Persistent Disk, so this can get expensive 
quickly :) Watch out!

If you didn't do more `Hub Customizations`_, you can do so now!


Step 6: Deploy the Production Hub
=================================

You can then do a production deployment with: ``hubploy deploy <hub-name> hub prod``, and test it 
out!


Step 7: Setup git-crypt for Secrets
===================================

`git crypt <https://github.com/AGWA/git-crypt>`_ is used to keep encrypted secrets in the git 
repository. We would eventually like to use something like 
`sops <https://github.com/mozilla/sops>`_
but for now...

#. Install git-crypt. You can get it from brew or your package manager.

#. In your repo, initialize it.

   .. code:: bash

      git crypt init

#. In ``.gitattributes`` have the following contents:

   .. code::

      deployments/*/secrets/** filter=git-crypt diff=git-crypt
      deployments/**/secrets/** filter=git-crypt diff=git-crypt
      support/secrets.yaml filter=git-crypt diff=git-crypt

#. Make a copy of your encryption key. This will be used to decrypt the secrets. You will need to 
   share it with your CD provider, and anyone else.

   .. code::

      git crypt export-key key

   This puts the key in a file called 'key'


Step 8: GitHub Workflows
========================

#. Get a base64 copy of your key

   .. code:: bash

      cat key | base64

#. Put it as a secret named GIT_CRYPT_KEY in github secrets.

#. Make sure you change the `myhub` to your deployment name in the
   workflows under `.github/workflows`.

#. Push to the staging branch, and check out GitHub actions, to
   see if your action goes to completion.

#. If the staging action succeeds, make a PR from staging to prod,
   and merge this PR. This should also trigger an action - see if
   this works out.

**Note**: *Always* make a PR from staging to prod, never push directly to prod. We want to keep 
the staging and prod branches as close to each other as possible, and this is the only long term 
guaranteed way to do that.

.. _this repository: https://github.com/yuvipanda/hubploy-template
.. _repo2docker: https://repo2docker.readthedocs.io/
.. _supported configuration files: https://repo2docker.readthedocs.io/en/latest/config_files.html
