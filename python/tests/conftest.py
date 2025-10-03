from pathlib import Path
import subprocess
import pytest
import xnat4tests
import time
import requests
import xnat
import re


@pytest.fixture(scope="session")
def xnat_config(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("data")

    return xnat4tests.Config(
        xnat_root_dir=tmp_dir,
        docker_image="xnat_mrd_xnat4tests",
        docker_container="xnat_mrd_xnat4tests",
        build_args={
            "xnat_version": "1.8.3",
            "xnat_cs_plugin_version": "3.2.0",
        },
    )


@pytest.fixture(scope="session")
def jar_path():
    jar_dir = Path(__file__).parents[2] / "build" / "libs"
    return list(jar_dir.glob("mrd-*xpl.jar"))[0]


@pytest.fixture(scope="session")
def plugin_version(jar_path):
    version = re.search("mrd-(.+?)-xpl.jar", jar_path.name).group(1)

    if version is None:
        raise NameError(
            "Jar name contains no version - did you set the JAR_VERSION env variable when you ran gradlew?"
        )
    else:
        return version


@pytest.fixture(scope="session")
def xnat_session(xnat_config, jar_path):
    plugin_path = Path("/data/xnat/home/plugins")
    if not jar_path.exists():
        raise FileNotFoundError(f"Plugin JAR file not found at {jar_path}")

    xnat4tests.start_xnat(xnat_config)

    # Install Mrd plugin by copying the jar into the container
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

    session.disconnect()
    xnat4tests.stop_xnat(xnat_config)
