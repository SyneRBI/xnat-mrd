from pathlib import Path

import pytest
import xmlschema
import xnat
import subprocess

from xnat_mrd.populate_datatype_fields import upload_mrd_data, read_mrd_header


@pytest.fixture
def mrd_schema_fields():
    """Read data fields from the plugin's mrd schema file - mrd.xsd - and convert to xnat style."""

    mrd_schema_file = (
        Path(__file__).parents[2]
        / "src"
        / "main"
        / "resources"
        / "schemas"
        / "mrd"
        / "mrd.xsd"
    )
    mrd_schema = xmlschema.XMLSchema(mrd_schema_file, validation="skip")

    # we only want the 'leaves' of the xml tree - not intermediate elements
    components = [
        component
        for component in mrd_schema.iter_components(
            xsd_classes=(xmlschema.validators.elements.XsdElement,)
        )
    ]
    filtered_components = []
    for component in components:
        if isinstance(component.type, xmlschema.validators.simple_types.XsdSimpleType):
            filtered_components.append(component)
        elif (component.type.name is not None) and (
            component.type.name.endswith("anyType")
        ):
            filtered_components.append(component)

    # get full path to each component in xnat style (i.e. _ separated + uppercase)
    component_paths = []
    for component in filtered_components:
        path = component.get_path().replace("{http://ptb.de/mrd}", "")
        path = f"mrdScanData/{path.replace('/', '_').upper()}"

        # paths over 75 characters in xnat seem to be truncated
        if len(path) > 75:
            path = path[:75]

        component_paths.append(path)

    return component_paths


def verify_headers_match(mrd_file_path, scan, dataset_name):
    """Check headers from a given mrd file match those in an xnat scan object"""

    mrd_headers = read_mrd_header(mrd_file_path, dataset_name)
    for mrd_key, mrd_value in mrd_headers.items():
        if (mrd_key[0:16] == "mrd:mrdScanData/") and (mrd_value != ""):
            xnat_header = mrd_key[16:]
            assert mrd_value == scan.data[xnat_header]


@pytest.mark.usefixtures("remove_test_data")
def test_mrdPlugin_installed(xnat_connection, plugin_version):
    assert "mrdPlugin" in xnat_connection.session.plugins
    mrd_plugin = xnat_connection.session.plugins["mrdPlugin"]
    assert mrd_plugin.version == f"{plugin_version}-xpl"
    assert mrd_plugin.name == "XNAT 1.8 ISMRMRD plugin"


@pytest.mark.filterwarnings("ignore:Import of namespace")
@pytest.mark.usefixtures("remove_test_data")
def test_mrd_data_fields(xnat_connection, mrd_schema_fields):
    """Confirm that all data fields defined in the mrd schema file - mrd.xsd - are registered in xnat"""

    # get mrd data types from xnat session
    inspector = xnat.inspect.Inspect(xnat_connection.session)
    assert "mrd:mrdScanData" in inspector.datatypes()
    xnat_data_fields = inspector.datafields("mrdScanData")

    # get expected data types from plugin's mrd schema (+ added types relating to xnat project / session info)
    additional_xnat_fields = [
        "mrdScanData/SESSION_LABEL",
        "mrdScanData/SUBJECT_ID",
        "mrdScanData/PROJECT",
        "mrdScanData/ID",
    ]
    expected_data_fields = mrd_schema_fields + additional_xnat_fields

    assert sorted(xnat_data_fields) == sorted(expected_data_fields)


@pytest.mark.usefixtures("ensure_mrd_project", "remove_test_data")
def test_mrd_data_upload(xnat_connection, mrd_file_path):
    project_id = "mrd"
    xnat_session = xnat_connection.session
    project = xnat_session.projects[project_id]
    upload_mrd_data(xnat_session, mrd_file_path, project_id)
    assert len(project.subjects) == 1

    subject = project.subjects[0]
    verify_headers_match(mrd_file_path, subject.experiments[0].scans[0], "dataset")


