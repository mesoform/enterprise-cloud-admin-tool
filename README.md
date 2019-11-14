# Enterprise Cloud Admin

This application pulls [Terraform](https://www.terraform.io/intro/index.html) code for deploying
cloud infrastructure, security defined policies, and environment configuration (currently from Github).
Then it compares the configuration against security policies and runs deploys
with [python-terraform](https://github.com/beelit94/python-terraform).
Afterwards it will log the changes and report stats to a monitoring system (currently [GCP Stackdriver](https://cloud.google.com/stackdriver/)).

## Getting Started

These instructions will get you an environment, ready for `enterprise-cloud-admin` development. 

### Prerequisites

1) This tool designed to work with Python of version `3.6`.
2) You should have [terraform](https://www.terraform.io/downloads.html) in your `PATH` environment variable.

    For example, you can download terraform and extract it to `/usr/local/bin`.

    Also, you can create make `tf_bin` directory right where you are, copy `terraform` into this directory, and run
    `export PATH=$PATH:$PWD/tf_bin`.

    Official Terraform documentation points [here](https://stackoverflow.com/questions/14637979/how-to-permanently-set-path-on-linux-unix) for additional instructions. 

3) Your platform should have installed [pipenv](https://github.com/pypa/pipenv).
4) You must have access token of your Github account, and this account should be admin of
some Github organization.

    You can generate it here: `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`.
5) You must have service account on google cloud platform, with enabled billing.

    You can find how to create it [here](https://cloud.google.com/iam/docs/creating-managing-service-accounts).
    It doesn't matter for which project you will create service account, you will be able to use it for any API activity.

6) You must have existing project on google cloud platform, that will used as monitoring namespace.

    This project must have service account attached, with `Monitoring Metric Writer` role assigned to this profile.
    So, just switch to your monitoring project, go to `IAM` menu, and add service account as a member with this role.

7) You must create, export and save your GCP service account private key in `json` format.

    More details about [here](https://cloud.google.com/iam/docs/creating-managing-service-account-keys).

### Installing

1) Clone this repo:

    ```shell script
    git clone https://github.com/mesoform/enterprise-cloud-admin.git && cd enterprise-cloud-admin
    ```

2) Install all dependencies:
    ```shell script
    pipenv install --dev
    ```

3) Activate virtual environment:
    ```shell script
    pipenv shell
    ```

4) Copy `terraform` binary in current directory. Path for this binary is
configurable, check `cat settings/default_settings.py | grep TERRAFORM_BINARY_PATH`.
    ```shell script
    cp ~/Downloads/terraform $(pwd)/terraform
    ```

5) Copy GCP service account token in `resources` directory:
    ```shell script
    cp ~/Downloads/gcp_service_account_key.json $(pwd)/resources/gcp_service_account_key.json
    ```

## Running the tests

```shell script
pytest
```

### Running tests inside docker container
If you just cloned repo and have docker installed, you can just build the container and run
tests without installing anything in your environment.

Build container and run pipenv shell:
```shell script
docker build . -t test_eca
docker run -it test_eca
```

After that, you will be attached to container's pipenv shell. You can run tests:
```shell script
pytest
```

### Parametrized tests
You can run pytest in verbose mode:
```shell script
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
You need to upload your terraform variable files and infrastructure code to
some repo of your organization account. To do so, at first, you must supply minimum GCP configuration.
```shell script
nano resources/templates/gcp_project_settings.auto.tfvars.json
```
In this file, you should set unique `project_id` ([project creation docs](https://cloud.google.com/resource-manager/docs/creating-managing-projects)).
Be aware, that it's unique across whole GCP platform, even six month after deletion.
So, if someone already have project with your id, you will receive unclear error.
Valid `billing_id` also mandatory ([billing docs](https://cloud.google.com/billing/docs/how-to/modify-project)).


Now you able to push variables and infrastructure code on VCS:
```shell script
./cloudctl -p <project id> -o <github organization name> -O <github organization name> --vcs-token <github token> --key-file resources/gcp_service_account_key.json --monitoring-namespace <monitoring project id> --debug true config create --force
``` 

And perform test deployment on GCP:
```shell script
./cloudctl -p <project id> -o <github organization name> -O <github organization name> --key-file resources/gcp_service_account_key.json --vcs-token <github token> --monitoring-namespace <monitoring project id> deploy --cloud gcp
```

Where:
 - `project id` — id of project, that will be created.
 - `github organization name` — name of organization, that holds repos with code/config.
 - `github token` — you developer's github token, that you have obtained in prerequisites section.
 - `monitoring project id` — id of existing monitoring project. You should have one if followed prerequisites section.

After that, you should receive success message in console, and metrics in your GCP monitoring project workspace.


## Contributing

Please read [CONTRIBUTING.md](https://github.com/mesoform/enterprise-cloud-admin/blob/master/CONTRIBUTING.md) for the process for submitting pull requests.

## License

This project is licensed under the [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
