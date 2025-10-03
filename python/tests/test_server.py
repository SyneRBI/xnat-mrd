import xnat


def test_mrdPlugin_installed(xnat_session, plugin_version):
    assert "mrdPlugin" in xnat_session.plugins
    mrd_plugin = xnat_session.plugins["mrdPlugin"]
    assert mrd_plugin.version == f"{plugin_version}-xpl"
    assert mrd_plugin.name == "XNAT 1.8 ISMRMRD plugin"


def test_mrd_data_fields(xnat_session):
    inspector = xnat.inspect.Inspect(xnat_session)
    assert "mrd:mrdScanData" in inspector.datatypes()
    inspector.datafields("mrdScanData")
