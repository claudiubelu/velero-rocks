#
# Copyright 2024 Canonical, Ltd.
#

import os

from k8s_test_harness.util import docker_util


def test_kubectl_rock():
    """Test kubectl rock."""

    image_variable = "ROCK_KUBECTL_1_30_2"
    image = os.getenv(image_variable)
    assert image is not None, f"${image_variable} is not set"

    # check binary name and version.
    process = docker_util.run_in_docker(image, ["kubectl", "version"], False)

    assert "Client Version: v1.30" in process.stdout
