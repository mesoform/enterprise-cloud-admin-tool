import os
import json
import textwrap

from collections import namedtuple

import pytest

from cloud_control import ArgumentsParser
from reporter.base import MetricsRegistry


@pytest.fixture(scope="session")
def working_directory(tmpdir_factory):
    return tmpdir_factory.mktemp("data")


@pytest.fixture(scope="session")
def command_line_args(working_directory):
    default_log_file = f"{working_directory.strpath}/enterprise_cloud_admin.log"
    default_metrics_file = (
        f"{working_directory.strpath}/enterprise_cloud_admin_metrics"
    )

    return ArgumentsParser(
        [
            "--monitoring-namespace",
            "monitoring-namespace",
            "--log-file",
            default_log_file,
            "--metrics-file",
            default_metrics_file,
            "--monitoring-system",
            "stackdriver",
            "deploy",
            "testproject",
            "--cloud",
            "gcp",
            "--code-repo",
            "testrepo1",
            "--config-repo",
            "testrepo2",
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
            variable "role_bindings" {}
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
            
            resource "google_project_service" "project" {
              project = "${google_project.project.project_id}"
              service = "compute.googleapis.com"
              disable_on_destroy = false
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
            "enabled_apis.auto.tfvars.json",
            "gcp/enabled_apis.auto.tfvars.json",
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
            "project_settings.auto.tfvars.json",
            "gcp/project_settings.auto.tfvars.json",
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
            "iam.auto.tfvars.json",
            "gcp/iam.auto.tfvars.json",
            b"""
            {
              "role_bindings": {
                "compute-admin": [],
                "viewer": []
              }
            }
            """,
        ),
        github_file_factory(
            "service_accounts.auto.tfvars.json",
            "gcp/service_accounts.auto.tfvars.json",
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
                            "skip_delete": True,
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
                            "skip_delete": False,
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
            # random hash
            "private_key_id": "36a0f83abf1d1781f1ea1ca7cc513c67530693fd",
            # random rsa private key
            "private_key": textwrap.dedent(
                """\
            -----BEGIN RSA PRIVATE KEY-----
            MIIEpAIBAAKCAQEA5zIskf9Bb4Wj9sW6zQSyMBmcOTPFUGdhFxMzZbsb28fA4MbP
            Rh73jSNq/QccYrbBQMXIVSVxwN8tcL6vWX4rhjmxX07nKV1F8Cs6rdyJBQEcNFye
            sJrwF7Ub52irGYpjbGf/ZwMEaE424ZHeueGzuFdm0QPdwh9L7ocKfjPBuuycNVEU
            KmRdPwk21Ai+POk2FN3XP4L+uvD9xSTT48+ltQ4DCtVAyuwdIxOTcl2A0MHFBk1D
            Hb5QizvlODei4a35g4lptOseHl1SrhCk+pCg1ZLQacin094iAWHYFKPVu/LKrLc1
            UkDdXa2LXBywgmxlVjtURgUHAqjJkUwrAeKrJwIDAQABAoIBAQC0xjqrfdeAiBKI
            5lsF6+IYUi4hXCWwlOUJ0e2iYgeKdkqOd2WjApu2NDd32ZOMbDH3n67hRQIJOXii
            a7dYVptZvMrAJ0YAxfnlrSeYwpQw4YlYOAOtO7j4EJjc/K6srdTH8xl1RpqvpFit
            UA3DcoPAZDb0v/0pyKbqv5So0Xdt3BAWKqf4SrKb5N9VO1v0ijQtq1cRC60mWLNB
            LMYrTy12hiK/S/rZn9akED1LNtHOpq2EhOwLZ953kmdciVFgQHLIJ2GHoRLk2RxF
            45QfwTHMs+3ZyCaMeQ85XRAFoy0u6fGnIZVvnDX1kuxeB2I1hZ7GcToGUqRJ8I5T
            7LEyvAXhAoGBAP0z8z9RulXV2UY2HQ4Ft3o0bXDYfotikhBLHLeSSwmM14XJW6lE
            4RqE8tQVg9DRwevKRKcZtZZ+OO4lAe1mCUtLGmXYLIoh9FRclZqni0d4++/qTKuu
            PxxLGaMGNabR9LDYyfm8vFK+dzcbb/Gb8HH78ndOdJrjLL1sO3MBx/DFAoGBAOm/
            /S8N2FrJSYqxpnY+9PFKnDf6+f0TpAASQr5Wug9o1t13RmzVD8joY8Ncq4CHj0O0
            /1rFKyXXSxvE0FOUSwCgadniIHYaH+QBgpVytQKljtngCAXgH3QVx0+j2JPllKst
            dB0vKFAacSD97vKXZJvyjcL4vWQBzkuguVQHeNL7AoGAOFR6ZTfVcIsmz0vyos/6
            xaEsR9KiNHg1bpKHTP+q2fEPcaAeWEYOnku9ihlPPgGsVrylEVfS4iwqljB9gUcW
            Aj4vHUE+h2yOYsZGMiXcAoaT5ggGDpuxRqYeifozrW1ANqfEJ18ptm7RLt1XxjSf
            BXy7sHcv0dWAepO9lhRrWtECgYA7LbAbyZWM5okH5BIQvb+llw4V3iSMPfy3R+g9
            6BcS76f2Scw6oXZtlugq/bstvyQ2MAy2HlTeL7OERD+56UFT10j1MJqnS9XnE7rL
            u064bNHNtzpQwn00Fo9vSjv6tZT+AXP0L4w1O3yIrcFhCZMfKDlbsz2/o/VmkDpb
            W8jrIQKBgQC4aE5RLg57pb08Q7UKBCNAsobfWOKBmiuPpmYneijdvjDILyM8a43d
            FSwXLhkaUPvUycDNO38ES9NS1UsMlkC/tRq2iVnKWL0lNJ0+I5f2kDNsTOkFX/N7
            zU1w9KOJBJgLFCQeYupLKu4ojIzrtGtAoaY7fmvjPcUOhuqVQ0nxWA==
            -----END RSA PRIVATE KEY-----"""
            ),
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


@pytest.fixture
def sha256_hash():
    return "cfe3246ba56244faf3f8e58fa2bca3dd21f83ae1"


@pytest.fixture
def short_code_config_hash(sha256_hash):
    return f"{sha256_hash[:7]}-{sha256_hash[:7]}"


@pytest.fixture
def metrics_registry():
    metrics_registry = MetricsRegistry("deploy")
    metrics_registry.add_metric("time", 453.77329)
    metrics_registry.add_metric("successes", 1)
    metrics_registry.add_metric("failures", 1)
    return metrics_registry
