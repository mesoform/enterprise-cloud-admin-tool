import os
import json

from collections import namedtuple

import pytest

from cloud_control import ArgumentsParser


@pytest.fixture(scope="session")
def working_directory(tmpdir_factory):
    return tmpdir_factory.mktemp("data")


@pytest.fixture(scope="session")
def command_line_args(working_directory):
    default_log_file = f"{working_directory.strpath}/enterprise_cloud_admin.log"

    return ArgumentsParser(
        [
            "-ptestproject",
            "--log-file",
            default_log_file,
            "deploy",
            "--cloud",
            "gcp",
        ]
    ).args


@pytest.fixture(scope="session")
def github_file_factory():
    file = namedtuple("GithubFile", ["name", "path", "decoded_content"])

    def factory(name, path, decoded_content):
        return file(name, path, decoded_content)

    return factory


@pytest.fixture(scope="session")
def code_files(github_file_factory):
    return [
        github_file_factory(
            "project.tf",
            "gcp/project.tf",
            b"""
            variable "project_id" {}
            variable "project_roles" {}
            variable "project_name" {}
            variable "org_id" {}
            variable "folder_id" {}
            variable "region" {}
            variable "skip_delete" {}
            
            provider "google" {
             region = "${var.region}"
            }
            
            resource "google_project" "project" {
             name            = "${var.project_name}"
             project_id      = "${var.project_id}"
            }
            
            resource "google_project_services" "project" {
             project = "${google_project.project.project_id}"
             services = [
               "compute.googleapis.com"
             ]
            }
            
            output "project_id" {
             value = "${google_project.project.project_id}"
            }
            """,
        )
    ]


@pytest.fixture(scope="session")
def config_files(github_file_factory):
    return [
        github_file_factory(
            "gcp_enabled_apis.auto.tfvars.json",
            "gcp/gcp_enabled_apis.auto.tfvars.json",
            b"""
            {
              "enabled_apis": [
                "compute.googleapis.com",
                "oslogin.googleapis.com"
              ]
            }
            """,
        ),
        github_file_factory(
            "gcp_project_settings.auto.tfvars.json",
            "gcp/gcp_project_settings.auto.tfvars.json",
            b"""
            {
              "project_id": "test-1234",
              "project_name": "MISSING",
              "billing_id": "MISSING",
              "folder_id": "MISSING",
              "org_id": "MISSING",
              "region": "MISSING"
            }
            """,
        ),
        github_file_factory(
            "gcp_role_bindings.auto.tfvars.json",
            "gcp/gcp_role_bindings.auto.tfvars.json",
            b"""
            {
              "project_roles": {
                "compute-admin": [],
                "viewer": []
              }
            }
            """,
        ),
        github_file_factory(
            "gcp_service_accounts.auto.tfvars.json",
            "gcp/gcp_service_accounts.auto.tfvars.json",
            b"""
            {
              "service_accounts":[
                {"compute-image-builder": "Account with shared VPC and image access"}
              ]
            }
            """,
        ),
    ]


@pytest.fixture
def project_state1():
    return {
        "version": 4,
        "terraform_version": "0.12.3",
        "serial": 3,
        "lineage": "3e192a43-85d6-a1e1-7bb2-d7265b16340a",
        "outputs": {
            "project_id": {
                "value": "testing-billing-test-123456789",
                "type": "string",
            }
        },
        "resources": [
            {
                "mode": "managed",
                "type": "google_project",
                "name": "project",
                "provider": "provider.google",
                "instances": [
                    {
                        "schema_version": 1,
                        "attributes": {
                            "app_engine": [],
                            "auto_create_network": True,
                            "billing_account": "018FB9-3FB698-74962C",
                            "folder_id": "",
                            "id": "testing-billing-test-123456789",
                            "labels": None,
                            "name": "testing-billing-test-123456789",
                            "number": "10394113145",
                            "org_id": "409420773147",
                            "policy_data": None,
                            "policy_etag": None,
                            "project_id": "testing-billing-test-123456789",
                            "skip_delete": None,
                            "timeouts": None,
                        },
                        "private": "eyJlMmJmYjczMC1lY2FhLTExZTYtOGY4OC0zNDM2M2Jj"
                        "N2M0YzAiOnsiY3JlYXRlIjoyNDAwMDAwMDAwMDAsImRl"
                        "bGV0ZSI6MjQwMDAwMDAwMDAwLCJyZWFkIjoyNDAwMDAw"
                        "MDAwMDAsInVwZGF0ZSI6MjQwMDAwMDAwMDAwfSwic2NoZ"
                        "W1hX3ZlcnNpb24iOiIxIn0=",
                    }
                ],
            },
            {
                "mode": "managed",
                "type": "google_project_services",
                "name": "project",
                "provider": "provider.google",
                "instances": [
                    {
                        "schema_version": 0,
                        "attributes": {
                            "disable_on_destroy": True,
                            "id": "testing-billing-test-123456789",
                            "project": "testing-billing-test-123456789",
                            "services": ["compute.googleapis.com"],
                            "timeouts": None,
                        },
                        "private": "eyJlMmJmYjczMC1lY2FhLTExZTYtOGY4OC0zNDM2M2Jj"
                        "N2M0YzAiOnsiY3JlYXRlIjoyNDAwMDAwMDAwMDAsImRl"
                        "bGV0ZSI6MjQwMDAwMDAwMDAwLCJyZWFkIjoyNDAwMDAw"
                        "MDAwMDAsInVwZGF0ZSI6MjQwMDAwMDAwMDAwfSwic2NoZ"
                        "W1hX3ZlcnNpb24iOiIxIn0=",
                        "depends_on": ["google_project.project"],
                    }
                ],
            },
        ],
    }


