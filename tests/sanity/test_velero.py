#
# Copyright 2024 Canonical, Ltd.
#

import os

from k8s_test_harness.util import docker_util


def test_velero_rock():
    """Test Velero rock."""

    image_variable = "ROCK_VELERO_1_13_2"
    image = os.getenv(image_variable)
    assert image is not None, f"${image_variable} is not set"

    # check binary name and version.
    process = docker_util.run_in_docker(image, False, "/velero", "version")
    expected_err = "error finding Kubernetes API server config in --kubeconfig"
    assert expected_err in process.stderr

    # check helper binary.
    process = docker_util.run_in_docker(image, False, "/velero-helper")
    expected_err = "at least one argument must be provided, the working mode"
    assert expected_err in process.stderr

    # check restic and its version.
    process = docker_util.run_in_docker(image, True, "restic", "version")
    assert "restic" in process.stdout and "0.15.0" in process.stdout
