import sys, os
from glob import glob
import datetime
import dateutil.parser as parser
import xlrd
import pandas
import numpy as np
from collections import defaultdict
import logging
from collections import defaultdict

def update_existing(dict, tmpdict):
    lblid = tmpdict.keys()[0]
    dates,dob,bacs = tmpdict.values()[0]
    if not dict[lblid]['dob'] == dob:
        print 'dob conflict! new:',dob,  dict[lblid]['dob']
        return
    if not dict[lblid]['bacs'] == bacs:
        print 'bacs conflict new:', bacs, dict[lblid]['bacs']
        return
    #print dates, dict[lblid]['dates']
    dates = [dates] + dict[lblid]['dates']
    
    dates.sort()
    dict[lblid]['dates'] = dates
    

def addnew(dict, tmpdict):
    lblid = tmpdict.keys()[0]
    dates,dob,bacs = tmpdict.values()[0]
    dict.update({lblid:{'dob':dob, 'dates':[dates], 'bacs':bacs}})
    

def update_dict(dict, tmpdict):
    if dict.has_key(tmpdict.keys()[0]):
        update_existing(dict, tmpdict)
    else:
        addnew(dict, tmpdict)

def get_header_map(inrow):
    headerd = {}
    for val, item in enumerate(inrow):
        headerd.update({item.value:val})
    return headerd


def dataframe_from_excel(infile, sheetname='Sheet1'):
    """ uses pandas tool to get a dataframe from
    an existing excel file"""
    excel_data = pandas.ExcelFile(infile)
    parsed = excel_data.parse(sheetname)
    return parsed


def get_headermap(dataframe):
    """ get the name: column key mapping dict
    from a Pandas DataFrame object"""
    hdrd = {}
    for val, hdr in enumerate(dataframe.columns):
        hdrd[hdr] = val
    return hdrd


def headermap_from_xlsfile(infile, sheet_index=0):
    """ opens an excel file and returns headermap
    mapping header string to column number
    by default uses first sheet, but can override with sheet_index
    """
    wb = xlrd.open_workbook(infile)
    sheet = wb.sheet_by_index(sheet_index)
    header_map = get_header_map(sheet.row_slice(0))
    return header_map

def simple_header(header_map):
    """ take the complex header map and create a simpler map
    remove redundant Patient Info::, whitespace, """
    outd = {}
    for item in header_map:
        newname = item.replace('Patient Info::','').replace(' ','')
        outd[newname] = item
    return outd
        
        
def bac_to_lbl(dataframe, header_map):
    """ Looks at dataframe and uses header_map to
    create a BAC -> LBL mapping"""
    shdrmap = simple_header(header_map)# create a simpler header map
    outd =  dict(zip(dataframe[shdrmap['BACID']],
                     dataframe[shdrmap['LBNLID']]))
    outd.pop(np.nan)# remove a non-mapping 
    return outd

def lbl_to_bac(dataframe, header_map):
    """ Looks at dataframe and uses header_map to
    create a BAC -> LBL mapping"""
    shdrmap = simple_header(header_map)# create a simpler header map
    outd =  dict(zip(dataframe[shdrmap['LBNLID']],
                    dataframe[shdrmap['BACID']]))
    #outd.pop('na')
    return outd


def is_bad_protocol(protocol):
    """ checks the generated protocol tuple generated
    for database entry errors

    strings should be : 
        'PET-FDG-Ecat', 'MRI'
    bad entry results in 'nan-nan-nan'
    returns True if it is a bad protocol
    False otherwise
    """
    if not all([isinstance(x, unicode) for x in protocol]):
        return True
    return False
    
def log_dberror(val, jnk):
    """ logs a found error in output from database
    includes
    val (line with error)
    jnk : current content of line
    """
    logging.error('bad protocol, database error, line %d'%val)
    logging.error(str(jnk.values))

def log_dbrepo_error(lblid, error, eventtype):
    """ logs an error found trying to match database report to 
    events found in repository"""
    logging.error(' '.join(['db repo mistmatch',eventtype,lblid,error]))


def make_dicts(dataframe):
    """ create unique sample dictionaries from dataframe

    Notes
    =====

    occaisionally someone will input a field improperly
    resulting in a protocol-type of nan-nan-nan
    this should generate an error log that can be returned to the
    database users so they can fix this entry

    """
    ##!! HACK, need to update to add a good log output dir
    now = datetime.datetime.now().strftime('%Y-%b-%d-%H')
    logging.basicConfig(filename='database_check_errors-%s.log'%now, filemode='w', level=logging.DEBUG)
    logging.info('Started sample_dicts: check database')
    shdr = simple_header(get_headermap(dataframe))
    mytypes = []
    for val, items in enumerate(zip(dataframe[shdr['SampleType']],
                                    dataframe[shdr['Radiotracer']],
                                    dataframe[shdr['PETScanner']])):
        if is_bad_protocol(items):
            # print to error log
            print 'BAD'
            jnk = dataframe.take([val], axis=0)
            log_dberror(val, jnk)
            mytypes.append('NA')
            continue
        #ritems = [str(x) for x in items]
        typestr = '-'.join([x.upper() for x in items]).replace('-N/A','')
        typestr = typestr.strip('\n')
        
        if 'MRI-' in typestr:
            print typestr
            jnk = dataframe.take([val], axis=0)
            log_dberror(val, jnk)
            mytypes.append('NA')
            continue
        mytypes.append(typestr)
    unique_types = set(mytypes)
    return mytypes, unique_types


