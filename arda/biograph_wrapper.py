# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/local/epd/bin/python
import sys, os, shutil, re
sys.path.insert(0, '/home/jagust/cindeem/CODE/ARDA/ardatools/arda')
import biograph_to_repo as bio
import pet_to_repo as ptr
import logging, logging.config
from time import asctime
sys.path.insert(0,'/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp

if __name__ == '__main__':

    #arda
    arda = '/home/jagust/arda/lblid'
    syncdir = '/home/jagust/LBL/finalPET'
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
    
    # find all subjecs recon directories
    recons = bio.glob('%s/B*/*bio*/*recon'%(syncdir))
    recons.sort()
    # find all subjects biograph directories in arda
    biographs = bio.glob('%s/B*/*BIO*'%arda)
    biographs.sort()

    for recon in recons:
        # Get subid
        subid = bio.regex_subid(recon)
        # get tgz files
        tgzs, ntgz = bio.tgz_in_recon(recon)
        if ntgz < 1:
            logging.error('no TGZ files: %s'%(recon))
            continue
        scandate = bio.check_scandates(tgzs)
        # generate full output directory name
        real_tracer = bio.get_real_tracer(recon)
        dirnme = bio.make_dirname(scandate, real_tracer)
        outdir, exists = pp.bg.make_rec_dir(os.path.join(arda, subid),
                                            dirname = dirnme)
        if not exists:
            # directory didnt exist, copy files
            logging.info('%s is NEW, copy date'%outdir)
            copy = True
        else:
            biographs.remove(outdir)
            
            arda_tgz, arda_ntgz=bio.tgz_in_recon(outdir)
            same_file = ptr.check_dates(tgzs, arda_tgz)
            if same_file:
                logging.info('%s exists, files are the same'%(outdir))
                copy = False
            else:
                copy = True
                logging.info('%s exists, files NOT same'%(outdir))

        if copy:
            os.system('rm %s/*'%(outdir))
            ptr.copy_files_withdate(tgzs, outdir)
            logging.info('COPIED TGZ: '%(tgzs))
        # check for recon notes in sync
        recon_notes = bio.check_reconnotes(recon)
        if recon_notes is None:
            # nothing to copy
            continue
        # check for recon notes in arda
        _ , rn_fname = os.path.split(recon_notes)
        globstr = os.path.join(outdir, rn_fname)
        arda_reconnotes = pp.find_single_file(globstr)
        # copy recon notes if new or missing
        if arda_reconnotes is None:
            ptr.copy_file_withdate(recon_notes, outdir)
            logging.info('No recon_notes in arda, copy %s'%(recon_notes))
            
        else:
            same_recon_notes = ptr.check_dates([recon_notes],
                                               [arda_reconnotes])
            
            if not same_recon_notes:
                ptr.copy_file_withdate(recon_notes, outdir)
                logging.info('DIFFERENT recon notes, copy %s'%(recon_notes))
            else:
                logging.info('%s same  in arda, NO COPY'%(recon_notes))
        # check for timing file
        timing_file = bio.check_pib_timing(recon)
        if not timing_file is None:
            logging.info('copied %s'%timing_file)
            ptr.copy_file_withdate(timing_file, outdir)
    ## log any biographs not found
    if len(biographs) > 0:
    
        logfile = os.path.join(logdir,'logs',
                               'ARDAERROR-%s%s.log'%(__file__,
                                                     cleantime))
        with open(logfile, 'w+') as fid:
            for item in biographs:
                fid.write('%s,\n'%item)
                
