# Enterprise Cloud Admin

This application pulls [Terraform](https://www.terraform.io/intro/index.html) code for deploying
cloud infrastructure, security defined policies, and environment configuration (currently from Github).
Then it compares the configuration against security policies and runs deploys
with [python-terraform](https://github.com/beelit94/python-terraform).
Afterwards it will log the changes and report stats to a monitoring system (currently [GCP Stackdriver](https://cloud.google.com/stackdriver/)).

## Getting Started

These instructions will get you an environment, ready for `enterprise-cloud-admin` development. 

### Prerequisites

1) You need to [download](https://www.terraform.io/downloads.html) and extract `terraform` binary
for your platform.
2) Your platform should have installed [pipenv](https://github.com/pypa/pipenv).
3) You must have access token of your Github account, and this account should be admin of
some Github organization.

    You can generate it here: `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`.
4) You must have service account on google cloud platform, with enabled billing.

    You can find how to create it [here](https://cloud.google.com/iam/docs/creating-managing-service-accounts).
    It doesn't matter for which project you will create service account, you will be able to use it for any API activity.

5) You must have existing project on google cloud platform, that will used as monitoring namespace.

    This project must have service account attached, with `Monitorin Metric Writer` role assigned to this profile.
    So, just switch to your monitoring project, go to `IAM` menu, and add service account as a member with this role.

6) You must create, export and save your GCP service account private key in `json` format.

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
pytest tests/
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
pytest tests
```


## Test deployment
You need to upload your terraform variable files and infrastructure code to
some repo of your organization account. To do so, at first, you must supply minimum GCP configuration.
```shell script
nano resources/templates/gcp_project_settings.auto.tfvars.json
```
In this file, you should set unique `project_id`.
Be aware, that it's unique across whole GCP platform, even six month after deletion.
So, if someone already have project with your id, you will receive unclear error.
Valid `billing_id` also mandatory.

Now you able to push variables and infrastructure code on VCS:
```shell script
./cloudctl -p <project id> -o <github organization name> -O <github organization name> --vcs-token <github token> --key-file resources/gcp_service_account_key.json --monitoring-namespace <monitoring project id> --debug true config create --force
``` 

And perform test deployment on GCP:
```shell script
./cloudctl -p <project id> -o <github organization name> -O <github organization name> --key-file resources/gcp_service_account_key.json --vcs-token <github token> --monitoring-namespace <monitoring project id> deploy --cloud gcp
```

After that, you should receive success message in console, and metrics in your GCP monitoring project workspace.


## Contributing

Please read [CONTRIBUTING.md](https://github.com/mesoform/enterprise-cloud-admin/blob/master/CONTRIBUTING.md) for the process for submitting pull requests.

## License

This project is licensed under the [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
