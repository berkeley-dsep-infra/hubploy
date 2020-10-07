========================
Helm Versions in Hubploy
========================

* `Helm Versions Present by Default`_
* `Using a Custom Version of Helm`_
* `Local Usage`_
* `GitHub Action Usage`_

Helm Versions Present by Default
================================

The ``hubploy`` Docker image has `Helm <https://helm.sh/>`_ v2.16.9
and v3.2.4 installed by default. This may depend on the specific version
of ``hubploy`` that is installed. Versions can be found in the
`Dockerfile <https://github.com/yuvipanda/hubploy/blob/master/Dockerfile>`_
present in the base folder of the
`hubploy <https://github.com/yuvipanda/hubploy>`_ repository. There isn't
a version matrix to help find which versions of ``helm`` ship with certain
versions of ``hubploy``. You can look at the ``Dockerfile``'s commit history
or just use the most recent version of ``hubploy``, which has the versions
listed above.


Using a Custom Version of Helm
==============================

To use your own installed version of ``helm``, set the environment variable
``HELM_EXECUTABLE``. ``hubploy`` will pick up the value from this environment
variable to use when running ``helm`` commands. It will default to ``helm``,
ie. v2.16.9, if nothing else is installed. You can find the line of code that
does this
`here <https://github.com/yuvipanda/hubploy/blob/master/hubploy/helm.py#L34>`_.


Local Usage
===========

To use this environment variable on a local installation of ``hubploy``,
use the command from your terminal

.. code:: bash

	export HELM_EXECUTABLE=~/absolute/path/to/helm/binary


GitHub Action Usage
===================

To use this environment variable in a GitHub Action, use the following lines
in your workflow file

.. code:: yaml

	env:
	  HELM_EXECUTABLE: /absolute/path/to/helm/binary

More information on this second option can be found on the
`Environment variables page <https://docs.github.com/en/free-pro-team@latest/actions/reference/environment-variables>`_
on GitHub Docs.

