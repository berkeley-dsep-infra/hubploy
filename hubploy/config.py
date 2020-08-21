"""
A util (get_config) that process hubploy.yaml deployment configuration and
returns it embedded with a set of LocalImage objects with filesystem paths made
absolute.
"""
import os
from ruamel.yaml import YAML
from repo2docker.app import Repo2Docker
import docker


from . import utils
yaml = YAML(typ='safe')

class DeploymentNotFoundError(Exception):
    def __init__(self, deployment, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deployment = deployment
        self.path = path

    def __str__(self):
        return f"deployment {self.deployment} not found at {self.path}"


class LocalImage:
    """
    A docker image that can be built from a local filesystem source
    """
    def __init__(self, name, path, helm_substitution_path='jupyterhub.singleuser.image'):
        """
        Create an Image from a local path

        name: Fully qualified name of image
        path: Absolute path to local directory with image contents
        helm_substitution_path: Dot separated path in a helm file that should be populated with this image spec

        Expects cwd to be inside the git repo we are operating in
        """
        # name must not be empty
        # FIXME: Validate name to conform to docker image name guidelines
        if not name or name.strip() == '':
            raise ValueError("Name of image to be built is not specified. Check hubploy.yaml of your deployment")
        self.name = name

        self.tag = utils.last_modified_commit(path)
        self.path = path
        self.helm_substitution_path = helm_substitution_path
        self.image_spec = f'{self.name}:{self.tag}'

        # Make r2d object here so we can use it to build & push
        self.r2d = Repo2Docker()
        self.r2d.subdir = self.path
        self.r2d.output_image_spec = self.image_spec
        self.r2d.user_id = 1000
        self.r2d.user_name = 'jovyan'
        self.r2d.target_repo_dir = '/srv/repo'
        self.r2d.initialize()

    @property
    def docker(self):
        """
        Return a shared docker client object

        Creating a docker client object with automatic version
        selection can be expensive (since there needs to be an API
        request to determien version). So we cache it on a per-class
        level.
        """
        # FIXME: Is this racey?
        if not hasattr(self.__class__, '_docker'):
            self.__class__._docker = docker.from_env()

        return self.__class__._docker

    def exists_in_registry(self):
        """
        Return true if image exists in registry
        """
        try:
            image_manifest = self.docker.images.get_registry_data(self.image_spec)
            return image_manifest is not None
        except docker.errors.ImageNotFound:
            return False
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError as e:
            # This message seems to vary across registries?
            if e.explanation.startswith('manifest unknown: '):
                return False
            else:
                raise

    def get_possible_parent_tags(self, n=16):
        """
        List n possible image tags that might be the same image built previously.

        It is much faster to build a new image if we have a list of cached
        images that were built from the same source. This forces a rebuild of
        only the parts that have changed.

        Since we know how the tags are formed, we try to find upto n tags for
        this image that might be possible cache hits
        """
        last_tag = None
        for i in range(1, n):
            # FIXME: Make this look for last modified since before beginning of commit_range
            # Otherwise, if there are more than n commits in the current PR that touch this
            # local image, we might not get any useful caches
            commit_sha = utils.last_modified_commit(self.path, n=i)
            # Stop looking for tags if our commit hashes repeat
            # This means `git log` is repeating itself
            if commit_sha != last_tag:
                last_tag = commit_sha
                yield commit_sha

    def fetch_parent_image(self):
        """
        Prime local image cache by pulling possible parent images.

        Return spec of parent image, or None if no parents could be pulled
        """
        for tag in self.get_possible_parent_tags():
            parent_image_spec = f'{self.name}:{tag}'
            try:
                print(f'Trying to fetch parent image {parent_image_spec}')
                self.docker.images.pull(parent_image_spec)
                return parent_image_spec
            except docker.errors.NotFound:
                pass
            except  docker.errors.APIError:
                # FIXME: This is too generic, but a lot of remote repos don't raise NotFound. ECR :()
                pass
        return None

    def needs_building(self, check_registry=False, commit_range=None):
        """
        Return true if image needs to be built.

        One of check_registry or commit_range must be set
        """
        if not (check_registry or commit_range):
            raise ValueError("One of check_registry or commit_range must be set")

        if check_registry:
            return not self.exists_in_registry()

        if commit_range:
            return utils.path_touched(self.path, commit_range=commit_range)


    def build(self, reuse_cache=True):
        """
        Build local image with repo2docker
        """
        if reuse_cache:
            parent_image_spec = self.fetch_parent_image()
            if parent_image_spec:
                self.r2d.cache_from = [parent_image_spec]

        self.r2d.build()

    def push(self):
        self.r2d.push_image()



def get_config(deployment):
    """
    Returns hubploy.yaml configuration as a Python dictionary if it exists for a
    given deployment, and also augments it with a set of LocalImage objects in
    ["images"]["images"] and updates the images' filesystem paths to be
    absolute.
    """
    deployment_path = os.path.abspath(os.path.join('deployments', deployment))
    if not os.path.exists(deployment_path):
        raise DeploymentNotFoundError(deployment, deployment_path)

    config_path = os.path.join(deployment_path, 'hubploy.yaml')
    with open(config_path) as f:
        # If config_path isn't found, this will raise a FileNotFoundError with useful info
        config = yaml.load(f)

    if 'images' in config:
        images_config = config['images']

        if 'image_name' in images_config:
            # Only one image is being built
            # FIXME: Deprecate after moving other hubploy users to list format
            images = [{
                'name': images_config['image_name'],
                'path': 'image',
            }]
            if 'image_config_path' in images_config:
                images[0]['helm_substitution_path'] = images_config['image_config_path']

        else:
            # Multiple images are being built
            images = images_config['images']

        for image in images:
            # Normalize paths to be absolute paths
            image['path'] = os.path.join(deployment_path, image['path'])

        config['images']['images'] = [LocalImage(**i) for i in images]

        # FIXME: Does not currently support multiple images in the images block
        # Backwards compatibility checker for images block
        if config['images']['registry']['provider'] == 'aws' and 'project' in config['images']['registry']['aws']:
            config['images']['registry']['aws']['account_id'] = config['images']['registry']['aws']['project']
            del config['images']['registry']['aws']['project']

        if config['images']['registry']['provider'] == 'aws' and 'zone' in config['images']['registry']['aws']:
            config['images']['registry']['aws']['region'] = config['images']['registry']['aws']['zone']
            del config['images']['registry']['aws']['zone']

        # Backwards compatibility checker for cluster block
        if config['cluster']['provider'] == 'aws' and 'project' in config['cluster']['aws']:
            config['cluster']['aws']['account_id'] = config['cluster']['aws']['project']
            del config['cluster']['aws']['project']

        if config['cluster']['provider'] == 'aws' and 'zone' in config['cluster']['aws']:
            config['cluster']['aws']['region'] = config['cluster']['aws']['zone']
            del config['cluster']['aws']['zone']

    return config
