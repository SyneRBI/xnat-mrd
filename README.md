# MRD

Xnat schema for ISMRMRD data format.

In order to create the plugin clone the repository:

```shell
git clone https://github.com/ckolbPTB/xnat-ismrmrd.git
cd xnat-ismrmrd
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

## Running pre-commit

**Prerequisites:** Java version 11 or greater is required to run pre-commit. If
you encounter issues, installing the latest Azul Zulu OpenJDK should resolve
them.

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
