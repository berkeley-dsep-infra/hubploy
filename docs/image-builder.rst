.. _image-builder:

=============
Image Builder
=============

Your repository should have a directory with a Dockerfile.
``image-builder`` builds the docker image only if there
is already not an image for the last commit that changed
the contents of the directory. This lets you run it
unconditionally on each deploy to make sure you have an
image to use.

Usage
=====

.. code-block:: bash

   hubploy-image-builder <path-to-image-directory> <image-name>

``<path-to-image-directory>`` is a directory in a git repository
with a ``Dockerfile``. ``<image-name>`` is a full docker image
name **without** a tag.

This command needs to be run on a machine with docker installed
and accessible to the user running the command.

It will:

#. Discover last commit that touched the directory
#. Check if an image already exists in the docker image registry
   where the tag is the commit hash of the last commit to touch
   the image directory
#. If the image does not exist, build the image and push it.