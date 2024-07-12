#
# Copyright 2024 Canonical, Ltd.
#

from k8s_test_harness.util import docker_util, env_util


def _test_velero_rock(image_version, restic_version):
    """Test Velero rock."""
    rock = env_util.get_build_meta_info_for_rock_version(
        "velero", image_version, "amd64"
    )
    image = rock.image

    # check binary name and version.
    process = docker_util.run_in_docker(image, ["/velero", "version"], False)
    expected_err = "error finding Kubernetes API server config in --kubeconfig"
    assert expected_err in process.stderr

    velero_version = docker_util.get_image_version(image)
    if velero_version != "1.9.5":
        # check helper binary.
        process = docker_util.run_in_docker(image, ["/velero-helper"], False)
        expected_err = "at least one argument must be provided, the working mode"
        assert expected_err in process.stderr

    # check restic and its version.
    process = docker_util.run_in_docker(image, ["restic", "version"])
    assert "restic" in process.stdout and restic_version in process.stdout


def test_velero_rock_1_13_2():
    _test_velero_rock("1.13.2", "0.15.0")


def test_velero_rock_1_12_1():
    _test_velero_rock("1.12.1", "0.15.0")


def test_velero_rock_1_9_5():
    _test_velero_rock("1.9.5", "0.14.0")
