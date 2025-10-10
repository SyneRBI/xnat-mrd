# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "xnat==0.7.2",
#     "ismrmrd==1.14.2",
#     "xmlschema==4.1.0",
# ]
# ///

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

import ismrmrd
import xnat

from mrd_2_xnat import mrd_2_xnat
import h5py
from fetch_datasets import get_multidata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("xnat_mrd_processing.log"),  # File output
    ],
)

logger = logging.getLogger(__name__)


def list_ismrmrd_datasets(mrd_file_path: Path) -> Tuple[list[str], bool]:
    with h5py.File(mrd_file_path, "r") as f:
        groups = list(f.keys())
        if len(groups) > 1:
            multidata = True
            return groups, multidata
        else:
            multidata = False
            return [groups[0]], multidata


def upload_mrd_data(
    xnat_session: xnat.XNATSession,
    mrd_file_path: Path,
    project_name: str,
    scan_id: str = "cart_cine_scan",
    experiment_date: str = "2022-05-04",
) -> None:
    

    if mrd_file_path.exists():
        logger.info(f"MRD file path: {mrd_file_path}")
    elif not mrd_file_path.exists():
        mrd_file_path = get_multidata()
    else:
        raise FileNotFoundError(f"MRD file not found: {mrd_file_path}")

    xnat_project = verify_project_exists(xnat_session, project_name)
    xnat_subject, time_id = create_unique_subject(xnat_session, xnat_project)
    experiment = add_exam(xnat_subject, time_id, experiment_date)

    dataset_names, multidata = list_ismrmrd_datasets(mrd_file_path)
    if multidata:
        dataset_name = dataset_names[1]
    else:
        dataset_name = dataset_names[0]
    # Load MRD header and convert to XNAT format
    with ismrmrd.Dataset(mrd_file_path, dataset_name, create_if_needed=False) as dset:
        header = dset.read_xml_header()
        xnat_hdr = mrd_2_xnat(header, Path(__file__).parent / "ismrmrd.xsd")

    add_scan(experiment, xnat_hdr, scan_id, mrd_file_path)


def verify_project_exists(session: xnat.XNATSession, project_name: str) -> Any:
    """Verify project exist on XNAT server - disconnect if project does not exist"""
    try:
        xnat_project = session.projects[project_name]
        logger.info(f"Project {xnat_project} exists")
        return xnat_project
    except KeyError:
        logger.error(f"Project {project_name} not available on server")
        raise NameError(f"Project {project_name} not available on server.")


def create_unique_subject(
    session: xnat.XNATSession, xnat_project: Any
) -> Tuple[Any, str]:
    """Create a unique subject that doesn't already exist"""
    time_id = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-3]
    subject_id = "Subj-" + time_id

    # Check if subject already exists
    existing_subjects = list(xnat_project.subjects.values())
    existing_subject_labels = [subj.label for subj in existing_subjects]

    if subject_id in existing_subject_labels:
        logger.error(f"Subject {subject_id} already exists")
        raise NameError(f"Subject {subject_id} already exists.")

    # Create subject using the proper XNAT object creation method
    # As per documentation: session.classes.SubjectData(parent=project, label='new_subject_label')
    xnat_subject = session.classes.SubjectData(parent=xnat_project, label=subject_id)

    logger.info(f"Created subject: {subject_id}")

    return xnat_subject, time_id


def add_exam(xnat_subject: Any, time_id: str, experiment_date: str) -> Any:
    """Add exam/experiment to the XNAT subject"""
    experiment_id = "Exp-" + time_id

    # Check if experiment already exists
    existing_experiments = list(xnat_subject.experiments.values())
    existing_experiment_labels = [exp.label for exp in existing_experiments]

    if experiment_id in existing_experiment_labels:
        logger.error(f"Exam {experiment_id} already exists")
        raise NameError(f"Exam {experiment_id} already exists.")

    # Create experiment using the proper XNAT object creation method
    # session.classes.MrSessionData(parent=subject, label='new_experiment_label')
    session = xnat_subject.xnat_session
    experiment = session.classes.MrSessionData(parent=xnat_subject, label=experiment_id)
    experiment.date = experiment_date

    logger.info(f"Created experiment: {experiment_id}")
    return experiment


def add_scan(
    experiment: Any, xnat_hdr: dict, scan_id: str, mrd_file_path: Path
) -> None:
    """Add scan to experiment. Create scan with the xnat_hdr info. Add MR_RAW resource
    to scan with mrd_file data.

    Args:
        experiment (Any): existing XNAT experiment
        xnat_hdr (dict): dict containing all the header info to populate in the data type mrd
        scan_id (str): custom str e.g. cart_cine_scan
        mrd_file_path (Path): Path of mrd_file containing MR raw data
    """
    # Check if scan already exists, otherwise create it with all header data
    if scan_id in experiment.scans:
        logger.error(f"XNAT scan {scan_id} already exists")
        raise NameError(f"XNAT scan {scan_id} already exists")

    # Create the scan with all MRD header data at once
    logger.info(f"Creating MRD scan {scan_id} with header data")

    # Use the xnat library's proper method for creating scans with data
    session = experiment.xnat_session
    scan_uri = f"{experiment.uri}/scans/{scan_id}"

    # Create the scan using PUT request with all header data as query parameters
    response = session.put(scan_uri, query=xnat_hdr)

    if response.ok:
        logger.info(f"Successfully created MRD scan: {scan_id}")
        # Refresh the experiment to see the new scan
        experiment.clearcache()

        # Get the created scan object
        scan = experiment.scans[scan_id]

    else:
        logger.error(f"Failed to create scan: {response.status_code} - {response.text}")
        raise Exception(f"Failed to create MRD scan: {response.status_code}")

    logger.info(f"Configured MRD scan: {scan_id}")

    # Create resource for MRD files - create the resource first, then upload
    scan_resource = scan.create_resource("MR_RAW")
    scan_resource.upload(mrd_file_path, mrd_file_path.name)
    logger.info(f"Successfully created scan {scan_id} and uploaded MRD file")


def main():
    xnat_server_address = "http://localhost"
    user = "admin"
    password = "admin"
    project_name = "mrd"

    mrd_file_path = (
        Path(__file__).parent.parent / "test-data" / "cart_t1_msense_integrated.mrd"
    )

    # Use context manager for automatic connection cleanup
    with xnat.connect(xnat_server_address, user=user, password=password) as session:
        logger.info("Connected to XNAT server")
        upload_mrd_data(session, mrd_file_path, project_name)


if __name__ == "__main__":
    main()
