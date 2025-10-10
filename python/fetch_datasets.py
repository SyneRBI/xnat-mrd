import pdb
import numpy.typing as npt
import pooch
import h5py
from pathlib import Path
import shutil

ZENODO = pooch.create(
    # Use the default cache folder for the operating system
    path=pooch.os_cache("python"),
    base_url="doi:10.5281/zenodo.15223816",
    registry=None,
)
ZENODO.load_registry_from_doi()


def _fetch_from_zenodo(image_name: str, local_dir: str = None) -> None:
    """Fetch mrd file from zenodo (if not already cached), and return as a 3D numpy array"""

    ZENODO.fetch(image_name)
    image_path = ZENODO.path / image_name
    print(image_path)
    # Optionally copy to local_dir
    if local_dir:
        local_path = Path(local_dir) / image_name
        shutil.copy(image_path, local_path)
        image_path = local_path
        
    return image_path


def get_multidata() -> None:
    """Fetch mrd file with multiple datasets"""
    return _fetch_from_zenodo("cart_t1_msense_integrated.mrd", local_dir=Path(__file__).parents[1] / "test-data")
