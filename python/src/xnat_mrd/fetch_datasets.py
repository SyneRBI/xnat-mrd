import pooch
from pathlib import Path


def _set_up_zenodo_doi(base_url: str):
    ZENODO = pooch.create(
        path=Path(__file__).parents[3] / "test-data",
        base_url=base_url,
        registry=None,
    )
    ZENODO.load_registry_from_doi()
    return ZENODO


def _fetch_from_zenodo(base_url: str, image_name: str) -> Path:
    """Fetch mrd file from zenodo (if not already cached), and return the file path where
    data is downloaded"""

    ZENODO = _set_up_zenodo_doi(base_url)

    image_path = Path(ZENODO.fetch(image_name))

    return image_path


def get_multidata() -> Path:
    """Fetch mrd file with multiple datasets"""
    return _fetch_from_zenodo(
        "doi:10.5281/zenodo.15223816",
        "cart_t1_msense_integrated.mrd",
    )


def get_singledata() -> Path:
    """Fetch mrd file with a single dataset"""
    return _fetch_from_zenodo(
        "doi.org/10.5281/zenodo.2633785",
        "cart_t1_msense_integrated.mrd",
    )
