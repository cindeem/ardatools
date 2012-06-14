# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import sys, os, shutil
sys.path.insert(0, '/home/jagust/cindeem/CODE/ARDA/ardatools/arda')
import mri_to_repo as mtr
import logging, logging.config
from time import asctime
sys.path.insert(0,'/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp

if __name__ == '__main__':

    #arda
    arda = '/home/jagust/arda/lblid'
    syncdir = '/home/jagust/cindeem/LBLSYNC/finalMRI'
    logdir , _ = os.path.split(syncdir)
    #set up log
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(logdir,'logs',
                           '%s%s.log'%(__file__,cleantime))
    
    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    user = os.environ['USER']
    logging.info('###START %s :::'%__file__)
    logging.info('###USER : %s'%(user))
    
    # find all subjecs raw scans
    scans = mtr.glob('%s/B10*/raw*.tgz'%(syncdir))
    scans.sort()

    for raw in scans[:]:
        # meta data
        logging.info(raw)
        _, rawf = os.path.split(raw)
        subid = mtr.get_subid(raw)
        if subid is None:
            logging.error('no subid in %s'%(raw))
            continue        
        logging.info(subid)
        visit_number = mtr.get_visit_number(raw)
        # get estimate of series field and date
        field, date = mtr.get_field_date(raw)            
        dirname = mtr.make_dirname(date, visit_number, field)
        ardadir = mtr.os.path.join(arda, subid, dirname)
        exists, _ = mtr.glob_file(ardadir)
        if not exists:
            os.makedirs(ardadir)
        arda_raw = os.path.join(ardadir, rawf)
        exists, _ = mtr.glob_file(arda_raw)
        copy = True
        if exists:
            # check if update needed
            same = mtr.compare_filedates(raw, arda_raw)
            if same:
                logging.info('%s and %s are same, no update'%(raw,
                                                              arda_raw))
                copy = False
            else:
                copy = True
                mtr.clean_directory(ardadir)
                logging.info('cleaned %s'%(ardadir))

        if copy:
            newnames, dcmd, tmpdir = mtr.clean_tgz(raw)
            dates, protocols, field = mtr.get_info_from_dicoms(dcmd)
            # make/check good field
            single_field, field = mtr.good_set(field)
            if not single_field:
                # has multiple field strengths in raw, fix
                shutil.rmtree(tmpdir)
                logging.error('multiple field strengths in %s, skipping'%raw)
                continue        
            # make/check date
            single_date, date = mtr.good_set(dates)
            if not single_date:
                shutil.rmtree(tmpdir)
                # has multiple visits in raw, fix
                logging.error('%s multiple visits, %s skipping'%(raw, dates))
                continue
            
            # tar zip individual scans to destdir
            for renamed in newnames:
                cmd = mtr.renamed_archive_copy(renamed, ardadir)
                os.system(cmd)
            logging.info('copied raw and converted to %s'%(ardadir))
            mtr.copy_file_withdate(raw, ardadir)
            shutil.rmtree(tmpdir)            
        #deal with scan notes
        # scan notes
        notes_exist, sync_notes = mtr.get_scannotes_fromsync(raw, visit_number)
        if notes_exist:
            _, notes_name = os.path.split(sync_notes)
            arda_notes = os.path.join(ardadir, notes_name)
            arda_notes_exist, _ = mtr.glob_file(arda_notes)
            if arda_notes_exist:
                same = mtr.compare_filedates(sync_notes, arda_notes)
                if not same:
                    mtr.copy_file_withdate(sync_notes,ardadir)
                    logging.info('updated %s'%(arda_notes))
            else:
                mtr.copy_file_withdate(sync_notes,ardadir)
                logging.info('copied %s'%(arda_notes))                
        else:
            logging.info('no scannotes for %s'%(raw))
        # behavioral
        behav_exists, behavioral = mtr.get_behavioral(raw)        
        # deal with any behavioral
        if behav_exists:
            for behav in behavioral:
                _, tmpnme = os.path.split(behav)
                arda_behav = os.path.join(ardadir,tmpnme)
                arda_behav_exist, arda_behav = mtr.glob_file(arda_behav)
                if arda_behav is None:
                    mtr.copy_file_withdate(behav, ardadir)
                    logging.info('copying %s in %s'%(behav, ardadir))
                elif not mtr.compare_filedates(behav, arda_behav):
                    # update only if changes found
                    mtr.copy_file_withdate(behav, ardadir)
                    logging.info('updating %s in %s'%(behav, ardadir))
                else:
                    logging.info('%s exists and up to date'%(arda_behav))
        logging.info('Finished %s'%subid)
