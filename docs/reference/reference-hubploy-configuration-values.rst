======================================
Hubploy Configuration Values Reference
======================================

This reference doc will detail the various configuration values present in ``hubploy.yaml``.
Here is the ``hubploy.yaml`` file that comes with cloning hubploy-template::

	images:
	  image_name: # TODO: Full path to your docker image, based on the following pattern
	  # On AWS: <account-id>.dkr.ecr.<zone>.amazonaws.com/<your-hub-name>-user-image
	  # On Google Cloud: gcr.io/<project-name>/<your-hub-name>-user-image
	  registry:
	    provider: # TODO: Pick 'gcloud' or 'aws', and fill up other config accordingly
	    gcloud:
	      # Pushes to Google Container Registry.
	      project: # TODO: GCloud Project Name
	      # Make a service account with GCR push permissions, put it in secrets/gcr-key.json
	      service_key: gcr-key.json
	    aws:
	      # Pushes to Amazon ECR
	      project: # TODO: AWS account id
	      zone: # TODO: Zone in which your container image should live. Match your cluster's zone
	      # TODO: Get AWS credentials that can push to ECR, in same format as ~/.aws/credentials
	      # then put them in secrets/aws-ecr-config.cfg
	      service_key: aws-ecr-config.cfg
	
	cluster:
	  provider: # TODO: gcloud or aws
	  gcloud:
	    project: # TODO: Name of your Google Cloud project with the cluster in it
	    cluster: # TODO: Name of your Kubernetes cluster
	    zone: # TODO: Zone or region your cluster is in
	    # Make a service key with permissions to talk to your cluster, put it in secrets/gkee-key.json
	    service_key: gke-key.json
	  aws:
	    project: # TODO: AWS account id
	    zone: # TODO: Zone or region in which your cluster is set up
	    cluster: # TODO: The name of your EKS cluster
	    # TODO: Get AWS credentials that can access your EKS cluster, in same format as ~/.aws credentials
	    # then put them in secrets/aws-eks-config.cfg
	    service_key: aws-eks-config.cfg

The various values are described below.


images
======

image_name
----------

Full path to your docker image, based on the following pattern:
  * On AWS: <account-id>.dkr.ecr.<zone>.amazonaws.com/<your-hub-name>-user-image
  * On Google Cloud: gcr.io/<project-name>/<your-hub-name>-user-image

registry
--------

provider
^^^^^^^^

Either 'aws' or 'gcloud'. More options will be present in the future.
Both the ``aws`` and ``gcloud`` blocks are uncommented. The one that you do not pick should be 
commented out.

gcloud
^^^^^^

project
"""""""

GCloud Project Name

service_key
"""""""""""

``gcr-key.json`` by default.

Make a service account with GCR push permissions and put it in ``secrets/gcr-key.json``. You can 
rename this file, but you will also need put the new filename here.

aws
^^^

project
"""""""

AWS account ID

zone
""""

The zone in which your ECR image will live. This should match the zone where your cluster will 
live. 

service_key
"""""""""""

``aws-ecr-config.cfg`` by default.

Get AWS Credentials that can push images to ECR. These credentials should be in the same format as 
found in ``~/.aws/credentials`` and put in to the file ``secrets/aws-ecr-config.cfg``. You can 
rename this file, but you will also need put the new filename here.


cluster
=======

provider
--------

Either 'aws' or 'gcloud'. More options will be present in the future.
Both the ``aws`` and ``gcloud`` blocks are uncommented. The one that you do not pick should be 
commented out.

gcloud
------

project
^^^^^^^

Name of your Google Cloud project with the cluster you will create.

cluster
^^^^^^^

Name of the Kubernetes cluster you will create.

zone
^^^^

Zone or region this cluster will sit in.

service_key
^^^^^^^^^^^

``gke-key.json`` by default.

Make a service key with permissions to talk to your cluster and put it in ``secrets/gke-key.json``.
You can rename this file, but you will also need put the new filename here.

aws
---

project
^^^^^^^

AWS account ID

cluster
^^^^^^^

The name of the EKS cluster you will create.

zone
^^^^

Zone or region this cluster will sit in.

service_key
^^^^^^^^^^^

``aws-eks-config.cfg`` by default. 

Get AWS credentials that can access your EKS cluster. These credentials should be in the same 
format as found in ``~/.aws/credentials`` and put in to the file ``secrets/aws-eks-config.cfg``.
You can rename this file, but you will also need put the new filename here.

