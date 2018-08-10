===========================================
HubPloy: The JupyterHub Kubernetes Deployer
===========================================

``hubploy`` is a suite of commandline tools & a python library
for continuous deployment of JupyterHub on Kubernetes (with
`Zero to JupyterHub <https://z2jh.jupyter.org>`_).

HubPloy has two major components:

#. An :ref:`image-builder` that builds images from subpaths of git repositories
   only when needed.
#. A `helm <https://helm.sh>`_ wrapper that deploys a helm chart when
   required.

HubPloy tries to be `level triggered <https://hackernoon.com/level-triggering-and-reconciliation-in-kubernetes-1f17fe30333d>`_
rather than edge triggered wherever possible, for simpler code & reliable
deploys.
