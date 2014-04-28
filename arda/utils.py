import os
import logging


def find_single_file(searchstring):
    """ glob for single file using searchstring
    if found returns full file path """
    file = glob(searchstring)
    if len(file) < 1:
        print '%s not found' % searchstring
        return None
    else:
        outfile = file[0]
        return outfile

def make_rec_dir(base_dir, dirname='fdg_nifti'):
    """ makes a new directories recursively if it doesnt already exist
    returns full path

    Parameters
    ----------
    base_dir : str
    the root directory
    dirname  : str (default pib_nifti)
    new directory name

    Returns
    -------
    newdir  : str
    full path of new directory
    """
    newdir = os.path.join(base_dir,dirname)
    directory_exists = os.path.isdir(newdir)
    if not directory_exists:
        os.makedirs(newdir)
    return newdir, directory_exists

def get_logging_configdict(logfile):
    log_settings = {
            'version': 1,
            'root': {
                'level': 'NOTSET',
                'handlers': ['console', 'file'],
            },
            'handlers': {
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'detailed',
                    'filename': logfile,
                    'mode': 'w',
                    'maxBytes': 10485760,
                    },
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'detailed',
                    'stream': 'ext://sys.stdout',
            }},
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s %(module)-17s line:%(lineno)-4d ' \
                    '%(levelname)-8s %(message)s',
                    }
                }}
    return log_settings
