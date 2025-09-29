import tempfile
from pathlib import Path
from xnat4tests import Config
import pytest
import xnat4tests


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
    xnat4tests.start_xnat(xnat_config)
    yield xnat_config.xnat_uri
    xnat4tests.stop_xnat(xnat_config)
