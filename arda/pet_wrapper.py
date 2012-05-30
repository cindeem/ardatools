import sys, os
sys.path.insert(0, '/home/jagust/cindeem/CODE/ARDA/ardatools/arda')
import pet_to_repo as ptr

if __name__ == '__main__':

    #arda
    arda = '/home/jagust/arda/lblid'
    syncdir = '/home/jagust/cindeem/LBLSYNC/finalPET'
    
    tracer = 'fdg'
    recons = ptr.get_recons_from_sync(tracer, syncdir)
    for recondir in recons[:1]:
        subid = ptr.get_subid(recondir)
        real_tracer = ptr.get_real_tracer(recondir, subid)
        globstr = os.path.join(recondir, '*.v')
        has_ecats, ecats = ptr.glob_file(globstr, single=False)
        if not has_ecats:
            print recondir, 'no ecats'
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
        print 'same',same, 'copy', copy, arda_dir
        if not same:  #copy ecats to new dir
            ptr.update_outdir(arda_dir, clobber=True)
            ptr.copy_files_withdate(ecats, arda_dir)
        if copy:
            ptr.copy_file_withdate(reconnotes_rsync, os.path.join(arda_dir,
                                                                  recon_fname))
            
