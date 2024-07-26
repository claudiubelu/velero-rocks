#
# Copyright 2024 Canonical, Ltd.
#
import logging
import uuid
from pathlib import Path

import pytest
from k8s_test_harness import harness
from k8s_test_harness.util import env_util, k8s_util
from packaging import version

LOG = logging.getLogger(__name__)

DIR = Path(__file__).absolute().parent
MANIFESTS_DIR = DIR / ".." / "templates"


VELERO_CHART_VERSIONS = [
    # (velero_version, chart_version)
    ("1.13.2", "6.7.0"),
    ("1.12.1", "5.2.2"),
    ("1.9.5", "2.32.6"),
]


def _get_velero_helm_cmd(velero_version, chart_version):
    velero_rock = env_util.get_build_meta_info_for_rock_version(
        "velero", velero_version, "amd64"
    )
    kubectl_rock = env_util.get_build_meta_info_for_rock_version(
        "kubectl", "1.30.2", "amd64"
    )
    images = [
        k8s_util.HelmImage(velero_rock.image),
        k8s_util.HelmImage(kubectl_rock.image, "kubectl"),
    ]

    credentials = """
[default]
aws_access_key_id = minio
aws_secret_access_key = minio123
"""
    minio_url = "http://minio.velero.svc:9000"

    # Velero chart version 4.0.0 introduced multiple backup storage locations.
    # Previously, the configuration.provider configuration was different.
    index = ""
    provider = "provider"
    if version.Version(chart_version) >= version.Version("4.0.0"):
        index = "[0]"
        provider = "backupStorageLocation[0].provider"

    set_configs = [
        f"credentials.secretContents.cloud={credentials}",
        f"configuration.{provider}=aws",
        f"configuration.backupStorageLocation{index}.bucket=velero",
        f"configuration.backupStorageLocation{index}.config.region=minio",
        f"configuration.backupStorageLocation{index}.config.s3ForcePathStyle=true",
        f"configuration.backupStorageLocation{index}.config.s3Url={minio_url}",
        "snapshotsEnabled=false",
        "initContainers[0].name=velero-plugin-for-aws",
        "initContainers[0].image=velero/velero-plugin-for-aws:v1.2.1",
        "initContainers[0].volumeMounts[0].mountPath=/target",
        "initContainers[0].volumeMounts[0].name=plugins",
    ]

    return k8s_util.get_helm_install_command(
        "velero",
        "velero",
        namespace="velero",
        repository="https://vmware-tanzu.github.io/helm-charts",
        images=images,
        set_configs=set_configs,
        chart_version=chart_version,
    )


def _exec_velero_cmd(instance, deployment_name, namespace, *cmd):
    instance.exec(
        [
            "k8s",
            "kubectl",
            "exec",
            "-ti",
            "--namespace",
            namespace,
            f"deployment.apps/{deployment_name}",
            "--",
            "/velero",
            *cmd,
        ]
    )


@pytest.mark.parametrize("velero_version,chart_version", VELERO_CHART_VERSIONS)
def test_integration_velero(
    function_instance: harness.Instance, velero_version, chart_version
):
    # Setup Minio first, which is an S3-compatible storage service. We'll use
    # it to test out Velero's functionality with it.
    manifest = MANIFESTS_DIR / "minio-deployment.yaml"
    function_instance.exec(
        ["k8s", "kubectl", "apply", "-f", "-"],
        input=Path(manifest).read_bytes(),
    )

    k8s_util.wait_for_deployment(function_instance, "minio", "velero")

    # Deploy Velero rock.
    function_instance.exec(_get_velero_helm_cmd(velero_version, chart_version))
    k8s_util.wait_for_deployment(function_instance, "velero", "velero")

    # Deploy an nginx app which we'll back up.
    manifest = MANIFESTS_DIR / "nginx-deployment.yaml"
    function_instance.exec(
        ["k8s", "kubectl", "apply", "-f", "-"],
        input=Path(manifest).read_bytes(),
    )

    k8s_util.wait_for_deployment(function_instance, "nginx-deployment", "nginx-example")

    # Back the nginx app.
    backup_name = f"nginx-backup-{uuid.uuid4()}"
    _exec_velero_cmd(
        function_instance,
        "velero",
        "velero",
        "backup",
        "create",
        backup_name,
        "--selector",
        "app=nginx",
    )

    # Delete the nginx app, we should be able to restore it.
    function_instance.exec(
        [
            "k8s",
            "kubectl",
            "delete",
            "--wait",
            "namespace",
            "nginx-example",
            "--timeout",
            "60s",
        ]
    )

    # Restore it, and expect it to become available.
    _exec_velero_cmd(
        function_instance,
        "velero",
        "velero",
        "restore",
        "create",
        "--from-backup",
        backup_name,
    )

    k8s_util.wait_for_deployment(function_instance, "nginx-deployment", "nginx-example")
