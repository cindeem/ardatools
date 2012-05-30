import sys, os, re
import shutil
import datetime
#sys.path.insert(0,'/home/jagust/cindeem/tmpgit/cindeem-nibabel')
import nibabel.ecat as ecat
from glob import glob
import hashlib
import filecmp
import json

# for testing
import numpy.testing as testing


"""
finalPET structure
<subid>/<tracer>
if <tracer is pib, fdg>
<subid>/<tracer>/recon
else if fmt
<subid>/<tracer>/recon/4mm*
else if rac
<subid>/<tracer>/recon/rac/rac1 or rac2/recon

Find all possible tracer directories from rsync
tracer = 'fdg'
( glob('%s/B*/%s*/*recon'(syncdir, tracer)  )
get ecats
generate output directory
check if output directory exists on arda
if not, 
   create new dated PET dir <TRACER>_date_time
   copy relevant files
if yes,
   check modification dates of old and new data
   if different:
       remove original directory
       copy over new data
   else:
       do nothing
Check reconnotes:
    generate reconnote filename from data
    check if exists in arda
    if not:
        get rid of any old notes
        copy
    if yes:
        do nothing
   

   ## TODO  shold check date of pet files, or check date of

"""
def save_json(filename, data):
    """Save data to a json file
    
    Parameters
    ----------
    filename : str
        Filename to save data in.
    data : dict
        Dictionary to save in json file.

    """
    fp = file(filename, 'w')
    json.dump(data, fp, sort_keys=True, indent=4)
    fp.close()


def load_json(filename):
    """Load data from a json file

    Parameters
    ----------
    filename : str
        Filename to load data from.

    Returns
    -------
    data : dict
   
    """
    fp = file(filename, 'r')
    data = json.load(fp)
    fp.close()
    return data


def md5file(filename, excludeline="", includeline=""):
    """Compute md5 hash of the specified file"""
    m = hashlib.md5()
    blocksz = 128 * m.block_size
    with open(filename,'rb') as f: 
        for chunk in iter(lambda: f.read(blocksz), ''): 
         m.update(chunk)
    return m.hexdigest()


def check_hash(filelist, jsonfile):
    """given a file list, generate dictionary of md5 hashes
    for each file, check for existing json file, load and
    compare dicts

    Parameters
    ----------
    filelist : list of datfiles

    jsonfile : filename of json file to check against

    Returns
    -------
    hashmatch : Bool
        True if hash dictionaries are equal
        False if no jsonfile or dict not equal
    
    jsondict  : dict
        dictionary that can be written to jsonfile
    """
    jsondict = {}
    for f in filelist:
        filehash = md5file(f)
        jsondict.update({f: filehash})
    
    if not os.path.exists(jsonfile):
        # json was never created
        hashmatch = False
        return hashmatch, jsondict

    else:
        orig_jsondict = load_json(jsonfile)

    if not orig_jsondict == jsondict:
        # new files have different md5hash
        return False, jsondict
    else:
        return True, orig_jsondict

def check_dates(filelist, original_list):
    compares = []
    try:
        for new, old in zip(filelist, original_list):
            compares.append(compare_filedates(new,old))
        return all(compares)
    except:
        return False

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
     

def make_outdirname(petframes, tracer='', arda='/home/jagust/arda/lblid'):
    """ given list of subjects pet files
    create full <dated> path
    to arda directory"""
    # file structure
    # /home/jagust/cindeem/LBLSYNC/finalPET/finalPET/B11-255/pib/recon
    # /B11_255-43D52D91000071FC-de.v
    subid = get_subid(petframes[0])
    hdr = ecat.load(petframes[0]).get_header()
    scantime = datetime.datetime.fromtimestamp(int(hdr['scan_start_time']))
    petdate = scantime.strftime('-%Y-%m-%d-%H')
    petdir = tracer + petdate
    outdir = os.path.join(arda, subid, petdir)
    return outdir

def age_from_ecat(petframes):
    """ data in header is not robust, do not use this
    given list of frames
    gets dob, scantime to get age at scan
    hdr = ecat.load(petframes[0]).get_header()    
    """
    pass

