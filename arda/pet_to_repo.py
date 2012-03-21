import sys, os, re
import shutil
import datetime
sys.path.insert(0,'/home/jagust/cindeem/tmpgit/cindeem-nibabel')
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

Find all possible tracer directories
open first file and check date
check if pet directory exists on arda
if not, 
   create new dated PET dir <TRACER>_date_time
   copy relevant files

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
    petdate = scantime.strftime('-%Y-%b-%d-%H')
    petdir = tracer + petdate
    outdir = os.path.join(arda, subid, petdir)
    return outdir


def update_outdir(outdir, clobber=True):
    """ checks for outdir,
    if exists and clobber(default True), empties
    else creates
    """
    if os.path.isdir(outdir) and clobber:
        shutil.unlink(outdir)
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
    if len(result) < 1:
        return False, None
    if len(result) == 1:
        return True, result[0]
    if single:
        # expecting only one file, otherwise assume bad
        return False, None
    else:
        # expect more than one, get files
        return True, result


def gen_recon_fname(dict, tracer=''):
    """given a dict of json names
    find the last mod date
    add tracer and moddate to filename
    """
    lastmod = 0
    for f in dict.keys():
        st = os.stat(f)
        if st.st_mtime > lastmod:
            lastmod = st.st_mtime
    lastmodtime = ctime(lastmod).replace(' ','_').replace(':','-')
    outfname = '%sreconnotes_%s.txt'%(tracer, lastmodtime)
    return outfname

## TODO  shold check date of pet files, or check date of
## recon notes or both
def check_recon_notes():
    """ Checks for existence, or change in recon notes
    1. check for recon notes file in rsync 
    2. check if exists in arda repo (if not just copy)
    3. if both files, check equality, updates if new
    """
    pass

if __name__ == '__main__':
    petfiles = ['/home/jagust/cindeem/LBLSYNC/finalPET/finalPET/'\
                'B11-255/pib/recon/B11_255-43D52D91000071FC-de.v']
    outdir = make_outdirname(petfiles, tracer='PIB')
    expected = '/home/jagust/arda/lblid/B11-255/PIB-2011-Jun-15-14'
    testing.assert_equal(expected, outdir)
    md5digest = md5file(petfiles[0])
    testing.assert_equal('7636b13b4bd7ff645371804d9410f02a',md5digest)
    # test glob_file
    exists, pth = glob_file('arda/*py')
    testing.assert_equal(False, exists)
    exists, pth = glob_file('arda/*py', single=False)
    testing.assert_equal(True, exists)
