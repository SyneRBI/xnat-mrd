import xmlschema

def mrd_2_xnat(ismrmrd_header, xml_scheme_filename):
    xml_schema = xmlschema.XMLSchema(xml_scheme_filename)

    assert xml_schema.is_valid(ismrmrd_header), 'Raw data file is not a valid ismrmrd file'

    ismrmrd_dict = xml_schema.to_dict(ismrmrd_header)

    # Get main parameter groups
    xnat_mrd_list = []
    for ckeys in ismrmrd_dict.keys():
        if '@' not in ckeys and 'userParameter' not in ckeys:
            xnat_mrd_list.append([ckeys, ])

    def get_dict_values(dict, key_list):
        if len(key_list) == 0:
            return None
        else:
            cval = dict[key_list[0]]
            for ind in range(1, len(key_list)):
                cval = cval[key_list[ind]]
            return (cval)

    # Go through all parameters and create list of parameter names
    for knd in range(5):
        flag_finished = True
        xnat_mrd_list_new = []
        for ckey_list in xnat_mrd_list:
            cvals = get_dict_values(ismrmrd_dict, ckey_list)
            if not isinstance(cvals, list):
                if isinstance(cvals, dict):
                    flag_finished = False
                    for ckey in cvals.keys():
                        xnat_mrd_list_new.append(ckey_list + [ckey, ])
                else:
                    xnat_mrd_list_new.append(ckey_list)
            else:
                for jnd in range(len(cvals)):
                    if isinstance(cvals[jnd], dict):
                        flag_finished = False
                        for ckey in cvals[jnd].keys():
                            xnat_mrd_list_new.append(ckey_list + [jnd, ckey, ])
                    else:
                        xnat_mrd_list_new.append(ckey_list + [jnd, ])

        if flag_finished == True:
            break
        xnat_mrd_list = xnat_mrd_list_new

    # Create dictionary with parameter names and their values
    xnat_mrd_dict = {}
    xnat_mrd_dict['scans'] = 'mrd:mrdScanData'

    # First deal with special cases
    # coilLabel
    coil_idx = [idx for idx in range(len(xnat_mrd_list)) if xnat_mrd_list[idx][0] == 'acquisitionSystemInformation'
                and xnat_mrd_list[idx][1] == 'coilLabel' and xnat_mrd_list[idx][3] == 'coilName']
    num_coils = len(coil_idx)

    coil_label_strg = ''
    for ind in range(num_coils):
        coil_label_strg += (get_dict_values(ismrmrd_dict, xnat_mrd_list[coil_idx[ind]]) + ' ')

    if len(coil_label_strg) > 255:
        coil_label_strg = coil_label_strg[:243] + ' (truncated)'

    xnat_mrd_dict['mrd:mrdScanData/acquisitionSystemInformation/coilLabelList'] = coil_label_strg
    xnat_mrd_list = [elem for elem in xnat_mrd_list if
                     elem[0] != 'acquisitionSystemInformation' and elem[1] != 'coilLabel']

    # waveformInformation
    waveform_idx = [idx for idx in range(len(xnat_mrd_list)) if xnat_mrd_list[idx][0] == 'waveformInformation'
                    and xnat_mrd_list[idx][2] == 'waveformType']
    num_waveforms = len(waveform_idx)

    waveform_strg = ''
    for ind in range(num_waveforms):
        waveform_strg += (get_dict_values(ismrmrd_dict, xnat_mrd_list[waveform_idx[ind]]) + ' ')

    if len(waveform_strg) > 255:
        waveform_strg = waveform_strg[:243] + ' (truncated)'

    xnat_mrd_dict['mrd:mrdScanData/waveformInformationList'] = waveform_strg
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[0] != 'waveformInformation']

    # encoding
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[0] != 'encoding' or elem[1] == 0]
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[:3] != ['encoding', 0, 'trajectoryDescription']]
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[:5] != ['encoding', 0, 'multiband', 'spacing', 'dZ']]
    xnat_mrd_list = [elem for elem in xnat_mrd_list if
                     elem[:6] != ['encoding', 0, 'paralellImaging', 'multiband', 'spacing', 'dZ']]

    # sequenceParameters
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[:2] != ['sequenceParameters', 'diffusion']]

    single_entries = ['TR', 'TE', 'flipAngle_deg', 'echo_spacing', 'TI']
    for ind in range(len(single_entries)):
        xnat_mrd_list = [elem for elem in xnat_mrd_list if
                         elem[:2] != ['sequenceParameters', single_entries[ind]] or elem[2] == 0]

    # measurementInformation
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[:2] != ['measurementInformation', 'measurementDependency']
                     or elem[2] == 0]
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[:2] != ['measurementInformation', 'referencedImageSequence',
                                                                    'referencedSOPInstanceUID'] or elem[3] == 0]

    for ind in range(len(xnat_mrd_list)):
        ckey = 'mrd:mrdScanData'
        for jnd in range(len(xnat_mrd_list[ind])):
            if isinstance(xnat_mrd_list[ind][jnd], str):
                ckey += ('/' + xnat_mrd_list[ind][jnd])
            # This field seems to be too long for xnat
            if 'parallelImaging/accelerationFactor/kspace_encoding_step' in ckey:
                ckey = ckey.replace('kspace_encoding_step', 'kspace_enc_step')
        xnat_mrd_dict[ckey] = get_dict_values(ismrmrd_dict, xnat_mrd_list[ind])


    xnat_mrd_dict['mrd:mrdScanData/acquisitionSystemInformation/coilLabelList'] = 'TEMP'

    return (xnat_mrd_dict)