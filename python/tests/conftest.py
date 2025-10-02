import tempfile
from pathlib import Path
import subprocess
from xnat4tests import Config
import pytest
import xnat4tests
import time
import requests
import xnat


@pytest.fixture(scope="session")
def xnat_config():
    tmp_dir = Path(tempfile.mkdtemp())

    return Config(
        xnat_root_dir=tmp_dir,
        docker_image="xnat_mrd_xnat4tests",
        docker_container="xnat_mrd_xnat4tests",
        build_args={
            "xnat_version": "1.8.3",
            "xnat_cs_plugin_version": "3.2.0",
        },
    )


@pytest.fixture(scope="session")
def xnat_uri(xnat_config):
    plugin_path = Path("/data/xnat/home/plugins")
    source_path = Path(__file__).parents[2] / "build" / "libs" / "mrd-xpl.jar"

    if not source_path.exists():
        raise FileNotFoundError(f"Plugin JAR file not found at {source_path}")

    xnat4tests.start_xnat(xnat_config)
    try:
        subprocess.run(
            [
                "docker",
                "cp",
                str(source_path),
                f"xnat_mrd_xnat4tests:{(plugin_path / source_path.name).as_posix()}",
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
            xnat4tests.connect(xnat_config)
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

    yield xnat_config.xnat_uri
    xnat4tests.stop_xnat(xnat_config)
