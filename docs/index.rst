=======
HubPloy
=======

``hubploy`` is a suite of commandline tools and an opinionated
repository structure for continuously deploying JupyterHubs on Kubernetes (with
`Zero to JupyterHub <https://z2jh.jupyter.org>`_). Find the ``hubploy``
`repository <https://github.com/yuvipanda/hubploy>`_ on GitHub.


Hubploy workflow
================

**Every change to your hub configuration must be made via a pull request
to your git repository**. Guided by principles of `continuous delivery <https://continuousdelivery.com/>`_,
this informs hubploy's design.

Components
----------

The following components make up a hubploy based deployment workflow:

#. A deployment *git repository*, containing *all* the configuration for your
   JupyterHubs. This includes image configuration, zero-to-jupyterhub configuration,
   and any secrets if necessary. hubploy is designed to support many different
   hubs deploying to different cloud providers from the same repository.
#. A *staging hub* for each JupyterHub in the git repo. End users rarely use
   this hub, and it is primarily used for testing by devs. The ``staging`` branch
   in the git repo contains the config for these hubs.
#. A *prod(uction) hub* for each JupyterHub in the git repo. End users actively
   use this hub, and we try to have minimal downtime here. The ``prod`` branch
   in the git repo contains the config for these hubs. However, since we want
   prod and staging to be as close as possible, the *prod branch match the
   staging branch completely* under normal circumstances. The only commits that
   can be in prod but not in staging are merge commits.

Deploying a change
------------------

.. mermaid::

   graph TD
   Change-Configuration[Change configuration] --> Create-Staging-PR[Create PR to 'staging' branch]
      subgraph iterate on config change
         Create-Staging-PR --> Automated-Tests[CI runs automated tests]
         Automated-Tests --> Code-Review[Code Review]
         Code-Review --> Automated-Tests
      end
      Code-Review --> Merge-Staging-PR[Merge PR to 'staging' branch]
      subgraph test in staging
         Merge-Staging-PR --> Deploy-To-Staging[CI deploys staging hub]
         Deploy-To-Staging --> Test-Staging[Manually test staging hub]
         Test-Staging --> |Success| Create-Prod-PR[Create PR from 'staging' to 'prod']
         Test-Staging --> |Fail| Try-Again[Debug & Try Again]
      end
      Create-Prod-PR --> Merge-Prod-PR[Merge PR to prod branch]
      subgraph promote to prod
         Merge-Prod-PR --> Deploy-To-Prod[CI deploys prod hub]
         Deploy-To-Prod --> Happy-Users[Users are happy!]
      end


How-To Guides
=============

These how-to guides are intended to walk you through the basics of particular tasks that you might do with Hubploy.

.. toctree::
   :maxdepth: 2

   howto/index


Topic Guides
============

These topic guides are meant as informative reference documents about various pieces of Hubploy.

.. toctree::
   :maxdepth: 2

   topics/index


Reference Documentation
=======================

These reference documents are here to describe the configuration values of various files in Hubploy
.

.. toctree::
   :maxdepth: 2

   reference/index


Known Limitations
=================

#. hubploy requires you already have infrastructure set up - Kubernetes
   cluster, persistent home directories, image repositories, etc. There
   are `ongoing efforts <https://github.com/pangeo-data/terraform-deploy>`_ to fix
   this, however.
#. More documentation and tests, as always!