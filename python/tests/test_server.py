import xnat


def test_mrdPlugin_installed(xnat_uri):
    with xnat.connect(
        server=xnat_uri,
        user="admin",
        password="admin",
    ) as session:
        print(session.plugins)
        plugin = [plugin for plugin in session.plugins if plugin == "mrdPlugin"]
        assert plugin[0] == "mrdPlugin"
        session.plugins.data[
            "mrdPlugin"
        ].version  # unknown vars() .name XNAT 1.8 ISMRMRD plugin
        print(xnat_uri)
        inspector = xnat.inspect.Inspect(session)
        mrddatatype = [
            datatype
            for datatype in inspector.datatypes()
            if datatype == "mrd:mrdScanData"
        ]
        assert mrddatatype[0] == "mrd:mrdScanData"
        inspector.datafields("mrdScanData")
