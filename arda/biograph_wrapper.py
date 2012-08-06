# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
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
    syncdir = '/home/jagust/cindeem/LBLSYNC/finalPET'
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
    recons = bio.glob('%s/B*/*bio*/recon'%(syncdir))
    recons.sort()

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
        outdir, exists = pp.bg.make_dir(os.path.join(arda, subid),
                                        dirname = dirnme)
        if not exists:
            # direcotry didnt exist, copy files
            copy = True
        elif exists
        #check if exists
        # copy if not exists or if changed
        # check for recon notes
        # copy recon notes if new or missing
        
        
