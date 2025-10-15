import pooch
from pathlib import Path
import shutil
from typing import Optional

ZENODO = pooch.create(
    # Use the default cache folder for the operating system
    path=pooch.os_cache("python"),
    base_url="doi:10.5281/zenodo.15223816",
    registry=None,
)
ZENODO.load_registry_from_doi()


def _fetch_from_zenodo(image_name: str, local_dir: Optional[Path] = None) -> Path:
    """Fetch mrd file from zenodo (if not already cached), and return the file path where
    data is downloaded"""

    image_path = Path(ZENODO.fetch(image_name))
    # Optionally copy to local_dir
    if local_dir:
        local_path = Path(local_dir) / image_name
        shutil.copy(image_path, local_path)
        image_path = local_path

    return image_path


def get_multidata() -> Path:
    """Fetch mrd file with multiple datasets"""
    return _fetch_from_zenodo(
        "cart_t1_msense_integrated.mrd",
        local_dir=Path(__file__).parents[3] / "test-data",
    )
