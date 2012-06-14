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

def get_subid(infile):
    """ parse filepath string like this:
    /home/to/data/B06-235/seed_ts_dmn_march2012/RSFC/3_corrZ.nii.gz
    with regular expression [B][0-9]{2}\-[0-9]{3}
    to get subject ID  B06-235
    """
    m = re.search('[B][0-9]{2}\-[0-9]{3}',infile)
    if m is None:
        logging.error('subid not found in %s'%infile)
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
    field = [x.original_string for x in field]
    return set(dates), set(protocols), set(field)

def good_set(set):
    """ for a given set, make sure only one item
    else raise error
    """
    if not len(set) == 1:
        print 'Error: ', set
        return False, None
    else:
        return True, set.pop()

def make_dirname(date, visit, field, base = 'MRI'):
    """ given set of dates from dicoms
    visit
    generate outfile name
    """
    dt = parser.parse(date)
    date = dt.strftime('%Y-%m-%d')
    dirname = '_'.join([base+visit, field, date])
    return dirname
    
def copy_file_withdate(file, dest):
    cmd = 'cp --preserve=timestamps %s %s'%(file, dest)
    os.system(cmd)

def copy_files_withdate(files, dest):
    for f in files:
        copy_file_withdate(f, dest)

def modification_date(filename):
    """returns modification date of filename"""
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)


def compare_filedates(infile, original_file):
    """given two files, return of the time stamps
    are equal"""
    modtime_infile = modification_date(infile)
    modtime_orig = modification_date(original_file)
    return modtime_infile == modtime_orig

def md5file(filename, excludeline="", includeline=""):
    """Compute md5 hash of the specified file"""
    m = hashlib.md5()
    blocksz = 128 * m.block_size
    with open(filename,'rb') as f: 
        for chunk in iter(lambda: f.read(blocksz), ''): 
         m.update(chunk)
    return m.hexdigest()

        
def glob_file(globstr, single=True):
    """globs for file specified by globstr
    if single is true, expects one file
    Returns
    -------
    exists : bool true if file exists

    file : /path/to/file
    """
    result = glob(globstr)
    result.sort()
    if len(result) < 1:
        return False, None
    if len(result) == 1 and single:
        return True, result[0]
    if single:
        # expecting only one file, otherwise assume bad
        return False, None
    else:
        # expect more than one, get files
        return True, result

def get_scannotes_fromsync(raw, visit):
    """given raw (/LBLSYNC/finalMRI/Bxx-xxx/raw.tgz
    and visit number  in LBLSYNC
    B96-349/scannotes.txt, visit = ''
    get corresponding scannotes and return"""
    basepath, _ = os.path.split(raw)
    globstr = os.path.join(basepath, '*scan_notes%s.txt'%(visit))
    exists, reconf = glob_file(globstr)
    return exists, reconf


def get_behavioral(raw):
    """ based on raw file, looks for <behavioral>_raw*.tar file(s)
    and returns"""
    basepath, raw = os.path.split(raw)
    behav = raw.replace('tgz', 'tar')
    globstr = os.path.join(basepath, '*%s'%(behav))
    exists, reconf = glob_file(globstr,single=False)
    return exists, reconf

def clean_directory(directory):
    """ removes directory and contents and then creates
    new empty directory
    """
    shutil.rmtree(directory)
    os.mkdir(directory)

def renamed_archive_copy(filename, dest):
    """ given first file of renamed
    tar archive it to dest"""
    startdir = os.getcwd()
    pth, basename = os.path.split(filename)
    basen = '_'.join(basename.split('_')[:-1])
    globstr = os.path.join(pth, basen + '*')                     
    tgznme = basen +'.tgz'
    cmd = 'tar cfz %s/%s %s'%(dest, tgznme, globstr)
    os.chdir(pth)
    logging.info(cmd)
    os.chdir(startdir)
    return cmd

def get_field_date(raw):
    with tarfile.open(raw, "r:gz") as tar:
        for member in tar:
            if '.IMA' in member.name and not '._' in member.name:
                tmpf = tar.extractfile(member.name)
                plan = dicom.read_file(tmpf)
                field = plan.MagneticFieldStrength.original_string
                date = plan.SeriesDate
                return field, date

    
    return field, date

    
if __name__ == '__main__':

    raw, renamed = tmp_dirs()
    testing.assert_equal(True, os.path.isdir(raw))
    testing.assert_equal(True, 'renamed' in renamed)
    # test dicom re-naming
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
    # test info from dicoms
    testing.assert_equal(dates, set(['20120604']))
    testing.assert_equal(True, 'localizer' in protocols)
    # test subid
    subid = get_subid(raw)
    testing.assert_equal(subid, 'B12-243')
    single_field, field = good_set(field)
    single_date, date = good_set(dates)
    # test manipulating sets from dicoms
    testing.assert_equal(True, single_field)
    testing.assert_equal(field, '1.5')
    # test generating directory name
    dirname = make_dirname(date, visit_number, field)
    testing.assert_equal(dirname, 'MRI_1.5_2012-06-04')
    exists, sync_reconnotes = get_scannotes_fromsync(raw, visit_number)
    testing.assert_equal(True, exists)
    testing.assert_equal(sync_reconnotes,
                         '/home/jagust/cindeem/LBLSYNC/finalMRI/B12-243/scan_notes.txt')
    exists, behavioral = get_behavioral(raw)
    # test finding behavioral
    testing.assert_equal(exists, True)
    testing.assert_equal(True, 'scenetask_raw.tar' in behavioral[0])
    
    
    cmd = renamed_archive_copy(newnames[0], dirname)
    
    shutil.rmtree(tmpdir)
