# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import sys, os, shutil
from glob import glob
import logging, logging.config
from datetime import datetime
import pandas

sys.path.insert(0, '/home/jagust/cindeem/CODE/ARDA/ardatools/arda')
import mri_to_repo as mtr
import utils


def is_bacs(instr):
    """checks if instr is bacs id"""
    return 'BAC' in instr

def bac_to_lbl(excelfile):
    """ uses dat ain excelfile to create a dict mapping
    bac to lblids"""
    ef = pandas.ExcelFile(excelfile)
    df = ef.parse(ef.sheet_names[0], index_col = 0)
    # drop nan vals
    df = df.dropna()
    outd = df.to_dict()
    # real dict is nested
    return outd[outd.keys()[0]]

def get_realvisit(visit):
    """ parses visit (v2), returns number as str, unless number is 1
    then returns empty string"""
    tmpv = visit.replace('v','')
    if tmpv == '1':
        return ''
    return tmpv


if __name__ == '__main__':

    #arda
    arda = '/home/jagust/arda/lblid'
    syncdir = '/home/jagust/LBL/3T'
    mapfile = '/home/jagust/LBL/3T/LBL_BAC_IDS.xlsx'
    logdir = os.path.join(syncdir, 'logs')
    #set up log
    cleantime = datetime.strftime(datetime.now(),'%Y-%m-%d-%H-%M')
    logfile = os.path.join(logdir,
                           '%s%s.log'%(__file__,cleantime))

    log_settings = utils.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    user = os.environ['USER']
    logging.info('###START %s :::'%__file__)
    logging.info('###USER : %s'%(user))

    # get bac2lbl mapping
    bac2lbl = bac_to_lbl(mapfile)
    # find all subjecs raw directories
    subs = mtr.glob('%s/B*_v*'%(syncdir))
    subs.sort()
    for sub in subs:
        _, sid = os.path.split(sub)
        subid, visit = sid.split('_')
        visitstr = get_realvisit(visit)
        if is_bacs(subid):
            print subid, 'is bacs'
            try:
                subid = bac2lbl[subid]
            except KeyError:
                logging.error('{0} has no LBLID, skipping'.format(subid))
                continue
        print subid, visit, sub
        globstr = os.path.join(sub, '*.tgz')
        scans = sorted(glob(globstr))
        if len(scans) < 1:
            logging.error('{}: missing scans as tgz files'.format(sub))
            continue
        localizer = [x for x in scans if 'localizer' in x]
        try:
            localizer = localizer[0]
        except:
            ## fall back on mprage
            localizer = [x for x in scans if 'rage' in x]
            try:
                localizer = localizer[0]
            except:
                logging.error('{}: no localizer or mprage found'.format(sub))
                continue
        try:
            date, fieldstr = mtr.info_from_tarfile(localizer)
        except:
            logging.error('Error pulling info from  {}'.format(localizer))
            logging.error('skipping {}'.format(sub))
            continue
        arda_dirname = mtr.make_dirname(date, visitstr, fieldstr + 'T')
        print arda_dirname

        ardadir = mtr.os.path.join(arda, subid, arda_dirname)
        exists, _ = mtr.glob_file(ardadir)
        if exists:
            logging.warn('{} exists, skipping'.format(ardadir))
            continue
        os.makedirs(ardadir)
        for scan in scans:
            newfile = mtr.fname_presuffix(scan, prefix = subid,
                newpath = ardadir)
            mtr.copy_file_withdate(scan, newfile)
            logging.info('copy: {}'.format(newfile))
        scannotes = glob(os.path.join(sub, '*scan*notes*.txt' ))
        try:
            mtr.copy_file_withdate(scannotes[0], ardadir)
            logging.info('{} copy scannotes'.format(ardadir))
        except:
            logging.info('{} missing scan notes'.format(sub))


        ## get files
        ## make outdir
        ## rename and move files
