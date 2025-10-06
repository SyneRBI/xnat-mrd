import xnat
from pathlib import Path
import xmlschema
import pytest


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
