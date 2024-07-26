#
# Copyright 2024 Canonical, Ltd.
#

import os

from k8s_test_harness.util import docker_util

ROCK_EXPECTED_FILES = [
    "/backup-driver",
    "/data-manager-for-plugin",
    "/plugins/libvixDiskLib.so",
    "/plugins/velero-plugin-for-vsphere",
    "/scripts/install.sh",
]


def test_velero_plugin_for_vsphere_rock():
    """Test Velero plugin for vSphere rock."""

    image_variable = "ROCK_VELERO_PLUGIN_FOR_VSPHERE"
    image = os.getenv(image_variable)
    assert image is not None, f"${image_variable} is not set"

    # check rock filesystem.
    docker_util.ensure_image_contains_paths(image, ROCK_EXPECTED_FILES)

    # check binaries.
    process = docker_util.run_in_docker(image, ["/backup-driver", "--help"])
    assert "Backup driver is a component in Velero vSphere plugin" in process.stdout

    process = docker_util.run_in_docker(image, ["/data-manager-for-plugin", "--help"])
    assert "Data manager is a component in Velero vSphere plugin" in process.stdout

    process = docker_util.run_in_docker(
        image, ["/plugins/velero-plugin-for-vsphere"], False
    )
    expected_err = (
        "This binary is a plugin. These are not meant to be executed directly."
    )
    assert expected_err in process.stderr

    # check script.
    process = docker_util.run_in_docker(image, ["/scripts/install.sh"], False)
    assert "No namespace specified in the namespace file" in process.stdout
