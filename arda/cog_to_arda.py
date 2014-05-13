# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys, os
from glob import glob
import argparse
import datetime
import dateutil.parser as parser
import pandas
import numpy.testing as testing
import numpy as np

def check_file_session(infile, session):
    """ match file session to specified session"""
    return '_S%d_'%(session) in infile

def header_key_find(header_map, identifier='Neuropsych'):
    header_str = [x for x in header_map if identifier in x]
    if len(header_str) > 1:
        raise StandardError('more than one %s found %s'%(identifier,
                                                         test_date_col))
    else:
        return header_str[0]

def find_valid_data(small):
    """ find rows with valid lblid, and test dates"""
    headers = small.columns
    lblid = header_key_find(headers, identifier='LBNL')
    date = header_key_find(headers, identifier='Date')    
    goodrows = []
    for nrow, row in small.iterrows():
        #print row[1]
        
        if isinstance(row[lblid], unicode) and not isinstance(row[date],
                pandas.tslib.NaTType):
            goodrows.append(nrow)
            #print row
    return goodrows

def get_smalldf(dataframe, headers):
    """ returns reindex of dataframe with only lblid, testdate, dob"""
    # get impt colums
    lblid = header_key_find(headers, identifier='LBNL')
    date = header_key_find(headers, identifier='Date')
    dob = header_key_find(headers, identifier='Birthday')
    small = dataframe.reindex(columns=(lblid, date, dob))
    return small

def check_arda_dir(row, session, headers):
    arda = '/home/jagust/arda/lblid'
    lblid_header = header_key_find(headers, identifier='LBNL')
    date = header_key_find(headers, identifier='Date')
    lblid = row[lblid_header]
    testdate = row[date].strftime('%Y-%m-%d')
    cogdir = os.path.join(arda, lblid, 'COG_S%d_%s'%(session, testdate))
    if not os.path.isdir(cogdir):
        try:
            os.mkdir(cogdir)
            return cogdir, False
        except:
            print '%s missing . skipping'%(os.path.split(cogdir)[0])
            return cogdir, True #skip since no lblid base dir
    else:
        return cogdir, True

def check_dob(cogdir, dob):
    subdir,_ = os.path.split(cogdir)
    dobf = os.path.join(subdir, '.DOB-%s'%dob)
    current_dob = glob('%s/.DOB-*'%subdir)
    if len(current_dob) < 1:
        os.system('touch %s'%dobf)
        return
    if not current_dob[0] == dobf: #dob dont match
        raise IOError('DOB mismatch, old: %s, new: %s'%(current_dob[0],
                                                        dobf))
        
def check_bac(cogdir, bac):
    subdir,_ = os.path.split(cogdir)
    bacf = os.path.join(subdir, bac)
    current_bac = glob('%s/BAC*'%subdir)
    if len(current_bac) < 1:
        os.system('touch %s'%bacf)
        return
    if not current_bac[0] == bacf: #dob dont match
        raise IOError('DOB mismatch, old: %s, new: %s'%(current_bac[0],
                                                        bacf))
            
    
def main(infile, session):
    if not check_file_session(infile, session):
        raise IOError('Session number: %d does not match file %s'(session,
                                                                  infile))
    dataframe = pandas.ExcelFile(infile).parse('Sheet1')
    headers = dataframe.columns
    small = get_smalldf(dataframe, headers)
    goodrows = find_valid_data(small)
    #stop
    print 'number of good data:', len(goodrows)
    for rown in goodrows:
        row = dataframe.ix[rown]
        cogdir, exists = check_arda_dir(row, session, headers)
        print exists, cogdir
        # check birthdate
        dobh = header_key_find(headers, identifier='Birthday') 
        dob = row[dobh].strftime('%Y-%m-%d')
        check_dob(cogdir, dob)
        # check BAC
        bach = header_key_find(headers, identifier='BAC')
        bacid = row[bach]
        check_bac(cogdir, bacid)
        if not exists:
            # save data to directory
            tmp = pandas.DataFrame(row)
            lblid_header = header_key_find(headers, identifier='LBNL')
            date = header_key_find(headers, identifier='Date')
            lblid = row[lblid_header]
            testdate = row[date].strftime('%Y-%m-%d')
            outfile = os.path.join(cogdir, '%s_COG_S%d_%s.xls'%(lblid,
                                                                session,
                                                                testdate))
            tmp.to_excel(outfile)
            print 'Wrote %s'%(outfile)
                                   

if __name__ == '__main__':

    ##tests

    excel = 'tests/Cindee_BACSUpdate_S3_10_30_12.xls'
    session = 3
    # test check file session
    testing.assert_equal(check_file_session(excel, session), True)
    
    # test find headers
    dataframe = pandas.ExcelFile(excel).parse('Sheet1')
    headers = dataframe.columns
    small = get_smalldf(dataframe, headers)
    testing.assert_equal(len(small.columns), 3)
    # test goodrows
    goodrows = find_valid_data(small)
    testing.assert_equal(len(goodrows), 71)
    #test row data
    row = dataframe.ix[goodrows[0]]
    cogdir, exists = check_arda_dir(row, session)
    