@pytest.fixture
def project_state2():
    return {
        "version": 4,
        "terraform_version": "0.12.3",
        "serial": 3,
        "lineage": "c87e8b0e-d952-595f-6074-056ccede2046",
        "outputs": {
            "project_id": {"value": "billing-test-123456789", "type": "string"}
        },
        "resources": [
            {
                "mode": "managed",
                "type": "google_project",
                "name": "project",
                "provider": "provider.google",
                "instances": [
                    {
                        "schema_version": 1,
                        "attributes": {
                            "app_engine": [],
                            "auto_create_network": True,
                            "billing_account": "018FB9-3FB698-74962C",
                            "folder_id": "",
                            "id": "billing-test-123456789",
                            "labels": None,
                            "name": "billing-test-123456789",
                            "number": "978341859879",
                            "org_id": "409420773147",
                            "policy_data": None,
                            "policy_etag": None,
                            "project_id": "billing-test-123456789",
                            "skip_delete": None,
                            "timeouts": None,
                        },
                        "private": "eyJlMmJmYjczMC1lY2FhLTExZTYtOGY4OC0zNDM2M2Jj"
                        "N2M0YzAiOnsiY3JlYXRlIjoyNDAwMDAwMDAwMDAsImRl"
                        "bGV0ZSI6MjQwMDAwMDAwMDAwLCJyZWFkIjoyNDAwMDAw"
                        "MDAwMDAsInVwZGF0ZSI6MjQwMDAwMDAwMDAwfSwic2NoZ"
                        "W1hX3ZlcnNpb24iOiIxIn0=",
                    }
                ],
            },
            {
                "mode": "managed",
                "type": "google_project_services",
                "name": "project",
                "provider": "provider.google",
                "instances": [
                    {
                        "schema_version": 0,
                        "attributes": {
                            "disable_on_destroy": True,
                            "id": "billing-test-123456789",
                            "project": "billing-test-123456789",
                            "services": ["compute.googleapis.com"],
                            "timeouts": None,
                        },
                        "private": "eyJlMmJmYjczMC1lY2FhLTExZTYtOGY4OC0zNDM2M2Jj"
                        "N2M0YzAiOnsiY3JlYXRlIjoyNDAwMDAwMDAwMDAsImRl"
                        "bGV0ZSI6MjQwMDAwMDAwMDAwLCJyZWFkIjoyNDAwMDAw"
                        "MDAwMDAsInVwZGF0ZSI6MjQwMDAwMDAwMDAwfSwic2NoZ"
                        "W1hX3ZlcnNpb24iOiIxIn0=",
                        "depends_on": ["google_project.project"],
                    }
                ],
            },
        ],
    }


@pytest.fixture
def state_of_deleted_project():
    return {
        "version": 4,
        "terraform_version": "0.12.3",
        "serial": 6,
        "lineage": "3e192a43-85d6-a1e1-7bb2-d7265b16340a",
        "outputs": {},
        "resources": [],
    }


@pytest.fixture
def google_credentials(working_directory, monkeypatch):
    filename = "gcp_key.json"
    credentials = json.dumps(
        {
            "type": "service_account",
            "project_id": "",
            "private_key_id": "",
            "private_key": "",
            "client_email": "",
            "client_id": "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "",
        }
    )
    filepath = f"{working_directory.strpath}/{filename}"
    with open(filepath, "w") as credentials_file:
        credentials_file.write(credentials)

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", filepath)

    yield filepath

    os.remove(filepath)
