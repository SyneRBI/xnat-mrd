import os
import re
import subprocess
import time
from pathlib import Path

import pytest
import requests
import xnat
import xnat4tests
import ismrmrd
from mrd_2_xnat import mrd_2_xnat


@pytest.fixture
def mrd_file_path():
    """Provides the mrd_data filepath"""

    mrd_data = (
        Path(__file__).parents[2]
        / "test-data"
        / "ptb_resolutionphantom_fully_ismrmrd.h5"
    )

    return mrd_data


@pytest.fixture
def mrd_headers(mrd_file_path):
    with ismrmrd.Dataset(mrd_file_path, "dataset", create_if_needed=False) as dset:
        header = dset.read_xml_header()
        xnat_hdr = mrd_2_xnat(header, Path(__file__).parents[1] / "ismrmrd.xsd")

    return xnat_hdr


@pytest.fixture(scope="session")
def xnat_version():
    try:
        version = os.environ["XNAT_VERSION"]
    except KeyError:
        version = "1.9.2"

    return version


@pytest.fixture(scope="session")
def xnat_container_service_version():
    try:
        version = os.environ["XNAT_CS_VERSION"]
    except KeyError:
        version = "3.7.2"

    return version


@pytest.fixture
def ensure_mrd_project(xnat_session):
    project_id = "mrd"
    if project_id not in xnat_session.projects:
        xnat_session.put(f"/data/archive/projects/{project_id}")
        xnat_session.projects.clearcache()
    yield


@pytest.fixture
def remove_test_data(xnat_session):
    yield
    for project in list(xnat_session.projects):
        for subject in list(project.subjects.values()):
            try:
                xnat_session.delete(
                    path=f"/data/projects/{project.id}/subjects/{subject.label}",
                    query={"removeFiles": "True"},
                )
            except xnat.exceptions.XNATResponseError as e:
                print(f"Could not delete subject {subject.label}: {e}")
        project.subjects.clearcache()


@pytest.fixture(scope="session")
def xnat_config(tmp_path_factory, xnat_version, xnat_container_service_version):
    tmp_dir = tmp_path_factory.mktemp("data")

    return xnat4tests.Config(
        xnat_root_dir=tmp_dir,
        docker_image="xnat_mrd_xnat4tests",
        docker_container="xnat_mrd_xnat4tests",
        build_args={
            "xnat_version": xnat_version,
            "xnat_cs_plugin_version": xnat_container_service_version,
        },
    )


@pytest.fixture(scope="session")
def jar_path():
    jar_dir = Path(__file__).parents[2] / "build" / "libs"
    return list(jar_dir.glob("mrd-*xpl.jar"))[0]


@pytest.fixture(scope="session")
def plugin_version(jar_path):
    match_version = re.search("mrd-(.+?)-xpl.jar", jar_path.name)

    if match_version is None:
        raise NameError(
            "Jar name contains no version - did you pull the latest tags from github before running gradlew?"
        )
    else:
        return match_version.group(1)


@pytest.fixture(scope="session")
def xnat_session(xnat_config, jar_path):
    plugin_path = Path("/data/xnat/home/plugins")
    if not jar_path.exists():
        raise FileNotFoundError(f"Plugin JAR file not found at {jar_path}")

    xnat4tests.start_xnat(xnat_config, rebuild=False, relaunch=False)

    # Install Mrd plugin by copying the jar into the container

    status = subprocess.run(
        [
            "docker",
            "exec",
            "xnat_mrd_xnat4tests",
            "ls",
            plugin_path.as_posix(),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    plugins_list = status.stdout.split("\n")

    if jar_path.name not in plugins_list:
        print("Jar not in plugins_list so restarting XNAT")
        try:
            subprocess.run(
                [
                    "docker",
                    "cp",
                    str(jar_path),
                    f"xnat_mrd_xnat4tests:{(plugin_path / jar_path.name).as_posix()}",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Command {e.cmd} returned with error code {e.returncode}: {e.output}"
            ) from e

    xnat4tests.restart_xnat(xnat_config)
    print("Waiting for XNAT to reload plugins...")

    # Wait for XNAT to be available. This is based on code in xnat4tests.start_xnat that waits for the initial
    # container startup.
    for attempts in range(xnat_config.connection_attempts):
        try:
            session = xnat4tests.connect(xnat_config)
        except (
            xnat.exceptions.XNATError,
            requests.ConnectionError,
            requests.ReadTimeout,
        ):
            if attempts == xnat_config.connection_attempts:
                raise RuntimeError("XNAT did not start in time")
            else:
                time.sleep(xnat_config.connection_attempt_sleep)
        else:
            break

    yield session

    # Allow the docker container to be re-used when the XNAT4TEST_KEEP_INSTANCE environment variable is set.
    # This is useful for fast local development, where we don't want to wait for the long Docker startup times
    # between every test run.
    if os.environ.get("XNAT4TEST_KEEP_INSTANCE", "False").lower() == "false":
        session.disconnect()
        xnat4tests.stop_xnat(xnat_config)
    else:
        for project in session.projects:
            for subject in project.subjects.values():
                try:
                    session.delete(
                        path=f"/data/projects/{project.id}/subjects/{subject.label}",
                        query={"removeFiles": "True"},
                    )
                except xnat.exceptions.XNATResponseError as e:
                    print(f"Could not delete subject {subject.label}: {e}")
        session.disconnect()