def update_outdir(outdir, clobber=True):
    """ checks for outdir,
    if exists and clobber(default True), empties
    else creates
    """
    if os.path.isdir(outdir) and clobber:
        shutil.rmtree(outdir)
    if not os.path.isdir(outdir):
        os.makedirs(outdir) #in case multiple level dir
    

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

def get_reconnotes_fromsync(recondir, tracer):
    """given a recondir and tracer in LBLSYNC
    B96-349/fdg/recon/
    get corresponding reconnotes and return"""
    
    basepath, _ = recondir.split('/%s/'%tracer)    
    globstr = os.path.join(basepath, '%sreconnotes.txt'%(tracer))
    exists, reconf = glob_file(globstr)
    return exists, reconf

def get_real_tracer(recondir, subid):
    """ looks for fdg2, etc and returns real tracertype"""
    _, tmp = recondir.split('%s/'%subid)
    real_tracer, _ = tmp.split('/recon')
    return real_tracer
    
def gen_recon_fname(flist, destdir, tracer = ''):
    """given list of file names
    find the last mod date
    add tracer and moddate to filename
    """
    lastmod = datetime.datetime(1900,01, 01)
    for f in flist:
        mod = modification_date(f)
        if mod > lastmod:
            lastmod = mod
    lastmodtime = lastmod.strftime('%Y-%m-%d')
    outfname = '%sreconnotes_%s.txt'%(tracer, lastmodtime)
    return os.path.join(destdir, outfname)


def check_recon_notes(newnotes, orignotes):
    """
    check recon notes based on date-stamped names
    Returns
    -------
    copy: bool (true if need to copy, otherwise False
    """
    try:
        _, newname = os.path.split(newnotes)
        _, origname = os.path.split(orignotes)
        ## if dated filenames differ, copy new notes
        if not newname == origname:
            return True
        else:
            return False
    except:
        return True

    
def get_recons_from_sync(tracer, root):
    if tracer == 'fmt':
        globstr = os.path.join(root, 'B*/%s*/recon/4mm'%(tracer))
    else:
        globstr = os.path.join(root, 'B*/%s*/recon'%(tracer))
    recons = glob(globstr)
    recons.sort()
    return recons

if __name__ == '__main__':
    petfiles = ['/home/jagust/cindeem/LBLSYNC/finalPET/'\
                'B11-255/pib/recon/B11_255-43D52D91000071FC-de.v']
    subid = get_subid(petfiles[0])
    testing.assert_equal('B11-255', subid)
    outdir = make_outdirname(petfiles, tracer='PIB')
    expected = '/home/jagust/arda/lblid/B11-255/PIB-2011-06-15-14'
    testing.assert_equal(expected, outdir)
    md5digest = md5file(petfiles[0])
    testing.assert_equal('7636b13b4bd7ff645371804d9410f02a',md5digest)
    # test glob_file
    exists, pth = glob_file('*py')
    testing.assert_equal(False, exists)
    exists, pth = glob_file('*py', single=False)
    testing.assert_equal(True, exists)

    ## check filedates
    filelist = glob('/home/jagust/cindeem/LBLSYNC/finalPET/B11-243/fdg/recon/*.v')
    filelist.sort()
    original = glob('/home/jagust/arda/lblid/B11-243/FDG-May-3-2011-12/*.v')
    original.sort()
    same = check_dates(filelist, original)
    testing.assert_equal(True, same)
    # reconnotes
    reconnotes_new = '/home/jagust/cindeem/LBLSYNC/finalPET/B11-243/fdgreconnotes.txt'
    nexists, new = glob_file(reconnotes_new)
    orig_exists, orig = glob_file('/home/jagust/arda/lblid/B11-243/FDG-May-3-2011-12/*notes*.txt')
    recon_name_new = gen_recon_fname(filelist, '/home/jagust/arda/lblid/B11-243/FDG-May-3-2011-12', tracer='fdg')
    copy = check_recon_notes(recon_name_new, orig)

    ## getting data
    tracer = 'fdg'
    syncdir = '/home/jagust/cindeem/LBLSYNC/finalPET'
    recons = get_recons_from_sync(tracer, syncdir)
    
