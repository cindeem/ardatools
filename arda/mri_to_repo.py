# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os, shutil
import sys
from glob import glob
import hashlib
import dicom
import calendar
import tempfile
import filecmp
from nipype.interfaces.base import CommandLine


# for testing
import numpy.testing as testing

def get_subid(infile):
    """ parse filepath string like this:
    /home/to/data/B06-235/seed_ts_dmn_march2012/RSFC/3_corrZ.nii.gz
    with regular expression [B][0-9]{2}\-[0-9]{3}
    to get subject ID  B06-235
    """
    m = re.search('[B][0-9]{2}\-[0-9]{3}',infile)
    if m is None:
        print 'subid not found in %s'%infile
        return None
    else:
        return m.group(0)
     


def tmp_dirs():
    """creates a tmp raw direcotry to hold
    unzipped tgz files and renamed dir to
    hold renamed files"""
    tmpdir = tempfile.mkdtemp()
    raw = '%s/raw'%(tmpdir)
    os.mkdir(raw)
    renamed = '%s/renamed'%(tmpdir)
    os.mkdir(renamed)
    return raw, renamed

def untar(infile, outdir):
    """ untars given tar archive to outdir"""
    cmd = 'tar  -xzf %s --directory=%s'%(infile, outdir)
    os.system(cmd)
    os.system('chmod -R 774 %s'%(raw))


def rename_dicom(dcm, outdir):
    """ rnames a dicom based on
    plan.PatientID,
    plan.ProtocolName,
    plan.StudyDate,
    plan.SeriesNumber,
    plan.InstanceNumber
    saves to outdir"""
    _, ext = os.path.splitext(dcm)
    plan = dicom.read_file(dcm)
    newname = '%s_%s_%s_%05d_%05d'%(plan.PatientID,
                                    plan.ProtocolName,
                                    plan.StudyDate,
                                    plan.SeriesNumber,
                                    plan.InstanceNumber)
    newname = newname.replace(' ','_')
    newname = newname.replace('.','_')
    newname = newname + ext
    newfile = os.path.join(outdir,newname)
    cmd = 'cp %s %s'%(dcm,newfile)
    out = CommandLine(cmd).run()
    if not out.runtime.returncode == 0:
        raise IOError('failed to rename %s'%dcm)
    else:
        return newfile, plan

def rename_dicoms(dicoms, outdir):
    renamed = []
    for dcm in dicoms:
        tmp = rename_dicom(dcm, outdir)
        renamed.append(tmp)
    return renamed

def clean_tgz(infile):
    # tmp dir to hold files
    raw, renamed = tmp_dirs()
    tmpdir, _ = os.path.split(raw)
    # untar
    untar(infile, raw)
    # walk directory and rename dicom files
    dcmd = {} # dict holding info on all the renamed files
    for root, dirs, files in os.walk(raw):
        if files:
            for f in files:
                if not 'IMA' in f or f[0] == '.':
                    # not dicom
                    continue
                tmpf = os.path.join(root,f)
                newf, plan = rename_dicom(tmpf, renamed)
                dcmd[newf] = [plan.StudyDate, plan.ProtocolName, plan.MagneticFieldStrength ]
    # find unique series
    newnames = glob('%s/*001.*'%(renamed))
    newnames.sort()
    return newnames, dcmd, tmpdir


def get_visit_number(raw):
    """ looks at file name to get visit number"""
    _, fname = os.path.split(raw)
    num = fname.split('.')[0].replace('raw','')

    return num

def get_info_from_dicoms(dict):
    """given a dict of files ->[date, protocol, field]"""
    dates = []
    protocols = []
    field = []

    for d,p,f in dict.values():
        dates.append(d)
        protocols.append(p)
        field.append(f)
    return set(dates), set(protocols), set(field)
    

if __name__ == '__main__':

    raw, renamed = tmp_dirs()
    testing.assert_equal(True, os.path.isdir(raw))
    testing.assert_equal(True, 'renamed' in renamed)
    dcm = 'tests/sample.IMA'
    newdcm, plan = rename_dicom(dcm, renamed)
    testing.assert_equal(newdcm, os.path.join(renamed,
                                              'B12-243_localizer_20120604_00001_00001.IMA'))
    
    
    # clean up
    shutil.rmtree(raw)
    shutil.rmtree(renamed)
    raw = '/home/jagust/cindeem/LBLSYNC/finalMRI/B12-243/raw.tgz'
    visit_number = get_visit_number(raw)
    newnames, dcmd, tmpdir = clean_tgz(raw)
    dates, protocols, field = get_info_from_dicoms(dcmd)
    testing.assert_equal(dates, set(['20120604']))
    testing.assert_equal(field, set(['1.5']))
    subid = get_subid(raw)
    testing.assert_equal(subid, 'B12-243')
