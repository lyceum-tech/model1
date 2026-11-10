"""Regression fixtures proving the static security checks would have caught
the statically detectable findings of security/security-audit-2026103.md.

Each fixture reproduces the audit-era declaration at its real repository path
with synthetic values. No real key material is reproduced. Semantics are
diff-aware: a check fails only when the candidate introduces or worsens a
finding; pre-existing debt is listed but does not fail.
"""

import json
import unittest
from unittest.mock import patch

import repository_checks as checks
from test_gates import GitFixture


def evaluate(fixture, check_id, base_files, head_files):
    for path, content in base_files.items():
        fixture.write(path, content)
    before = checks.Snapshot(fixture.repo, fixture.commit())
    for path, content in head_files.items():
        fixture.write(path, content)
    after = checks.Snapshot(fixture.repo, fixture.commit())
    return checks.security_check(before, after, check_id)


def introduced(fixture, check_id, files):
    """Vulnerable files appear only in the candidate, as in the introducing PR."""
    return evaluate(fixture, check_id, {}, files)


def findings(result, rule):
    return [f for f in result["findings"] if f["rule"] == rule]


class WorkloadIsolationTest(GitFixture):
    CHECK = "workload-isolation"

    def test_f01_privileged_customer_container_fails(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/docker/container.go":
                "package docker\n\nfunc config() {\n\thostConfig.Privileged = true\n\t_ = hostConfig{Privileged: true}\n}\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F01"))

    def test_f01_unprivileged_container_passes(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/docker/container.go":
                "package docker\n\nfunc config() { _ = hostConfig{Privileged: false} }\n",
        })
        self.assertEqual(result["status"], "passed")
        self.assertEqual(findings(result, "SEC-F01"), [])

    def test_f01_privileged_compose_service_fails(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/compose.yaml": "services:\n  job:\n    privileged: true\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F01"))

    def test_f01_preexisting_debt_is_listed_but_does_not_fail(self):
        vulnerable = {"stream_execlet/docker/container.go": "package docker\nvar _ = hostConfig{Privileged: true}\n"}
        result = evaluate(self, self.CHECK, vulnerable, {"README.md": "unrelated\n"})
        self.assertEqual(result["status"], "passed")
        debt = findings(result, "SEC-F01")
        self.assertTrue(debt)
        self.assertTrue(all(f["kind"] == "pre-existing" for f in debt))

    def test_f01_worsening_preexisting_debt_fails(self):
        base = {"stream_execlet/docker/container.go": "package docker\nvar _ = hostConfig{Privileged: true}\n"}
        head = {"stream_execlet/docker/container.go":
                "package docker\nvar _ = hostConfig{Privileged: true}\nvar _ = hostConfig{Privileged: true}\n"}
        result = evaluate(self, self.CHECK, base, head)
        self.assertEqual(result["status"], "failed")

    def test_f15_trust_remote_code_fails(self):
        result = introduced(self, self.CHECK, {
            "iris/deployment_controller/internal/k8smanifest/build.go":
                'package k8smanifest\n\nfunc args() { args = append(args, "--trust-remote-code") }\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F15"))

    def test_f15_new_container_without_nonroot_fails_then_passes_with_it(self):
        container = 'package k8smanifest\n\nvar _ = corev1.Container{Name: "model"}\n'
        result = introduced(self, self.CHECK, {
            "iris/deployment_controller/internal/k8smanifest/build.go": container,
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F15"))

        fixed = container + "var _ = true\nvar _ = corev1.SecurityContext{RunAsNonRoot: &trueVal}\n"
        result = evaluate(self, self.CHECK, {}, {
            "iris/deployment_controller/internal/k8smanifest/build.go": fixed,
        })
        self.assertEqual(findings(result, "SEC-F15"), [])


class SecretsInSourceAndLogsTest(GitFixture):
    CHECK = "secrets-in-source-and-logs"

    def test_f02_embedded_private_key_fails_without_echoing_it(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/job/job.go":
                "package job\n\nconst privateKey = `-----BEGIN PRIVATE KEY-----\n"
                "synthetic-canary-key-material\n-----END PRIVATE KEY-----`\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F02"))
        self.assertNotIn("synthetic-canary-key-material", json.dumps(result))
        self.assertNotIn("BEGIN PRIVATE KEY", json.dumps(result))

    def test_f02_key_loaded_from_file_passes(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/job/job.go":
                'package job\n\nfunc load() { os.ReadFile(os.Getenv("EXECLET_S3_PRIVATE_KEY_FILE")) }\n',
        })
        self.assertEqual(result["status"], "passed")

    def test_f02_decrypted_credentials_logging_fails(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/job/job.go":
                'package job\n\nfunc run() { slog.Info("Decrypted S3 credentials", "creds", creds) }\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F02"))

    def test_f02_ordinary_logging_passes(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/job/job.go":
                'package job\n\nfunc run() { slog.Info("Executing job", "job_id", j.ID) }\n',
        })
        self.assertEqual(result["status"], "passed")

    def test_f20_whole_job_object_logging_fails(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/job/job.go":
                'package job\n\nfunc run() { slog.Info("Executing job", "job_id", j.ID, "job", j.Job) }\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F20"))

    def test_f20_logging_an_identifier_under_a_job_key_passes(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/exec/executionservice.go":
                'package exec\n\nfunc run() { slog.Warn("New execlet reported running job", "job", runningJobID) }\n',
        })
        self.assertEqual(result["status"], "passed")

    def test_f02_test_files_are_out_of_scope(self):
        result = introduced(self, self.CHECK, {
            "stream_execlet/job/job_test.go":
                "package job\n\nconst fixtureKey = `-----BEGIN PRIVATE KEY-----\nsynthetic\n-----END PRIVATE KEY-----`\n",
        })
        self.assertEqual(result["status"], "passed")


class StorageVersionAndSessionsTest(GitFixture):
    CHECK = "storage-version-and-sessions"

    def test_f03_minio_before_session_policy_fix_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/vars.yml": "ubuntu_minio_minio_version: RELEASE.2025-07-18T21-56-31Z\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F03"))

    def test_f03_minio_at_fix_floor_passes_and_downgrade_fails(self):
        fixed = "ubuntu_minio_minio_version: RELEASE.2025-10-15T17-29-55Z\n"
        result = introduced(self, self.CHECK, {"infra/ansible/vars.yml": fixed})
        self.assertEqual(result["status"], "passed")
        result = evaluate(self, self.CHECK, {"infra/ansible/vars.yml": fixed},
                          {"infra/ansible/vars.yml": "ubuntu_minio_minio_version: RELEASE.2025-07-18T21-56-31Z\n"})
        self.assertEqual(result["status"], "failed")

    def test_f04_year_long_storage_session_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/services/minio-identity-plugin/internal/handler/auth.go":
                "package handler\n\nconst OneYear = 31536000\n\nvar _ = AuthResponseSuccess{MaxValiditySeconds: OneYear}\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F04"))

    def test_f04_fifteen_minute_session_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/services/minio-identity-plugin/internal/handler/auth.go":
                "package handler\n\nconst FifteenMinutes = 900\n\nvar _ = AuthResponseSuccess{MaxValiditySeconds: FifteenMinutes}\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f04_api_key_lookup_without_expiry_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/services/minio-identity-plugin/internal/supabase/supabase.go":
                'package supabase\n\nvar _ = "%s/rest/v1/api_keys?key_hash=eq.%s&is_active=eq.true&select=user_id"\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F04"))

    def test_f04_api_key_lookup_with_expiry_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/services/minio-identity-plugin/internal/supabase/supabase.go":
                'package supabase\n\nvar _ = "%s/rest/v1/api_keys?key_hash=eq.%s&is_active=eq.true&select=user_id,expires_at"\n',
        })
        self.assertEqual(result["status"], "passed")