def make_lbl_bac_dict(infile):
    lbl_2_bac = {}
    bac_2_lbl = {}
    wb = xlrd.open_workbook(infile)
    sheet = wb.sheet_by_index(0)
    nrows = sheet.nrows
    header_map = get_header_map(sheet.row_slice(0))
    for rown in range(1,nrows):
        tmprow = sheet.row_slice(rown)
        lblid = tmprow[header_map['LBNL ID']].value.upper().strip('\n')
        bacid = tmprow[header_map['Patient Info::BAC ID']].value.upper().replace('\n','')

        if len(lblid) < 2 or len(bacid) < 2:
            print lblid, bacid
            continue
        if not lbl_2_bac.has_key(lblid):
            lbl_2_bac.update({lblid:bacid})
        if not bac_2_lbl.has_key(bacid):
            bac_2_lbl.update({bacid:lblid})
    return lbl_2_bac, bac_2_lbl


def good_header_map(header_map):
    """
    given the expected header_map, compares to new header_map to see if anything has changed
    """
    orig_header_map =\
    {u'Age at Scan': 5,
     u'CTDI': 13,
     u'Dementia Type': 15,
     u'Diagnosis': 14,
     u'FAIL Reason': 18,
     u'Injected Dose': 12,
     u'Notes': 16,
     u'PET Scanner': 11,
     u'Patient Info::BAC ID': 1,
     u'Patient Info::Date of Birth': 3,
     u'Patient Info::LBNL ID': 0,
     u'Patient Info::Other ID': 2,
     u'Patient Info::Patient Notes': 4,
     u'Protocols::Protocol Name': 8,
     u'QC': 17,
     u'Radiotracer': 10,
     u'Sample Date': 6,
     u'Sample Protocol': 7,
     u'Sample Type': 9}

    baseline = defaultdict(int, orig_header_map)
    if not baseline == header_map:
        return False
    return True


def rows_for_types(alltypes, types):
    """ Given a specific set of types, return 
        a dict of type->indicies such that the 
        indicies of the alltypes match type"""
    outd = {}
    alltypes = np.array(alltypes)
    allind = np.indices(alltypes.shape).squeeze()
    for item in types:
        outd[item] = allind[alltypes == item]
    return outd
        

def generate_sampletype_dict(dataframe, typedict, sampletype):
    """ given the dataframe and the indicies of a specific
    sample type (stypedict['PET-RAC-ECAT'] = [3,5,...]), 
    create a new dictionary holding
    LBLID [0], BACID [1], Age at Scan[5], DOB[3], Sample Date[6], 
    QC[-2]"""
    sampledict = {}
    for val in typedict[sampletype]:
        values = dataframe.ix[val]
        lblid, bacid, age, dob, date,qc = values[0], values[1], values[5], values[3], values[6],values[-2]
        lblid = lblid.strip('\n')#db allows users to enter newline chars
        sampledict.setdefault(lblid, []).append([bacid, age, dob, date,qc])
    return sampledict


def check_dir(indir, isglob=False):
    """ check for exsistence of directory indir
    if isglob == True, tries to match pattern
    """
    if not isglob:
        return os.path.isdir(indir)
    else:
        result = glob(indir)
        if len(result) == 1:
            return True
        else:
            print len(result), 'results for ', indir
            return False
            

def check_dict_repo(dict, type):
    """ given a sample dict of type type ('MRI') 
    lblid->[[bacid, age, dob, date,qc],
    [bacid, age, dob, date,qc]], match to info in repository (arda)
    """
    arda = '/home/jagust/arda/lblid'
    for lblid, events in sorted(dict.items()):
        subdir = os.path.join(arda,lblid)
        if not check_dir(subdir):
            log_dbrepo_error(lblid, 'arda missing subdir' + lblid,type)
            continue
        for event in events:
            bacid, age, dob, date,qa = event
            qa = str(qa)
            if 'FAIL' in qa:
                continue
            print 'passed qa'
            event_dir = os.path.join(subdir, '-'.join([type, date.strftime('%b-%d-%Y'),'*'])) 
            if not check_dir(event_dir, isglob=True):           
	        log_dbrepo_error(lblid, 'missing event dir' + event_dir,type)
            else:
                print event_dir

"""
Notes about Pandas

dataframe.ix[val] indexes the val row of the data frame


"""

if __name__ == '__main__':

    try:
        infile = sys.argv[1]
    except:
        infile = '/home/jagust/cindeem/CODE/ARDA/spreadsheets/update_03_09_2012/Cindee_ScansUpdate_3_9_12.xls'

    #(mrid ,bloodd, pibd ,fdgd ,fmtd ,racd ,cfnd ,salivad) =main(infile)

    #lbl_2_bac, bac_2_lbl = make_lbl_bac_dict(infile)

    dataframe = dataframe_from_excel(infile)
    header_map = get_headermap(dataframe)
    lbl2bac = lbl_to_bac(dataframe, header_map)
    bac2lbl = bac_to_lbl(dataframe, header_map)
    alltypes, typeset = make_dicts(dataframe)
    print good_header_map(header_map)
    typed = rows_for_types(alltypes, typeset)
    mrid = generate_sampletype_dict(dataframe, typed, 'MRI')
    check_dict_repo(mrid, 'MRI')
    fdgd = generate_sampletype_dict(dataframe, typed, 'PET-FDG-ECAT')
    check_dict_repo(fdgd, 'FDG') 
