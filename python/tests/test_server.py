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
        print(xnat_uri)
