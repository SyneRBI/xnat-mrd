import tempfile
from pathlib import Path
import subprocess
from xnat4tests import Config
import os
import pytest
import xnat4tests


@pytest.fixture(scope="session")
def xnat_config():
    tmp_dir = Path(tempfile.mkdtemp())
    config = Config.load("default")
    print(config)
    config.xnat_root_dir = tmp_dir
    config.build_args = (
        {
            "xnat_version": "1.8.3",
            "xnat_cs_plugin_version": "3.2.0",
        },
    )
    config.xnat_mnt_dirs = [
        "home/logs",
        "home/work",
        "build",
        "archive",
        "prearchive",
        "home/plugins",
    ]

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
    yield xnat_config.xnat_uri
    xnat4tests.stop_xnat(xnat_config)
