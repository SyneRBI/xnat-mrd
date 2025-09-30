import xnat


def test_spin_up_server(xnat_uri):
    with xnat.connect(
        server=xnat_uri,
        user="admin",
        password="admin",
    ) as session:
        print(session.plugins)
        print(xnat_uri)
