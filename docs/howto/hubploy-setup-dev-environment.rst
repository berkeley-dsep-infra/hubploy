==============================================
How to Setup a Hubploy Development Environment
==============================================

This is a guide on how to setup a development environment for Hubploy. Use cases would be for 
making a custom Hubploy image for your own use or contributing to the Hubploy repository.

* `Prerequisites`_
* `Modifying Hubploy Files`_
* `Using a Custom Hubploy Locally`_
* `Building a Custom Hubploy on DockerHub`_
* `Contributing to Hubploy`_

Prerequisites
===========================

To start, fork the `main Hubploy repository <https://github.com/yuvipanda/hubploy>`_
and then clone your fork. This will enable easier setup for pull requests and
independent development. Methodology for testing Hubploy is limited right now but it is
recommendation that you have a working JupyterHub configuration so you can try to
build and deploy.

If you don't have such a configuration set up, we recommend setting one up using the 
`hubploy template repository <https://github.com/yuvipanda/hubploy-template>`_ and following the 
how-to on Deploying a JupyterHub with Hubploy (link later).


Modifying Hubploy Files
=======================

The code for Hubploy is contained in the ``hubploy/hubploy`` folder. All of it is in Python, so 
there is no compiling necessary to use it locally. As long as the files are saved, their changes 
should be reflected the next time you run a ``hubploy`` command.


Using a Custom Hubploy Locally
==============================

Hubploy can be installed via ``pip install hubploy``, but this version is very out-of-date.
Using a custom version of Hubploy will require different installation methods.

If you are just using your custom Hubploy locally, you can link it with ``pip``. Go to the top 
folder of your ``hubploy-template`` or JupyterHub deployment repo and run::

  pip install -e ~/<absolute-path-to>/hubploy

You can then make changes to your local Hubploy files and rerun Hubploy commands in the other 
folder for quick development.

`hubploy` can also be installed at any specific commit with the following line in a
`requirements.txt` file:
::

  git+https://github.com/yuvipanda/hubploy@<commit-hash>


Building a Custom Hubploy on DockerHub
======================================

Another way to use Hubploy is by building a Docker image and pushing it to DockerHub. For this, 
you will need to have forked the Hubploy repository to your personal GitHub account. You will also 
need a personal DockerHub account.

Modify the file ``hubploy/.github/workflows/docker-push.yaml``. Change ``name: yuvipanda/hubploy``
 to ``name: <your-dockerhub-name>/hubploy``. You will need to input your DockerHub credentials as 
 secrets in your personal Hubploy GitHub repository as ``DOCKER_USERNAME`` and ``DOCKER_PASSWORD``.
 Also in the GitHub repository, go to the Actions tab and allow the repo to run workflows by 
 clicking "I understand my workflows, go ahead and run them."

Once you have made the changes you want for your custom Hubploy, you can ``git push`` your local 
changes. The file mentioned above will automatically attempt to push your Hubploy to DockerHub! If 
it fails, there will be output in the Actions tab that should have some insights.

Now that you have a publicly-hosted image for your custom Hubploy, you can reference it anywhere 
you want! In ``hubploy-template``, these references are in the ``hubploy/.github/workflows/`` files
::

  jobs:
    build:
      name:
      # This job runs on Linux
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v1
        - uses: docker://yuvipanda/hubploy:20191210215236cfab2d

You will need to change the docker link everywhere you see it in these files to the link of your 
image on DockerHub.


Contributing to Hubploy
=======================

If you have your own fork of Hubploy, and have a feature that would be generally useful, feel free 
to join the dicussions in the Issues section or contribute a PR!
