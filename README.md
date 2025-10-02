# MRD

Xnat schema for ISMRMRD data format.

In order to create the plugin clone the repository:

```shell
git clone https://github.com/SyneRBI/xnat-mrd.git
cd xnat-mrd
```

and then use gradlew to build the plugin

```shell
./gradlew init
./gradlew clean xnatPluginJar
```

If you want to rebuild the plugin after making some changes to the code it is a
good idea to ensure there are no more running gradlew clients:

```shell
./gradlew --stop
```

before building again with

```shell
./gradlew clean xnatPluginJar
```

## Creating a new release

Create a new tag in the form `vX.Y.Z` and push it to the repository e.g.

```bash
git tag v1.0.0
git push origin v1.0.0
```

This will trigger a github actions workflow creating:

- a new Github release with `.jar` attached
- a new package on
  [Github packages](https://github.com/orgs/SyneRBI/packages?repo_name=xnat-mrd)

For information about how to use this package as a dependency, see the github
docs for
[maven](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-apache-maven-registry#installing-a-package)
or
[gradle](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-gradle-registry#using-a-published-package).

## Running pre-commit

To set up and run pre-commit:

```shell
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the pre-commit hooks
pre-commit install

# Run pre-commit on all files (optional)
pre-commit run --all-files
```

If you want to disable the pre-commit hooks:

```shell

pre-commit uninstall
```

## Requirements

If using uv then you can take advantage of the inline requirements at the top of
populate_datatype_fields.py by running:

```shell

uv run populate_datatype_fields.py
```

However, the `requirements.txt` file is still available if running the code as
normal with python.