class CiFederationAndPrivilegeTest(GitFixture):
    CHECK = "ci-federation-and-standing-privilege"

    def test_f05_organization_wide_federation_binding_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/github/wif.tf":
                'resource "google_service_account_iam_member" "github_actions_wif_binding" {\n'
                '  member = "principalSet://iam.googleapis.com/pool/attribute.repository_owner/lyceum-tech"\n}\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F05"))

    def test_f05_repository_ref_binding_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/github/wif.tf":
                'resource "google_service_account_iam_member" "github_actions_wif_binding" {\n'
                '  member = "principalSet://iam.googleapis.com/pool/attribute.repository_ref/lyceum-tech/lyceum@refs/heads/main"\n}\n',
        })
        self.assertEqual(result["status"], "passed")

    def test_f12_standing_project_owner_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/project_iam_members/main.tf":
                'resource "google_project_iam_member" "owner" {\n  role = "roles/owner"\n}\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F12"))

    def test_f22_mutable_action_ref_and_stale_review_settings_fail(self):
        result = introduced(self, self.CHECK, {
            ".github/workflows/release.yml":
                "jobs:\n  release:\n    steps:\n      - uses: lyceum-tech/checkout-lyceum@main\n",
            "infra/terraform/_modules/github/repositories/rulesets.tf":
                "      dismiss_stale_reviews_on_push   = false\n      require_last_push_approval      = false\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(findings(result, "SEC-F22")), 3)

    def test_f22_pinned_action_and_strict_reviews_pass(self):
        result = introduced(self, self.CHECK, {
            ".github/workflows/release.yml":
                "jobs:\n  release:\n    steps:\n      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
            "infra/terraform/_modules/github/repositories/rulesets.tf":
                "      dismiss_stale_reviews_on_push   = true\n      require_last_push_approval      = true\n",
        })
        self.assertEqual(result["status"], "passed")


class NetworkExposureAndTransportTest(GitFixture):
    CHECK = "network-exposure-and-plaintext-transport"

    def test_f06_public_ssh_firewall_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/legacy/main.tf":
                'resource "google_compute_firewall" "ssh" {\n'
                "  allow {\n    protocol = \"tcp\"\n    ports    = [\"22\"]\n  }\n"
                '  source_ranges = ["0.0.0.0/0"]\n}\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F06"))

    def test_f06_public_https_and_subnet_ssh_pass(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/legacy/main.tf":
                'resource "google_compute_firewall" "https" {\n'
                "  allow {\n    protocol = \"tcp\"\n    ports    = [\"80\", \"443\"]\n  }\n"
                '  source_ranges = ["0.0.0.0/0"]\n}\n'
                'resource "google_compute_firewall" "ssh" {\n'
                "  allow {\n    protocol = \"tcp\"\n    ports    = [\"22\"]\n  }\n"
                "  source_ranges = [var.main_subnetwork_ip_cidr_range]\n}\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f06_broad_tailnet_vpc_grant_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/tailscale/main.tf":
                '        dst = [\n          "${cfg.gcp_main_subnet_ip_cidr_range}:*",\n        ]\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F06"))

    def test_f09_https_upstream_without_verification_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/ubuntu-proxy.yml":
                "          proxy_pass https://inference.example.invalid;\n          proxy_ssl_server_name on;\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F09"))

    def test_f09_verified_upstream_passes_and_removing_verification_fails(self):
        verified = ("          proxy_pass https://inference.example.invalid;\n"
                    "          proxy_ssl_verify on;\n          proxy_ssl_verify_depth 5;\n")
        result = introduced(self, self.CHECK, {"infra/ansible/playbooks/ubuntu-proxy.yml": verified})
        self.assertEqual(result["status"], "passed")
        result = evaluate(self, self.CHECK,
                          {"infra/ansible/playbooks/ubuntu-proxy.yml": verified},
                          {"infra/ansible/playbooks/ubuntu-proxy.yml":
                           "          proxy_pass https://inference.example.invalid;\n"})
        self.assertEqual(result["status"], "failed")

    def test_f13_plaintext_internal_transports_fail(self):
        result = introduced(self, self.CHECK, {
            "infra/inventory/common/config.yml": "LYC_ATLAS_BASE_URL: http://atlas\n",
            "infra/terraform/_modules/gcp/iris/cloud_run_inference_proxy.tf":
                '        value = "redis://${var.redis_ip_address}:${var.redis_port}"\n',
            "iris/inference_worker/src/config.py":
                '        return f"amqp://{username}:{password}@{host}/{vhost}"\n',
            "infra/ansible/playbooks/ubuntu-proxy.yml":
                "                  proxy_pass http://gateway:8000;\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(findings(result, "SEC-F13")), 4)

    def test_f13_tls_transports_and_localhost_default_pass(self):
        result = introduced(self, self.CHECK, {
            "infra/inventory/common/config.yml": "LYC_ATLAS_BASE_URL: https://atlas\n",
            "iris/inference_worker/src/config.py":
                '    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")\n'
                '        return f"amqps://{username}:{password}@{host}/{vhost}"\n',
        })
        self.assertEqual(result["status"], "passed")


class ServiceIdentityMeshEndpointAuthTest(GitFixture):
    CHECK = "service-identity-mesh-and-endpoint-auth"

    def test_f07_shared_wildcard_leaf_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/k3s_server/templates/iris-endpoint-tls.yaml.j2":
                '  dnsNames:\n    - "*.{{ k3s_server_iris_dns_zone }}"\n    - localhost\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F07"))

    def test_f07_long_lived_certificates_fail(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/k3s_server/defaults/main.yml":
                "k3s_server_iris_endpoint_ca_duration: 87600h\nk3s_server_iris_endpoint_cert_duration: 43800h\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(findings(result, "SEC-F07")), 2)

    def test_f07_short_lived_per_workload_certificate_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/k3s_server/templates/iris-endpoint-tls.yaml.j2":
                '  dnsNames:\n    - "{{ deployment_id }}.{{ k3s_server_iris_dns_zone }}"\n',
            "infra/ansible/playbooks/roles/k3s_server/defaults/main.yml":
                "k3s_server_iris_endpoint_ca_duration: 8760h\nk3s_server_iris_endpoint_cert_duration: 720h\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f08_dynamo_builder_without_endpoint_auth_fails(self):
        result = introduced(self, self.CHECK, {
            "iris/deployment_controller/internal/k8smanifest/build.go":
                "package k8smanifest\n\n"
                "func buildDGD(tmpl *Template) error {\n"
                "\tserveFrontendOverTLS(frontend, secret)\n\treturn nil\n}\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F08"))

    def test_f08_dynamo_builder_with_endpoint_auth_passes(self):
        result = introduced(self, self.CHECK, {
            "iris/deployment_controller/internal/k8smanifest/build.go":
                "package k8smanifest\n\n"
                "func buildDGD(tmpl *Template) error {\n"
                '\tfrontendEnv = append(frontendEnv, corev1.EnvVar{Name: "VLLM_API_KEY", Value: token})\n'
                "\treturn nil\n}\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f10_consul_without_acl_or_tls_verification_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/consul/templates/consul.hcl.j2":
                'bind_addr = "0.0.0.0"\nclient_addr = "0.0.0.0"\nencrypt = "{{ consul_encryption_key }}"\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F10"))

    def test_f10_consul_with_acl_and_tls_verification_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/consul/templates/consul.hcl.j2":
                'bind_addr = "0.0.0.0"\nacl {\n  enabled = true\n}\nverify_incoming = true\nverify_outgoing = true\n',
        })
        self.assertEqual(result["status"], "passed")


class SshBootstrapAndHandoverTest(GitFixture):
    CHECK = "ssh-bootstrap-and-vm-handover"

    def test_f11_disabled_host_key_verification_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/ansible.cfg": "[defaults]\nhost_key_checking = False\n",
            "infra/services/hydra-autoscaler/internal/ssh/ssh.go":
                "package ssh\n\nvar _ = &ssh.ClientConfig{HostKeyCallback: ssh.InsecureIgnoreHostKey()}\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(findings(result, "SEC-F11")), 2)

    def test_f11_verified_host_keys_pass(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/ansible.cfg": "[defaults]\nhost_key_checking = True\n",
            "infra/services/hydra-autoscaler/internal/ssh/ssh.go":
                "package ssh\n\nvar _ = &ssh.ClientConfig{HostKeyCallback: callback}\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f24_nonexclusive_customer_key_handover_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/lyceum_user/tasks/hand_over_ssh.yml":
                "    - name: Configure SSH access for lyceum user with provided public key\n"
                "      ansible.posix.authorized_key:\n        user: lyceum\n        state: present\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F24"))

    def test_f24_exclusive_customer_key_handover_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/lyceum_user/tasks/hand_over_ssh.yml":
                "    - name: Configure SSH access for lyceum user with provided public key\n"
                "      ansible.posix.authorized_key:\n        user: lyceum\n        state: present\n        exclusive: true\n",
        })
        self.assertEqual(result["status"], "passed")


class PlatformHardeningTest(GitFixture):
    CHECK = "platform-hardening-and-lifecycle"

    def test_f14_k3s_without_secret_encryption_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/k3s_server/templates/config.yaml.j2":
                'cluster-cidr: "{{ k3s_server_cluster_cidr }}"\nservice-cidr: "{{ k3s_server_service_cidr }}"\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F14"))

    def test_f14_k3s_with_secret_encryption_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/k3s_server/templates/config.yaml.j2":
                'cluster-cidr: "{{ k3s_server_cluster_cidr }}"\nsecrets-encryption: true\n',
        })
        self.assertEqual(result["status"], "passed")

    def test_f17_raw_filesystem_without_encryption_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/block_volumes/tasks/main.yml":
                "- name: Create a filesystem on volumes that have never carried one\n"
                "  community.general.filesystem:\n    fstype: ext4\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F17"))

    def test_f17_encrypted_volume_provisioning_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/roles/block_volumes/tasks/main.yml":
                "- name: Open LUKS volume\n  community.crypto.luks_device:\n"
                "- name: Create a filesystem\n  community.general.filesystem:\n    fstype: ext4\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f18_disabled_unattended_upgrades_fail(self):
        result = introduced(self, self.CHECK, {
            "infra/ansible/playbooks/k3s-server.yml":
                "    - role: apt_unattended_upgrades\n      vars:\n        apt_unattended_upgrades_enabled: false\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F18"))

    def test_f19_mutable_images_fail(self):
        result = introduced(self, self.CHECK, {
            "infra/inventory/production/config.yml":
                "LYC_GCP_INFERENCE_WORKER_IMAGE_REF: registry.example.invalid/inference_worker:latest\n",
            "iris/inference_proxy/Dockerfile": "FROM alpine:3.21\n",
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(findings(result, "SEC-F19")), 2)

    def test_f19_digest_pinned_images_pass(self):
        result = introduced(self, self.CHECK, {
            "infra/inventory/production/config.yml":
                "LYC_GCP_INFERENCE_WORKER_IMAGE_REF: registry.example.invalid/inference_worker@sha256:" + "a" * 64 + "\n",
            "iris/inference_proxy/Dockerfile":
                "FROM registry.example.invalid/go-runtime@sha256:" + "b" * 64 + "\nFROM builder\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f21_instance_without_backups_fails(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/cloud_sql/instances.tf":
                'resource "google_sql_database_instance" "main" {\n  settings {\n    tier = "db-custom-2-7680"\n  }\n}\n',
        })
        self.assertEqual(result["status"], "failed")
        self.assertTrue(findings(result, "SEC-F21"))

    def test_f21_instance_with_backups_and_pitr_passes(self):
        result = introduced(self, self.CHECK, {
            "infra/terraform/_modules/gcp/cloud_sql/instances.tf":
                'resource "google_sql_database_instance" "main" {\n'
                "  settings {\n    backup_configuration {\n      enabled = true\n"
                "      point_in_time_recovery_enabled = true\n    }\n  }\n}\n",
        })
        self.assertEqual(result["status"], "passed")

    def test_f21_removing_backups_from_existing_instance_fails(self):
        protected = ('resource "google_sql_database_instance" "main" {\n'
                     "  backup_configuration {\n    enabled = true\n"
                     "    point_in_time_recovery_enabled = true\n  }\n}\n")
        result = evaluate(self, self.CHECK,
                          {"infra/terraform/_modules/gcp/cloud_sql/instances.tf": protected},
                          {"infra/terraform/_modules/gcp/cloud_sql/instances.tf":
                           'resource "google_sql_database_instance" "main" {\n}\n'})
        self.assertEqual(result["status"], "failed")


class EngineSemanticsTest(GitFixture):
    def test_unknown_check_is_incomplete_not_passed(self):
        before = checks.Snapshot(self.repo, self.commit())
        result = checks.security_check(before, before, "no-such-check")
        self.assertEqual(result["status"], "incomplete")

    def test_fixing_a_finding_passes_with_no_findings(self):
        result = evaluate(self, "workload-isolation",
                          {"stream_execlet/docker/container.go": "package docker\nvar _ = hostConfig{Privileged: true}\n"},
                          {"stream_execlet/docker/container.go": "package docker\nvar _ = hostConfig{Privileged: false}\n"})
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["findings"], [])

    def test_candidate_policy_file_cannot_weaken_checks(self):
        result = evaluate(self, "workload-isolation", {},
                          {"stream_execlet/docker/container.go": "package docker\nvar _ = hostConfig{Privileged: true}\n",
                           "review_rules/policy.json": "{}"})
        self.assertEqual(result["status"], "failed")

    def test_patched_policy_drives_evaluation(self):
        mini = {"security": [{"id": "mini", "findings": [
            {"finding": "FX", "kind": "forbidden", "paths": ["src/**/*.py"], "patterns": [r"eval\("]},
        ]}]}
        with patch("repository_checks.policy", return_value=mini):
            result = evaluate(self, "mini", {}, {"src/app.py": "eval(user_input)\n"})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["findings"][0]["rule"], "SEC-FX")


if __name__ == "__main__":
    unittest.main()
