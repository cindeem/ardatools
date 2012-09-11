# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, shutil
import sys, re
from glob import glob
import hashlib
import dicom
import datetime
import dateutil.parser as parser
import tempfile
import filecmp
import tarfile
from nipype.interfaces.base import CommandLine
import logging

# for testing
import numpy.testing as testing



def get_date(raw):
    """ reads a tgz file, searches for dicom, and returns
    SeriesDate field"""
    with tarfile.open(raw, "r:gz") as tar:
        for member in tar:
            if  not '._' in member.name or not member.name == 'raw':
                print member.name
                try:
                    tmpf = tar.extractfile(member)
                    #print tmpf
                    plan = dicom.read_file(tmpf)
                    date = plan.SeriesDate
                    return date
                except:
                    print member.name
                    date = None
                    continue
                    
    return date

def check_scandates(list):
    """given a list of tgx files, check for scan dats and make sure they are
    all the same)
    """
    alldates = [get_date(x) for x in list]
    if not len(set(alldates)) == 1:
        logging.error('Scan dates MISMATCH:  %s'%list)
        logging.error(alldates)
        raise IOError('Scan dates Mismatched: %s'%(alldates))
    else:
        return alldates[0]

    
    
    

def get_real_tracer(raw):
    """ get tracer type and visit, check for NIFD"""        
    pth, _ = os.path.split(raw)
    _, tracer = os.path.split(pth)
    if 'NIFD' in raw:
        return 'NIFD' + tracer
    return tracer


def make_dirname(date, tracer):
    """ given set of dates from dicoms
    generate outfile name
    """
    dt = parser.parse(date)
    date = dt.strftime('%Y-%m-%d')
    dirname = '_'.join([tracer.upper(),  date])
    return dirname


def tgz_in_recon(recon):
    """ returns a list of tgz files found in recondirectory
    and number of files found"""
    globstr = os.path.join(recon, '*.tgz')
    result = glob(globstr)
    result.sort()
    return result, len(result)


def regex_subid(string, pattern='B[0-9]{2}-[0-9]{3}'):
    """ find subject ID in string
    default is LBL style SUBID
    return subid, or raise error
    """
    try:
        m = re.search(pattern, string)
        subid = m.group()
        return subid
    except:
        logging.error('cant find ID in %s'%string)
        raise IOError('cant find ID in %s'%(string))
  

def check_reconnotes(recon):
    """ check for existence of recon notes"""
    pth , _ = os.path.split(recon)
    basepth, fnme = os.path.split(pth)
    if 'NIFD' in recon:
        fnme = fnme.split('_')        
        globstr = os.path.join(basepth,
                               '%sNIFD*%s*'%(fnme[0],fnme[1]) + '.txt')
    else:
        globstr = os.path.join(basepth, fnme.replace('_', '*') + '.txt')
    result = glob(globstr)
    if not 'NIFD' in recon:
        result = [x for x in result if not 'NIFD' in x]
    if len(result) < 1:
        logging.error('NO RECONNOTES: %s'%globstr)
        return None
    elif len(result) > 1:
        logging.error('TOO MANY RECONNOTES: %s'%globstr)
        return None
    else:
        return result[0]
    
    

if __name__ == '__main__':
    ## tests for now
    sync_recon = '/home/jagust/cindeem/LBLSYNC/finalPET/B09-290/pib2_biograph/recon'
    testdat = 'tests/B09-290PIBFR25TO26.tgz'
    # Test date form tar archive
    date = get_date(testdat)
    testing.assert_equal(date, '20120313')
    # test tracer from string
    real_tracer = get_real_tracer(sync_recon)
    testing.assert_equal(real_tracer, 'pib2_biograph')
    # test dirname creation
    dirnme = make_dirname(date, real_tracer)
    testing.assert_equal(dirnme, 'PIB2_BIOGRAPH_2012-03-13')
    # test subid from string
    subid = regex_subid(sync_recon)
    testing.assert_equal(subid, 'B09-290')
    # test check for recon notes
    recon_notes = check_reconnotes(sync_recon)
    testing.assert_true(recon_notes,
                        '/home/jagust/cindeem/LBLSYNC/finalPET/B09-290/pib2reconnotes_biograph.txt')
    
