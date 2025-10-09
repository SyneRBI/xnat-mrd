from pathlib import Path

import pytest
import xmlschema
import xnat

from populate_datatype_fields import upload_mrd_data


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


@pytest.mark.usefixtures("remove_test_data")
def test_mrdPlugin_installed(xnat_session, plugin_version):
    assert "mrdPlugin" in xnat_session.plugins
    mrd_plugin = xnat_session.plugins["mrdPlugin"]
    assert mrd_plugin.version == f"{plugin_version}-xpl"
    assert mrd_plugin.name == "XNAT 1.8 ISMRMRD plugin"


@pytest.mark.usefixtures("remove_test_data")
def test_mrd_data_fields(xnat_session, mrd_schema_fields):
    """Confirm that all data fields defined in the mrd schema file - mrd.xsd - are registered in xnat"""

    # get mrd data types from xnat session
    inspector = xnat.inspect.Inspect(xnat_session)
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
def test_mrd_data_upload(xnat_session, mrd_file_path, mrd_headers):
    project_id = "mrd"
    project = xnat_session.projects[project_id]
    upload_mrd_data(xnat_session, mrd_file_path, project_id)
    assert len(project.subjects) == 1
    subject = project.subjects[0]

    for header in mrd_headers:
        if header[0:16] == "mrd:mrdScanData/":
            xnat_header = header[16 : len(header)]
            if mrd_headers[header] != "":
                assert (
                    mrd_headers[header]
                    == subject.experiments[0].scans[0].data[xnat_header]
                )


@pytest.mark.usefixtures("ensure_mrd_project", "remove_test_data")
def test_mrd_data_modification(xnat_session, mrd_file_path):
    project_id = "mrd"
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
def test_mrd_data_deletion(xnat_session, mrd_file_path):
    project_id = "mrd"
    project = xnat_session.projects[project_id]
    upload_mrd_data(xnat_session, mrd_file_path, project_id)
    experiments = project.subjects[0].experiments
    assert len(experiments) == 1
    experiments[0].delete()
    assert len(experiments) == 0
