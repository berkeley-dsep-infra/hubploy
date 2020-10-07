==================
Contribution Guide
==================

* `Setting up for Documentation Development`_
* `Setting up for Hubploy Development`_


``hubploy`` is open-source and anyone can contribute to it. We welcome
the help! Yuvi Panda is the original author and can give GitHub contributor
access to those who are committed to making ``hubploy`` better. You do not
have to be a contributor on GitHub to suggest changes in
`the Issues section <https://github.com/yuvipanda/hubploy/issues>`_ or make
pull requests. A contributor will have to accept your changes before they become
a part of ``hubploy``.

If you don't have `git <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_
already, install it and clone this repository.

.. code:: bash

   git clone https://github.com/yuvipanda/hubploy

Using a
`forking workflow <https://www.atlassian.com/git/tutorials/comparing-workflows/forking-workflow>`_
is also useful and will make seting up pull requests easier.

Once you have made changes that you are ready to offer to ``hubploy``,
make a
`pull request <https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/about-pull-requests>`_
to the main `hubploy repository <https://github.com/yuvipanda/hubploy>`_.
Someone will get back to you soon on your changes.

If you want to dicuss
changes before they get onto GitHub or contact a contributor, try the
`JupyterHub Gitter channel <https://gitter.im/jupyterhub/jupyterhub>`_.


Setting up for Documentation Development
========================================

The ``hubploy`` documentation is automatically built on each commit
`as configured on ReadTheDocs <https://readthedocs.org/projects/hubploy/>`_.
Source files are in the ``docs/`` folder of the main repository.

To set up your local machine for documentation development, install the
required packages with:

.. code:: bash

   # From the docs/ folder
   pip install -r doc-requirements.txt

To test your updated documentation, run:

.. code:: bash

   # From the docs/ folder
   make html

Make sure there are no warnings or errors. From there, you can check
the ``_build/html/`` folder and launch the ``.html`` files locally to
check that formatting is as you expect.


Setting up for Hubploy Development
==================================

See the How-To guide on
`setting up a development environment <https://hubploy.readthedocs.io/en/latest/howto/hubploy-setup-dev-environment.html>`_
for ``hubploy``.

In short, you can install ``hubploy`` and its dependencies easily
with the above guide but you will need a
`kubernetes <https://kubernetes.io/>`_ cluster to do local deployment
tests. Some good resources for deploying a kubernetes cluster are:

#. `Zero to JupyterHub K8s <https://zero-to-jupyterhub.readthedocs.io/en/latest/>`_
#. `AWS Terraform K8s Examples <https://github.com/pangeo-data/terraform-deploy/tree/master/aws-examples>`_

You will also need to reference the section
`Using a Custom Hubploy Locally <https://hubploy.readthedocs.io/en/latest/howto/hubploy-setup-dev-environment.html#using-a-custom-hubploy-locally>`_,
rather than doing a default ``hubploy`` installation.

