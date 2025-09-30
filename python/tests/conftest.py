import tempfile
from pathlib import Path
import subprocess
from xnat4tests import Config
import os
import pytest
import xnat4tests
import time
import requests


@pytest.fixture(scope="session")
def xnat_config():
    tmp_dir = Path(tempfile.mkdtemp())

    return Config(
        xnat_root_dir=tmp_dir,
        xnat_port=9999,
        docker_image="xnat_mrd_xnat4tests",
        docker_container="xnat_mrd_xnat4tests",
        build_args={
            "xnat_version": "1.8.3",
            "xnat_cs_plugin_version": "3.2.0",
        },
    )


@pytest.fixture(scope="session")
def xnat_uri(xnat_config):
    print(os.getcwd())
    plugin_path = Path("/data/xnat/home/plugins")
    source_path = Path(__file__).parent / "mrd-xpl.jar"
    if not source_path.exists():
        raise FileNotFoundError(f"Plugin JAR file not found at {source_path}")
    xnat4tests.start_xnat(xnat_config)
    subprocess.call(
        f"docker cp {source_path} xnat_mrd_xnat4tests:{plugin_path / 'mrd-xpl.jar'}",
        shell=True,
    )
    xnat4tests.restart_xnat(xnat_config)
    subprocess.call(
        "docker exec xnat_mrd_xnat4tests ls -la /data/xnat/home/plugins/",
        shell=True,
    )

    # Wait for XNAT to be available
    xnat_url = xnat_config.xnat_uri
    for _ in range(60):  # Wait up to 60 seconds
        try:
            r = requests.get(xnat_url)
            if r.status_code == 200:
                print("XNAT is up!")
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        raise RuntimeError("XNAT did not start in time")
    yield xnat_config.xnat_uri
    xnat4tests.stop_xnat(xnat_config)
