# Enterprise Cloud Admin

This application pulls [Terraform](https://www.terraform.io/intro/index.html) code for deploying
cloud infrastructure, security defined policies, and environment configuration (currently from Github).
Then it compares the configuration against security policies and runs deploys
with [python-terraform](https://github.com/beelit94/python-terraform).
Afterwards it will log the changes and report stats to a monitoring system (currently [GCP Stackdriver](https://cloud.google.com/stackdriver/)).

## Getting Started

These instructions will get you an environment, ready for `enterprise-cloud-admin` development. 

### Prerequisites

1. This tool designed to work with Python of version `3.6`.

1. You should have [terraform](https://www.terraform.io/downloads.html) in your `PATH` environment variable.
For example, you can download terraform and extract it to `/usr/local/bin`.
Also, you can create make `tf_bin` directory right where you are, copy `terraform` into this directory, and run
`export PATH=$PATH:$PWD/tf_bin`.
Official Terraform documentation points [here](https://stackoverflow.com/questions/14637979/how-to-permanently-set-path-on-linux-unix) for additional instructions. 

1. Your platform should have installed [pipenv](https://github.com/pypa/pipenv).

1. You must have access token of your Github account, and this account should be admin of
some Github organization.
You can generate it here: `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`.
This token needs permissions for 'repo', 'admin:org', and 'delete_repo'.

1. You must have service account on google cloud platform, with enabled billing.
You can find how to create it [here](https://cloud.google.com/iam/docs/creating-managing-service-accounts).
It doesn't matter for which project you will create service account, you will be able to use it for any API activity.

1. You must have existing project on google cloud platform, that will used as monitoring namespace.
This project must have service account attached, with `Monitoring Metric Writer` role assigned to this profile.
So, just switch to your monitoring project, go to `IAM` menu, and add service account as a member with this role. 
Once created go to 'Monitoring' and if it doesn't already exist, create a monitoring space in Stackdriver.


1. You must create, export and save your GCP service account private key in `json` format.

More details about [here](https://cloud.google.com/iam/docs/creating-managing-service-account-keys).

### Installing

1. Clone this repo:

    ```
    git clone https://github.com/mesoform/enterprise-cloud-admin.git && cd enterprise-cloud-admin
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
We prepared two example repos:

1. [example-ecat-project-config](https://github.com/mesoform/example-ecat-project-config) — contains terraform
variable files.
1. [example-ecat-deployment-code](https://github.com/mesoform/example-ecat-deployment-code) — contains terraform infrastructure code.

In order to perform test deployment, you should fork these repos to your organization, and customize config repo:

* `example-ecat-project-config/gcp/project_settings.auto.tfvars.json` — In this file, you should set unique `project_id` ([project creation docs](https://cloud.google.com/resource-manager/docs/creating-managing-projects)),
set or remove any remaining key value pair according your requirements.
Be aware, that `project_id` unique across whole GCP platform, even six month after deletion. So, if someone already have project with your id, you will receive unclear error.
* Also add a valid `billing_id`, it's mandatory ([billing docs](https://cloud.google.com/billing/docs/how-to/modify-project)).
* `folder_id` means folder numeric ID, [more information about how it can be obtained](https://cloud.google.com/resource-manager/docs/creating-managing-folders).
### Create config repo with eCat from template

```shell
./cloudctl -p <project id> \
  -o <github organization name> \
  -O <github organization name> \
  --vcs-token <github token> \
  --key-file resources/gcp_service_account_key.json \
  --monitoring-namespace <monitoring project id> \
  --debug true \
  config create \
  --config-repo <config repo> \
  --force
```

Where:

- `project id` — id of project, that will be created.
- `github organization name` — name of organization, that holds repos with code/config.
- `github token` — you developer's github token, that you have obtained in prerequisites section.
- `monitoring project id` — id of existing monitoring project. You should have one if followed prerequisites section.
- `config repo` — name of repo, that will contain terraform variables files.

#### Updating of config repo
If you want to override config files, you can just run again the same command as for creation.
If you see this:
```
{'message': 'Could not update file: At least 1 approving review is required by reviewers with write access.', 'documentation_url': 'https://help.github.com/articles/about-protected-branches'}
```
then, try to pass `--bypass-branch-protection` option to `config` subcommand.

### Test deployment using created code and config
When you created/forked example code and config repos, you can perform test deployment:

```shell
./cloudctl -p <project id> \
  -o <github organization name> \
  -O <github organization name> \
  --vcs-token <github token> \
  --key-file resources/gcp_service_account_key.json \
  --monitoring-namespace <monitoring project id> \
  deploy \
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

After that, you should receive success message in console, and metrics in your GCP monitoring project workspace.


## Logging
There is some command line arguments for logging setup:
1) `--json-logging` — this one will enable logging in json format.
2. `--disable-local-reporter` — in order to disable dumping of all metrics, you may want to pass this argument.

Both arguments related to root cli parser, so you can pass them this way:
```shell script
./cloudctl -p <project id> \
  -o <github organization name> \
  ...
  --json-logging \
  --disable-local-reporter \
  ...
  deploy --cloud gcp \
  ...
```

By default, we writing logs in `/var/log/enterprise_cloud_admin.log`,
so probably you need to create and change ownership of this file:
```shell script
touch /var/log/enterprise_cloud_admin.log
chown <user>:<group> /var/log/enterprise_cloud_admin.log
```


## Troubleshooting

### Google Cloud Platform and Stackdriver

Sometimes it's really hard to interpret immediately what GCP error means, so terraform community members
created curated list of common problems: [TROUBLESHOOTING.md](https://github.com/terraform-google-modules/terraform-google-project-factory/blob/master/docs/TROUBLESHOOTING.md).


## Contributing

Please read [CONTRIBUTING.md](https://github.com/mesoform/enterprise-cloud-admin/blob/master/CONTRIBUTING.md) for the process for submitting pull requests.

## License

This project is licensed under the [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
