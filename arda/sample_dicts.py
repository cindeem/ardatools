import sys
import datetime
import dateutil.parser as parser
import xlrd
import pandas
import numpy as np

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


def make_dicts(dataframe):
    """ create unique sample dictionaries from dataframe"""
    shdr = simple_header(get_headermap(dataframe))
    mytype = []
    for items in zip(dataframe[shdrmap['SampleType']],
                     dataframe[shdrmap['Radiotracer']],
                     dataframe[shdrmap['PETScanner']]):
        
        ritems = [str(x) for x in items]
        typestr = '-'.join(ritems).replace('-n/a','')
        mytype.append(typestr)
    unique_types = set(mytype)
    return mytype, unique_type


def main(infile):
    mrid = {}
    bloodd = {}
    pibd = {}
    fdgd = {}
    fmtd = {}
    racd = {}
    cfnd = {}
    salivad = {}
    wb = xlrd.open_workbook(infile)
    sheet = wb.sheet_by_index(0)
    nrows = sheet.nrows

    header_map = get_header_map(sheet.row_slice(0))

    for rown in range(1,nrows):
        tmprow = sheet.row_slice(rown)
        sampletype = tmprow[header_map['Sample Type']].value.replace('\n', '')
        if sampletype == '':
            print rown, lblid
            continue        
        lblid = tmprow[header_map['LBNL ID']].value.upper()
        bacid = tmprow[header_map['Patient Info::BAC ID']].value.upper()
        dob = xlrd.xldate_as_tuple(tmprow[header_map['Patient Info::Date of Birth']].value,0)
        dob = '-'.join(['%d'%x for x in dob[:3]])
        sampledate = xlrd.xldate_as_tuple(tmprow[header_map['Sample Date']].value,0)
        sampledate = '-'.join(['%d'%x for x in sampledate[:3]])
        
        pettype = tmprow[header_map['Radiotracer']].value
        tmpdict = {lblid:[sampledate,dob,bacid]}
        
        if sampletype == 'MRI':
            update_dict(mrid, tmpdict)
            
        elif sampletype.upper() == 'BLOOD':
            update_dict(bloodd, tmpdict)
            #bloodd.update({lblid:[sampledate,dob,bacid]})
            #print line
        elif sampletype == 'PET':
            if 'PIB' in pettype.upper():
                update_dict(pibd, tmpdict)
                #pibd.update({lblid:[sampledate,dob,bacid]})
            elif 'FDG' in pettype:
                update_dict(fdgd, tmpdict)
                #fdgd.update({lblid:[sampledate,dob,bacid]})
            elif 'FMT' in pettype:
                update_dict(fmtd, tmpdict)
                #fmtd.update({lblid:[sampledate,dob,bacid]})
            elif 'RAC' in pettype:
                update_dict(racd, tmpdict)
                #racd.update({lblid:[sampledate,dob,bacid]})
            elif 'CFN' in pettype:
                update_dict(cfnd, tmpdict)
                #cfnd.update({lblid:[sampledate,dob,bacid]})
            else:
                print 'pettype: ', pettype, ' NOT FOUND'
        elif sampletype.upper() == 'SALIVA':
            update_dict(salivad, tmpdict)
            #salivad.update({lblid:[sampledate,dob,bacid]})
        else:
            print 'sampletype ', sampletype, ' NOT FOUND'
            print rown
    return (mrid ,bloodd, pibd ,fdgd ,fmtd ,racd ,cfnd ,salivad) 


def make_lbl_bac_dict(infile):
    lbl_2_bac = {}
    bac_2_lbl = {}
    wb = xlrd.open_workbook(infile)
    sheet = wb.sheet_by_index(0)
    nrows = sheet.nrows
    header_map = get_header_map(sheet.row_slice(0))
    for rown in range(1,nrows):
        tmprow = sheet.row_slice(rown)
        lblid = tmprow[header_map['LBNL ID']].value.upper().replace('\n','')
        bacid = tmprow[header_map['Patient Info::BAC ID']].value.upper().replace('\n','')

        if len(lblid) < 2 or len(bacid) < 2:
            print lblid, bacid
            continue
        if not lbl_2_bac.has_key(lblid):
            lbl_2_bac.update({lblid:bacid})
        if not bac_2_lbl.has_key(bacid):
            bac_2_lbl.update({bacid:lblid})
    return lbl_2_bac, bac_2_lbl

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
