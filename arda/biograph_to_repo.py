# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, shutil
import sys, re
from glob import glob
import hashlib
import dicom
import datetime
import dateutil.parser as parser
import tempfile
import filecmp
import tarfile
from nipype.interfaces.base import CommandLine
import logging

# for testing
import numpy.testing as testing



def get_field_date(raw):
    """ reads a tgz file, searches for dicom, and returns
    SeriesDate field"""
    with tarfile.open(raw, "r:gz") as tar:
        for member in tar:
            if  not '._' in member.name or not member.name == 'raw':
                print member.name
                try:
                    tmpf = tar.extractfile(member)
                    #print tmpf
                    plan = dicom.read_file(tmpf)
                    date = plan.SeriesDate
                    return date
                except:
                    print member.name
                    date = None
                    continue
                    
    return date


def get_real_tracer(raw):
    pth, _ = os.path.split(raw)
    _, tracer = os.path.split(pth)
    return tracer


def make_dirname(date, tracer):
    """ given set of dates from dicoms
    generate outfile name
    """
    dt = parser.parse(date)
    date = dt.strftime('%Y-%m-%d')
    dirname = '_'.join([tracer.upper(),  date])
    return dirname


