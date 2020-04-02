=======
HubPloy
=======

``hubploy`` is a suite of commandline tools and an opinionated
repository structure for continuously deploying JupyterHubs on Kubernetes (with
`Zero to JupyterHub <https://z2jh.jupyter.org>`_).


Deployment workflow
===================

Every change to your hub (image changes, config changes, etc) *must*
flow through a git repo set up with continuous deployment. The following
chart describes the process of deploying a change to your users on the
production hub.

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

Hubploy features
================
HubPloy has two major components:

#. An :ref:`image-builder` that builds images from subpaths of git repositories
   only when needed.
#. A `helm <https://helm.sh>`_ wrapper that deploys a helm chart when
   required.

HubPloy tries to be `level triggered <https://hackernoon.com/level-triggering-and-reconciliation-in-kubernetes-1f17fe30333d>`_
rather than edge triggered wherever possible, for simpler code & reliable
deploys.
