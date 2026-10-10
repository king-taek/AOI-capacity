import sys, os, json, datetime as dt, re, statistics as st
WORK = os.environ.get('AOI_WORK') or sys.exit('set AOI_WORK')
A=os.path.join(WORK,'an3')
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt
from fam import family