@pytest.mark.usefixtures("ensure_mrd_project", "remove_test_data")
def test_mrd_multidata_upload(xnat_connection, mrd_file_multidata_path):
    project_id = "mrd"
    xnat_session = xnat_connection.session
    project = xnat_session.projects[project_id]
    upload_mrd_data(xnat_session, mrd_file_multidata_path, project_id)
    assert len(project.subjects) == 1
    subject = project.subjects[0]
    verify_headers_match(
        mrd_file_multidata_path, subject.experiments[0].scans[0], "dataset_2"
    )


@pytest.mark.usefixtures("ensure_mrd_project", "remove_test_data")
def test_mrd_data_modification(xnat_connection, mrd_file_path):
    project_id = "mrd"
    xnat_session = xnat_connection.session
    project = xnat_session.projects[project_id]
    upload_mrd_data(xnat_session, mrd_file_path, project_id)
    subject = project.subjects[0]

    xnat_header = "encoding/encodedSpace/matrixSize/x"
    all_headers = subject.experiments[0].scans[0].data
    assert all_headers[xnat_header] == 512
    all_headers[xnat_header] = 256
    assert all_headers[xnat_header] == 256
    assert xnat_header in all_headers.keys()
    new_header = "encoding/x"
    all_headers[new_header] = all_headers.pop(xnat_header)
    assert new_header in all_headers.keys()
    assert xnat_header not in all_headers.keys()


@pytest.mark.usefixtures("ensure_mrd_project", "remove_test_data")
def test_mrd_data_deletion(xnat_connection, mrd_file_path):
    project_id = "mrd"
    xnat_session = xnat_connection.session
    project = xnat_session.projects[project_id]
    upload_mrd_data(xnat_session, mrd_file_path, project_id)

    experiments = project.subjects[0].experiments
    assert len(experiments) == 1
    experiments[0].delete()
    assert len(experiments) == 0


@pytest.mark.slow
@pytest.mark.usefixtures("ensure_mrd_project", "remove_test_data")
def test_plugin_update(
    xnat_connection, plugin_dir, jar_path, plugin_version, mrd_file_path
):
    """Test that updating the plugin (i.e. copying a new mrd-VERSION-xpl.jar into xnat + restarting) doesn't
    affect previously uploaded data."""

    xnat_session = xnat_connection.session
    project = xnat_session.projects["mrd"]
    upload_mrd_data(xnat_session, mrd_file_path, "mrd")

    # Check plugin version and data is as expected
    assert xnat_session.plugins["mrdPlugin"].version == f"{plugin_version}-xpl"
    scan = project.subjects[0].experiments[0].scans[0]
    verify_headers_match(mrd_file_path, scan, "dataset")

    # Re-name the plugin jar to another version (to mimic overwriting the existing plugin with a new version)
    current_plugin_path = plugin_dir / jar_path.name
    new_plugin_path = plugin_dir / "mrd-0.0.1-xpl.jar"

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "xnat_mrd_xnat4tests",
                "mv",
                current_plugin_path.as_posix(),
                new_plugin_path.as_posix(),
            ],
            check=True,
        )

        xnat_connection.restart_xnat()
        xnat_session = xnat_connection.session
        project = xnat_session.projects["mrd"]

        # Check no data has been changed after plugin update
        assert xnat_session.plugins["mrdPlugin"].version == "0.0.1-xpl"
        scan = project.subjects[0].experiments[0].scans[0]
        verify_headers_match(mrd_file_path, scan, "dataset")

    finally:
        # re-set plugin to original state
        subprocess.run(
            [
                "docker",
                "exec",
                "xnat_mrd_xnat4tests",
                "mv",
                new_plugin_path.as_posix(),
                current_plugin_path.as_posix(),
            ],
            check=True,
        )
        xnat_connection.restart_xnat()
