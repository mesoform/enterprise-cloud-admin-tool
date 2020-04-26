# Enterprise Cloud Admin Tool

This application pulls [Terraform](https://www.terraform.io/intro/index.html) code for deploying
cloud infrastructure, security defined policies, and environment configuration (currently from Github).
Then it compares the configuration against security policies and runs deploys
with [python-terraform](https://github.com/beelit94/python-terraform).
Afterwards it will log the changes and report stats to a monitoring system
([GCP Stackdriver](https://cloud.google.com/stackdriver/) or [AWS Cloudwatch](https://aws.amazon.com/cloudwatch/)).


## Sequence diagram
Here is rendered sequence diagram of possible workflow in [PlantUML](https://plantuml.com/) format.
For diagram code, review `docs` directory.

![sequence diagram](https://raw.githubusercontent.com/mesoform/enterprise-cloud-admin-tool/dev/docs/sequence_diagram.png "Sequence Diagram")

## Getting Started

These instructions will get you an environment, ready for `enterprise-cloud-admin-tool` development. 

### Prerequisites

1. This tool has been tested to work with:
 - Python version `>=3.6,<=3.7.4`
 - Terraform version `>=0.12.0,<=0.12.1`

1. You should have [terraform](https://www.terraform.io/downloads.html) in your `PATH` environment variable.
For example, you can download terraform and extract it to `/usr/local/bin`.
Also, you can create make `tf_bin` directory right where you are, copy `terraform` into this directory, and run
`export PATH=$PATH:$PWD/tf_bin`.
Official Terraform documentation points [here](https://stackoverflow.com/questions/14637979/how-to-permanently-set-path-on-linux-unix) for additional instructions. 

1. Your platform should have installed [pipenv](https://github.com/pypa/pipenv).

    If you're unable to install it through system package manager, you can use `pip`:
    `pip install --user --upgrade pipenv`.

    Recommended way of installing `pip` is through official `get_pip.py` script. You can find more information [here](https://pip.pypa.io/en/stable/installing/).

1. You must have access token of your Github account, and this account should be admin of
some Github organization.
You can generate it here: `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`.
This token needs permissions for 'repo', 'admin:org', and 'delete_repo'.

1. You must have a project on Google Cloud Platform that will be used as the build project and as a monitoring namespace.

    - "Cloud Resource Manager" and "Cloud Billing" APIs need to be enabled on the project.

    As this project will also be used as a monitoring namespace you need to create that namespace. To do so go to 'Monitoring' menu and create a monitoring space in Stackdriver.

1. When building the project Terraform will need to maintain a remote state file. This can be hosted anywhere and the path to this state file will be required in deployment code. We have used an example hosted in Google Cloud Storage (GCS). More information on remote backend is [here](https://www.terraform.io/docs/backends/types/remote.html)

1. The build/monitoring project must have a service account. Switch to your project, go to `IAM` menu, and add a service account. Then assign the following permissions to that service account:

    - "Billing Account User" role set at the organization level or on the specified billing account by an org/billing admin. (Check billing access control documentation [here](https://cloud.google.com/billing/docs/how-to/billing-access))
    - "Project Creator" role set minimum at the folder level.
    - "Monitoring Metric Writer" role assigned at the project level.
    - relevant permission to access the state file - if using GCS this is "Storage Object Admin" assigned at the storage level

    You can find how to create a service account [here](https://cloud.google.com/iam/docs/creating-managing-service-accounts).
    It doesn't matter for which project you will create service account, you will be able to use it for any API activity.

1. You must create, export and save your GCP service account private key in `json` format.

    More details about [here](https://cloud.google.com/iam/docs/creating-managing-service-account-keys).

### Installing

1. Clone this repo:

    ```
    git clone https://github.com/mesoform/enterprise-cloud-admin-tool.git && cd enterprise-cloud-admin-tool
    ```

1. Update pipfile with current version of python

    ```
    vi $(pwd)/Pipfile
    ```    
    
1. Install all dependencies:

    ```
    pipenv install --dev
    ```

1. Activate virtual environment:

    ```
    pipenv shell
    ```

1. Copy `terraform` binary in current directory. Path for this binary is configurable, check `cat settings/default_settings.py | grep TERRAFORM_BINARY_PATH`. Then,

    ```
    cp ~/Downloads/terraform $(pwd)/terraform
    ```

1. Copy GCP service account token in `resources` directory:

    ```
    cp ~/Downloads/gcp_service_account_key.json $(pwd)/resources/gcp_service_account_key.json
    ```

1. Point `gcloud` to service account token file via `GOOGLE_CREDENTIALS` environment variable:
    ```
    export GOOGLE_CREDENTIALS=$(pwd)/resources/gcp_service_account_key.json
    ```

1. **[Optional]** In order to use `cloudwatch` monitoring system, you need to setup credentials and default
    region for `boto3` library. You can do that with [AWS CLI](http://aws.amazon.com/cli/) or manually.
    [Details](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html).

## Running the tests

```shell
pytest
```

### Running tests inside docker container
If you just cloned repo and have docker installed, you can just build the container and run
tests without installing anything in your environment.

Build container and run bash shell:

```shell
docker build . -t test_eca
docker run -it test_eca bash
```

After that, you will be attached to container's bash shell. You can run tests:

```shell
pytest
```

### Parametrized tests
You can run pytest in verbose mode:

```shell
pytest -v
```

Then, you will be able to see each test, that generated by parametrize decorator, like:

```
tests/test_deployer.py::test_deploy_different_states[test_state0-real_state0] PASSED [ 89%]
tests/test_deployer.py::test_deploy_different_states[test_state1-real_state1] PASSED [ 94%]
tests/test_deployer.py::test_deploy_different_states[test_state2-real_state2] PASSED [100%]
```

Also, if some of parametrized tests is failing,
you are able to determine which one by it's name in square brackets, like `test_state1-real_state1`:
here number of parametrize argument is a number after test name.

## Test deployment
### Create config and code using examples

In order to test a deployment we require a github repo which will contain the configuration files and another repo for the deployment code.

We prepared two example repos:

1. [example-ecat-project-config](https://github.com/mesoform/example-ecat-project-config) — contains terraform
variable files.
1. [example-ecat-deployment-code](https://github.com/mesoform/example-ecat-deployment-code) — contains terraform infrastructure code.

Please note, that both config and code repos require certain structure to be valid:
* top-level directories must be named like: `gcp`, `aws`, or `azure`.
* each top-level directory must contain it's own set of config or code files.
* The example-ecat-deployment-code should be updated with path to the remote state bucket and prefix

### Create config repo with eCat from example
In order to perform test deployment using these examples, you should fork these repos to your organization, and then customise the configuration as per below:

* `example-ecat-project-config/gcp/project_settings.auto.tfvars.json` — In this file, you should set unique `project_id` ([project creation docs](https://cloud.google.com/resource-manager/docs/creating-managing-projects)),
set or remove any remaining key value pair according your requirements.
Be aware, that `project_id` unique across whole GCP platform, even six month after deletion. So, if someone already have project with your id, you will receive unclear error.
* Also add a valid `billing_id`, it's mandatory ([billing docs](https://cloud.google.com/billing/docs/how-to/modify-project)).
* `folder_id` means folder numeric ID, [more information about how it can be obtained](https://cloud.google.com/resource-manager/docs/creating-managing-folders).
### Create config repo with eCat from template

If you wish to create a config repo manually this command will create the required repo and required config files

```shell
./cloudctl \
  --code-org <github organization name> \
  --config-org <github organization name> \
  --vcs-token <github token> \
  --key-file resources/gcp_service_account_key.json \
  --monitoring-namespace <monitoring project id> \
  --monitoring-system <monitoring system> \
  --notification-system <notification system> \
  --debug true \
  config create <project id> \
  --config-repo <config repo> \
  --force
```

Where:

- `project id` — id of project, that will be created.
- `github organization name` — name of organization, that holds repos with code/config.
- `github token` — you developer's github token, that you have obtained in prerequisites section.
- `monitoring project id` — id of existing monitoring project. You should have one if followed prerequisites section.
- `monitoring system` — identifier of monitoring backend, that you want to use for metrics collection
- `notification system` - identifier of notification backend, where you want to send notifications
- `config repo` — name of repo, that will contain terraform variables files.

In the project settings file created within the config repo you should ensure a unique `project_id` is set ([project creation docs](https://cloud.google.com/resource-manager/docs/creating-managing-projects)),
set or remove any remaining key value pair according your requirements.
Be aware, that `project_id` unique across whole GCP platform, even six month after deletion. So, if someone already have project with your id, you will receive unclear error.
* Also add a valid `billing_id`, it's mandatory ([billing docs](https://cloud.google.com/billing/docs/how-to/modify-project)).
* And update the `folder_id` (numeric folderID from GCP), [more information about how it can be obtained](https://cloud.google.com/resource-manager/docs/creating-managing-folders).


#### Updating of config repo
If you want to override config files, you can just run again the same command as for creation.
If you see this:
```
{'message': 'Could not update file: At least 1 approving review is required by reviewers with write access.', 'documentation_url': 'https://help.github.com/articles/about-protected-branches'}
```
then, try to pass `--bypass-branch-protection` option to `config` subcommand.

### Test deployment using created code and config
Once the created/example config and code repos have been updated, you can perform test deployment with the following command:


```shell
./cloudctl \
  --code-org <github organization name> \
  --config-org <github organization name> \
  --vcs-token <github token> \
  --key-file resources/gcp_service_account_key.json \
  --monitoring-namespace <monitoring project id> \
  --monitoring-system <monitoring system> \
  --notification-system <notification system> \
  deploy <project id> \
  --cloud gcp \
  --code-repo <code repo> \
  --config-repo <config repo>
```

Where:

- `project id` — id of project, that will be created.
- `code repo` — name of repo, that contain created infrastructure code.
- `config repo` — name of repo, that contain created terraform variables files.
- `github organization name` — name of organization, that holds repos with code/config.
- `github token` — you developer's github token, that you have obtained in prerequisites section.
- `monitoring project id` — id of existing monitoring project. You should have one if followed prerequisites section.
- `monitoring system` — identifier of monitoring backend, that you want to use for metrics collecting
- `notification system` - identifier of notification backend, where you want to send notifications

After that, you should receive success message in console, and metrics in your GCP monitoring project workspace.


## Logging
There is some command line arguments for logging setup:
1) `--json-logging` — this one will enable logging in json format.
2. `--disable-local-reporter` — in order to disable dumping of all metrics, you may want to pass this argument.

Both arguments related to root cli parser, so you can pass them this way:
```shell script
./cloudctl \
  --code-org <github organization name> \
  ...
  --json-logging \
  --disable-local-reporter \
  ...
  deploy <project id> --cloud gcp \
  ...
```

By default, we writing logs in `/var/log/enterprise_cloud_admin.log`,
so probably you need to create and change ownership of this file:
```shell script
touch /var/log/enterprise_cloud_admin.log
chown <user>:<group> /var/log/enterprise_cloud_admin.log
```
Same you should do for `/var/log/enterprise_cloud_admin_metrics` file in case you use `local` reporter (monitoring system).

## Monitoring

### Metrics
You can choose monitoring backend, that you want to use for metrics collecting with help of `--monitoring-system` argument.

Possible choices for now are:
- `stackdriver` — uses [GCP Stackdriver](https://cloud.google.com/stackdriver) as a monitoring backend.
- `cloudwatch` — uses [AWS Cloudwatch](https://aws.amazon.com/cloudwatch/) as a monitoring backend.

Be aware, that there is also `local` monitoring system, that dumps metrics into local files. It's enabled by default, and can be disabled
by `--disable-local-reporter` argument.

Default metrics file path is `/var/log/enterprise_cloud_admin_metrics.<command>`,
where `<command>` is either `deploy` or `config`.

You may want to create these files and change ownership for them:
```shell script
touch /var/log/enterprise_cloud_admin_metrics.config
chown <user>:<group> /var/log/enterprise_cloud_admin_metrics.config

touch /var/log/enterprise_cloud_admin_metrics.deploy
chown <user>:<group> /var/log/enterprise_cloud_admin_metrics.deploy
```

### Notifications

It is possible to send notifications, that include basic information, such as what `eCat` command has been invoked,
result of run, etc.

To do that, `--notification-system` cli argument should be specified. For now, available options are:
- `slack`

#### Slack

In order to use `slack` notification system for your existing `Slack` workspace, `--slack-channel` and `--slack-token` cli arguments must be specified.

`--slack-channel` is channel, where notification will go.

`--slack-token` is your "Bot User OAuth Access Token".

Go through official [Slack App Docs](https://api.slack.com/start/overview) to become comfortable with Bot setup.

In general, steps are:
1) Create `Slack App` [here](https://api.slack.com/apps). During this step you must choose target workspace.
2) Then you should go `Features` -> `OAuth & Permissions` -> `Scopes` -> `Add an OAuth Scope`.
3) You should choose in dropdown `chat:write` scope. It's enough for app to send notifications.
4) On the same page you should click on `Install App to Workspace` button.
5) Then, you will be asked to approve permissions request. Confirm it.
6) You will be redirected on the page with your `Bot User OAuth Access Token`. Copy it and use as `--slack-token`.
7) Tag `@ecat` in some channel, invite it, and use that channel as `--slack-channel`.

## Troubleshooting

### Google Cloud Platform and Stackdriver

Sometimes it's really hard to interpret immediately what GCP error means, so terraform community members
created curated list of common problems: [TROUBLESHOOTING.md](https://github.com/terraform-google-modules/terraform-google-project-factory/blob/master/docs/TROUBLESHOOTING.md).

### Other known issues ###

1) If a "testing*" project has already been created but the deployment failed to complete, retrying the deployment will throw the "requested entity already exists" error due to an already existing "testing*" project. To bypass this issue the name of the project needs to be changed. E.g: xyz-eca-test01 to xyz-eca-test02

```
STDERR:
Error: error creating project testing-123456a-123456b (testing-123456a-123456b): googleapi: Error 409: Requested entity already exists, alreadyExists. If you received a 403 error, make sure you have the `roles/resourcemanager.projectCreator` permission
  on project.tf line 9, in resource "google_project" "project":
   9: resource "google_project" "project" {
```

2) Check that the service account has the minimum required billing permissions granted. More: https://cloud.google.com/billing/docs/how-to/billing-access

```
STDERR:
Error: Error setting billing account "01234A-12345B-23456C" for project "projects/testing-123456a-123456b": googleapi: Error 403: The caller does not have permission, forbidden
  on project.tf line 9, in resource "google_project" "project":
   9: resource "google_project" "project" {
```

3) Check whether Cloud Resource Manager API is enabled on the project owning the service account which is used for the deployment.

```
STDERR:
Error: error creating project testing-123456a-123456b (testing-123456a-123456b): googleapi: Error 403: Cloud Resource Manager API has not been used in project 123456789101 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudresourcemanager.googleapis.com/overview?project=123456789101 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry., accessNotConfigured. If you received a 403 error, make sure you have the `roles/resourcemanager.projectCreator` permission
  on project.tf line 9, in resource "google_project" "project":
   9: resource "google_project" "project" {
```   


4) If the limit of projects associated with the billing account has been reached a "precondition check failed" error will be shown. Try removing some projects from that billing account.

```
STDERR:
Error: Error setting billing account "01234A-12345B-23456C" for project "projects/xyz-eca-test07": googleapi: Error 400: Precondition check failed., failedPrecondition
  on project.tf line 9, in resource "google_project" "project":
   9: resource "google_project" "project" {
```

## Contributing

Please read [CONTRIBUTING.md](https://github.com/mesoform/enterprise-cloud-admin-tool/blob/master/CONTRIBUTING.md) for the process for submitting pull requests.

## License

This project is licensed under the [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
