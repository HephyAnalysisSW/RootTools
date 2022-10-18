''' MultiReader example: Loop over several samples in parallel.
'''
import logging
import ROOT

#RootTools
from RootTools.core.standard import *

# argParser
import argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--logLevel', 
      action='store',
      nargs='?',
      choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE', 'NOTSET'],
      default='INFO',
      help="Log level for logging"
)

args = argParser.parse_args()
logger = get_logger(args.logLevel, logFile = None)

# Two samples (from same file, but that makes no difference) 
s0 = Sample.fromFiles("s0", files = ["example_data/file_0.root"], treeName = "Events", selectionString = 'Jet_pt[0]>100')
s1 = Sample.fromFiles("s1", files = ["example_data/file_0.root"], treeName = "Events", selectionString = 'Jet_pt[0]>50')

variables =  list(map( TreeVariable.fromString, [ 'evt/l', 'run/I', 'lumi/I', 'Jet[pt/F,eta/F,phi/F]', 'met_pt/F', 'met_phi/F'] ))

# Make two readers
r1 = s0.treeReader( variables = variables, selectionString = "met_pt>100" )
r2 = s1.treeReader( variables = variables, selectionString = "met_pt>100" )

# define a key to align the events
key = lambda event: ( event.run, event.lumi, event.evt )

# Create MultiReader instance according to MultiReader( reader1, key1, reader2, key2, ... )
r = MultiReader( 
    ( r1, key ), 
    ( r2, key ) )

r.start()
while r.run():
    print(r.position, r1.event.evt, r2.event.evt)
    break
