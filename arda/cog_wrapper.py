# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import sys, os
from glob import glob
import argparse
sys.path.insert(0, '/home/jagust/cindeem/CODE/ARDA/ardatools/arda')
import cog_to_arda as ca


if __name__ == '__main__':

    # create the parser
    parser = argparse.ArgumentParser(
        description='Put cognitive data into arda')

    # add the arguments
    parser.add_argument(
        'infile', type=str, nargs=1,
        help='Input Session Filename')

    parser.add_argument(
        '-sess', type=int,
        default=0, 
        help='Session Number')
        
    if len(sys.argv) ==1:
        parser.print_help()
    else:
        args = parser.parse_args()
        print args.sess, args.infile
        ca.main(args.infile[0], args.sess)
