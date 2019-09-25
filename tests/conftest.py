from collections import namedtuple

import pytest

from cloud_control import ArgumentsParser


@pytest.fixture(scope="session")
def command_line_args():
    return ArgumentsParser(["-ptestproject", "deploy", "--cloud", "gcp"]).args


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
