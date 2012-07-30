import sys, os
sys.path.insert(0, '/home/jagust/cindeem/CODE/ARDA/ardatools/arda')
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
    
    tracer = 'fdg'
    logging.info(tracer)
    
    recons = ptr.get_recons_from_sync(tracer, syncdir)
    for recondir in recons[:]:
        subid = ptr.get_subid(recondir)
        real_tracer = ptr.get_real_tracer(recondir)
        globstr = os.path.join(recondir, '*.v')
        has_ecats, ecats = ptr.glob_file(globstr, single=False)
        if not has_ecats:
            print recondir, 'no ecats'
            logging.error('NO ECATS: %s'%recondir)
            continue
        ## generate string of arda output directory
        
        arda_dir = ptr.make_outdirname(ecats, tracer=real_tracer.upper(),
                                       arda=arda)
        exists, orig_ecats = ptr.glob_file('%s/*.v'%arda_dir, single=False)
        same = ptr.check_dates(ecats, orig_ecats)
        has_recon, reconnotes_rsync = ptr.get_reconnotes_fromsync(recondir,
                                                                  real_tracer)
        recon_fname = ptr.gen_recon_fname(ecats, arda_dir, real_tracer)
        orig_exists, orig_notes = ptr.glob_file('%s/*notes*.txt'%(arda_dir))
        copy = ptr.check_recon_notes(recon_fname, orig_notes)
        print 'same',same, 'copy reconnotes', copy, arda_dir
        logging.info(arda_dir)
        logging.info('Files Same %s: %s'%(arda_dir, same))
        logging.info('%s Copy ReconNotes: %s (exists: %s)'%(subid, copy,has_recon))
        if not same:  #copy ecats to new dir
            ptr.update_outdir(arda_dir, clobber=True)
            ptr.copy_files_withdate(ecats, arda_dir)
        if copy and has_recon:
            
            ptr.copy_file_withdate(reconnotes_rsync, os.path.join(arda_dir,
                                                                  recon_fname))
            