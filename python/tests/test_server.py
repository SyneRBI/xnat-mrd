import pdb
import time
from pathlib import Path

import ismrmrd
import pytest
import xmlschema
import xnat

from mrd_2_xnat import mrd_2_xnat
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


@pytest.fixture
def mrd_data():
    """Provides the mrd_data filepath"""

    mrd_data = (
        Path(__file__).parents[2]
        / "test-data"
        / "ptb_resolutionphantom_fully_ismrmrd.h5"
    )

    return mrd_data


@pytest.fixture
def mrd_headers():
    mrd_file_path = (
        Path(__file__).parents[2]
        / "test-data"
        / "ptb_resolutionphantom_fully_ismrmrd.h5"
    )
    with ismrmrd.Dataset(mrd_file_path, "dataset", create_if_needed=False) as dset:
        header = dset.read_xml_header()
        xnat_hdr = mrd_2_xnat(header, Path(__file__).parents[1] / "ismrmrd.xsd")

    return xnat_hdr


def test_mrdPlugin_installed(xnat_session, plugin_version):
    assert "mrdPlugin" in xnat_session.plugins
    mrd_plugin = xnat_session.plugins["mrdPlugin"]
    assert mrd_plugin.version == f"{plugin_version}-xpl"
    assert mrd_plugin.name == "XNAT 1.8 ISMRMRD plugin"


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


def test_mrd_data_upload(xnat_session, mrd_data, mrd_headers):
    project_id = "mrd"
    project_name = "MRD Project"
    project_description = "MRD test project"

    # Create the project using the XNAT REST API
    uri = f"/data/projects/{project_id}"
    payload = {
        "name": project_name,
        "description": project_description,
        "id": project_id,
    }
    response = xnat_session.put(uri, query=payload)
    assert response.ok, (
        f"Failed to create project: {response.status_code} {response.text}"
    )

    # Retry until project appears (max 5 seconds)
    for _ in range(10):
        try:
            project = xnat_session.projects[project_id]
            break
        except KeyError:
            time.sleep(0.5)
    else:
        raise RuntimeError(f"Project '{project_id}' not found after creation.")

    upload_mrd_data(xnat_session, mrd_data, project_name)
    assert len(project.subjects) == 1
    subject = project.subjects[0]
    subject.experiments[0].scans[0].data
    pdb.set_trace()
    [header for header in mrd_headers]

    missing_parameters = [
        "waveformInformationList",
        "alias",
        "PI/firstname",
        "PI/lastname",
        "meta/last_modified",
        "meta/insert_date",
        "meta/insert_user",
    ]
    for header in mrd_headers:
        if header[0:16] == "mrd:mrdScanData/":
            if header[16 : len(header)] not in missing_parameters:
                assert (
                    mrd_headers[header]
                    == subject.experiments[0].scans[0].data[header[16 : len(header)]]
                )
