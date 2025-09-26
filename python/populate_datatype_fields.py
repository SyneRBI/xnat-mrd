import xnat
from pathlib import Path
from datetime import datetime
from mrd_2_xnat import mrd_2_xnat
import os
import ismrmrd
import logging
from typing import Any, Tuple

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


def verify_project_exists(session: xnat.session, project_name: str) -> Any:
    """Verify project exist on XNAT server - disconnect if project does not exist"""
    try:
        xnat_project = session.projects[project_name]
        logger.info(f"Project {xnat_project} exists")
        return xnat_project
    except KeyError:
        logger.error(f"Project {project_name} not available on server")
        raise NameError(f"Project {project_name} not available on server.")

    logger.info(f"Project {xnat_project} exists")
    return xnat_project


def create_unique_subject(
    session: xnat.XNATSession, xnat_project: Any, subject_list: list
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

    # Create subject using REST API - PUT method as per XNAT documentation
    # PUT /data/projects/{PROJECT_ID}/subjects/{SUBJECT_ID}?label={SUBJECT_LABEL}
    session.put(
        f"/data/projects/{xnat_project.id}/subjects/{subject_id}",
        query={"label": subject_id},
    )

    # Get the created subject from the project
    # After creation, we can access it through the collection
    import time

    time.sleep(0.5)  # Brief pause to ensure creation is complete

    try:
        xnat_subject = xnat_project.subjects[subject_id]
    except KeyError:
        # If still not available, create a minimal subject proxy
        xnat_subject = type(
            "Subject",
            (),
            {
                "label": subject_id,
                "id": subject_id,
                "parent": xnat_project,
                "xnat_session": session,
                "experiments": type("Experiments", (), {"values": lambda: []})(),
            },
        )()

    subject_list.append(subject_id)
    logger.info(f"Created subject: {subject_id}")

    return xnat_subject, time_id


def add_exam(xnat_subject: Any, time_id: str, experiment_date: str) -> Any:
    """Add exam/experiment to the XNAT subject - disconnect if experiment already exists"""
    # Add exam
    experiment_id = "Exp-" + time_id
    experiment = xnat_subject.experiments[experiment_id]
    if experiment.exists():
        logger.error(f"Exam {experiment_id} already exists")
        raise NameError(f"Exam {experiment_id} already exists.")
    else:
        experiment.create(
            **{
                "experiments": "xnat:mrSessionData",
                "xnat:mrSessionData/date": experiment_date,
            }
        )
        logger.info(f"Created experiment: {experiment_id}")
    return experiment


def add_scan(experiment: Any, xnat_hdr: dict, scan_id: str, mrd_file: str) -> None:
    """Add scan to experiment. Create scan with the xnat_hdr info. Add MR_RAW resource
    to scan with mrd_file data.

    Args:
        experiment (Any): existing XNAT experiment
        xnat_hdr (dict): dict containing all the header info to populate in the data type mrd
        scan_id (str): custom str e.g. cart_cine_scan
        mrd_file (str): _description_
    """
    scan = experiment.scan(scan_id)
    if scan.exists():
        logger.warning(f"XNAT scan {scan_id} already exists")
    else:
        scan.create(**xnat_hdr)
        scan_resource = scan.resource("MR_RAW")
        scan_resource.put(
            (mrd_file,),
            format="HDF5",
            label="MR_RAW",
            content="RAW",
            **{"xsi:type": "xnat:mrScanData"},
        )
        logger.info(f"Successfully created scan {scan_id} and uploaded MRD file")


def main():
    xnat_server_address = "http://localhost"
    user = "admin"
    password = "admin"

    mrd_file_path = (
        Path(__file__).parent.parent
        / "test-data"
        / "ptb_resolutionphantom_fully_ismrmrd.h5"
    )
    mrd_file = str(mrd_file_path)

    logger.info(f"MRD file path: {mrd_file}")

    if not mrd_file_path.exists():
        raise FileNotFoundError(f"MRD file not found: {mrd_file}")

    experiment_date = "2022-05-04"
    scan_id = "cart_cine_scan"

    project_name = "mrd"
    subject_list = []

    # Use context manager for automatic connection cleanup
    with xnat.connect(xnat_server_address, user=user, password=password) as session:
        logger.info("Connected to XNAT server")

        xnat_project = verify_project_exists(session, project_name)
        xnat_subject, time_id = create_unique_subject(
            session, xnat_project, subject_list
        )
        experiment = add_exam(xnat_subject, time_id, experiment_date)
        # Load MRD header and convert to XNAT format
        dset = ismrmrd.Dataset(mrd_file, "dataset", create_if_needed=False)
        header = dset.read_xml_header()
        xnat_hdr = mrd_2_xnat(
            header, os.path.join(os.path.dirname(__file__), "ismrmrd.xsd")
        )
        add_scan(experiment, xnat_hdr, scan_id, mrd_file)


if __name__ == "__main__":
    main()
