import sys
import os
sys.path.insert(0,'/home/jagust/cindeem/src/pynifti-git')
import nifti.ecat as ecat
from glob import glob
from time import ctime
import hashlib
import filecmp
import json


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
        
