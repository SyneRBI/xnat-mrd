import xnat


def test_mrdPlugin_installed(xnat_uri, xnat_config):
    with xnat.connect(
        server=xnat_uri,
        user=xnat_config.xnat_user,
        password=xnat_config.xnat_password,
    ) as session:
        assert "mrdPlugin" in session.plugins
        session.plugins.data[
            "mrdPlugin"
        ].version  # unknown vars() .name XNAT 1.8 ISMRMRD plugin

        inspector = xnat.inspect.Inspect(session)
        assert "mrd:mrdScanData" in inspector.datatypes()
        inspector.datafields("mrdScanData")
