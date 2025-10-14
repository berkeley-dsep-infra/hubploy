# hubploy

Toolkit to deploy many z2jh based JupyterHubs

Usage:

``` bash
hubploy deploy <deployment> <chart> <environment>
```

Help text:

``` bash
$ hubploy --help
usage: hubploy [-h] [-d] [-D] [-v] {deploy} ...

positional arguments:
  {deploy}
    deploy          Deploy a chart to the given environment.

options:
  -h, --help        show this help message and exit
  -d, --debug       Enable tool debug output (not including helm debug).
  -D, --helm-debug  Enable Helm debug output. This is not allowed to be used in a CI environment due to secrets being displayed in plain text, and the script will exit. To enable this option, set a local environment varible HUBPLOY_LOCAL_DEBUG=true
  -v, --verbose     Enable verbose output.
```

Deploy help:

``` bash
hubploy deploy --help
usage: hubploy deploy [-h] [--namespace NAMESPACE] [--set SET] [--set-string SET_STRING] [--version VERSION] [--timeout TIMEOUT] [--force] [--atomic]
                      [--cleanup-on-fail] [--dry-run] [--image-overrides IMAGE_OVERRIDES [IMAGE_OVERRIDES ...]]
                      deployment chart {develop,staging,prod}

positional arguments:
  deployment            The name of the hub to deploy.
  chart                 The path to the main hub chart.
  {develop,staging,prod}
                        The environment to deploy to.

options:
  -h, --help            show this help message and exit
  --namespace NAMESPACE
                        Helm option: the namespace to deploy to. If not specified, the namespace will be derived from the environment argument.
  --set SET             Helm option: set values on the command line (can specify multiple or separate values with commas: key1=val1,key2=val2)
  --set-string SET_STRING
                        Helm option: set STRING values on the command line (can specify multiple or separate values with commas: key1=val1,key2=val2)
  --version VERSION     Helm option: specify a version constraint for the chart version to use. This constraint can be a specific tag (e.g. 1.1.1) or it may reference a
                        valid range (e.g. ^2.0.0). If this is not specified, the latest version is used.
  --timeout TIMEOUT     Helm option: time in seconds to wait for any individual Kubernetes operation (like Jobs for hooks, etc). Defaults to 300 seconds.
  --force               Helm option: force resource updates through a replacement strategy.
  --atomic              Helm option: if set, upgrade process rolls back changes made in case of failed upgrade. The --wait flag will be set automatically if --atomic is
                        used.
  --cleanup-on-fail     Helm option: allow deletion of new resources created in this upgrade when upgrade fails.
  --dry-run             Dry run the helm upgrade command. This also renders the chart to STDOUT. This is not allowed to be used in a CI environment due to secrets being
                        displayed in plain text, and the script will exit. To enable this option, set a local environment varible HUBPLOY_LOCAL_DEBUG=true
```
