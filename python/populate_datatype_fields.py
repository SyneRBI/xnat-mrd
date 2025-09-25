from typing import Any
import xmlschema
import pyxnat
from pathlib import Path
from datetime import datetime
from mrd_2_xnat import mrd_2_xnat
import os
import ismrmrd


xnat_server_address = 'http://localhost'
user='admin'
password='admin'

mrd_file = Path(__file__).parent / 'test-data' / 'ptb_resolutionphantom_fully_ismrmrd.h5'

if not mrd_file.exists():
    raise FileNotFoundError(f"MRD file not found: {mrd_file}")

experiment_date = '2022-05-04'
scan_id = 'cart_cine_scan'

project_name = 'mrd'
subject_list = []


def connect_to_server(server, user, password) -> None:
    ''' Connect to XNAT server '''
    xnat_server = pyxnat.Interface(server=server, user=user, password=password)

def verify_project_exists(xnat_server, project_name) -> None:
    # Verify project exists
    xnat_project = xnat_server.select.project(project_name)
    if not xnat_project.exists():
        xnat_server.disconnect()
        raise NameError(f'Project {project_name} not available on server.')
    
    return xnat_project

def verify_subject_does_not_exist(xnat_server, xnat_project) -> None:
    # Verify subject does not exist
    time_id = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')[:-3]
    subject_id = 'Subj-' + time_id
    xnat_subject = xnat_project.subject(subject_id)
    if xnat_subject.exists():
        xnat_server.disconnect()
        raise NameError(f'Subject {subject_id} already exists.')
    else:
        subject_list.append(subject_id)
        
    return subject_id, time_id

def add_exam(xnat_server, xnat_subject, time_id) -> None:
    # Add exam
    experiment_id = 'Exp-' + time_id
    experiment = xnat_subject.experiment(experiment_id)
    if xnat_subject.exists():
        xnat_server.disconnect()
        raise NameError(f'Exam {experiment_id} already exists.')
    else:
        experiment.create(
            **{'experiments': 'xnat:mrSessionData',
            'xnat:mrSessionData/date': experiment_date})
    return experiment

def add_scan(experiment, xnat_hdr):
    # Add scan
    scan = experiment.scan(scan_id)
    if scan.exists():
        print(f'xnat scan {scan_id} already exists')
    else:
        scan.create(**xnat_hdr)
        scan_resource = scan.resource('MR_RAW')
        scan_resource.put((mrd_file,), format='HDF5', label='MR_RAW', content='RAW', **{'xsi:type': 'xnat:mrScanData'})



def main():
    xnat_server = connect_to_server(xnat_server_address, user, password)
    xnat_project = verify_project_exists(xnat_server, project_name)
    xnat_subject, time_id = verify_subject_does_not_exist(xnat_server, xnat_project)
    experiment = add_exam(xnat_server, xnat_subject, time_id)
    # Load MRD header and convert to XNAT format
    dset = ismrmrd.Dataset(mrd_file, 'dataset', create_if_needed=False)
    header = dset.read_xml_header()
    xnat_hdr = mrd_2_xnat(header, os.path.join(os.path.dirname(__file__), 'ismrmrd.xsd'))
    add_scan(experiment, xnat_hdr)
    xnat_server.disconnect()
    
    
    if __name__ == "__main__":
        main()








