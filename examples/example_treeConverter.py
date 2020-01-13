'''Combining a TreeReader and a TreeMaker, a simple converter is built 
that splits an input sample into chunks of given size and stores the result in new ROOT files.
'''

# Standard imports
import ROOT
import sys
import logging
import os

#RootTools
from RootTools.core.standard import *
from RootTools.plot.Immutable import Immutable

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
logger = get_logger(args.logLevel, None)

# from files
s0 = Sample.fromFiles("s0", files = [os.path.expandvars("$CMSSW_BASE/src/RootTools/examples/example_data/file_0.root")], treeName = "Events")

read_variables =  [ TreeVariable.fromString( "nJet/I"), TreeVariable.fromString('Jet[pt/F,eta/F,phi/F]' ) ] \
                + [ TreeVariable.fromString(x) for x in [ 'met_pt/F', 'met_phi/F' ] ]

new_variables =     [ TreeVariable.fromString('MyJet[pt2/F]' ) ] \
                  + [ TreeVariable.fromString(x) for x in [ 'myMetOver2/F' ] ]

outputfilename = "./converted.root"


branches_to_keep = [ "met_phi" ]

# Define a reader
reader = s0.treeReader( variables = read_variables, selectionString = "(met_pt>100)")

# A simple eample
def filler(event):
    event.nMyJet = reader.event.nJet
    for i in range(reader.event.nJet):
        event.MyJet_pt2[i] = reader.event.Jet_pt[i]**2
    event.myMetOver2 = reader.event.met_pt/2.

    return

# Create a maker. Maker class will be compiled. This instance will be used as a parent in the loop
treeMaker_parent = TreeMaker( sequence = [filler], variables = new_variables , treeName = "newTree")

# Split input in ranges
eventRanges = reader.getEventRanges( maxFileSizeMB = 30)
logger.info( "Splitting into %i ranges of %i events on average.",  len(eventRanges), (eventRanges[-1][1] - eventRanges[0][0])/len(eventRanges) )

convertedEvents = 0
clonedEvents = 0

for ievtRange, eventRange in enumerate(eventRanges):

    logger.info( "Now at range %i which has %i events.",  ievtRange, eventRange[1]-eventRange[0] )

    tmp_directory = ROOT.gDirectory
    filename, ext = os.path.splitext( outputfilename )
    outputfile = ROOT.TFile.Open(filename+'_'+str(ievtRange)+ext, 'recreate')
    tmp_directory.cd()

    # Set the reader to the event range
    reader.setEventRange( eventRange )
    clonedTree = reader.cloneTree( branches_to_keep, rootfile = outputfile )
    clonedTree.SetName( "newTree" )
    clonedEvents += clonedTree.GetEntries()

    # Clone the empty maker in order to avoid recompilation at every loop iteration
    maker = treeMaker_parent.cloneWithoutCompile( externalTree = clonedTree )
    maker.start()

    # Do the thing
    reader.start()
    while reader.run():
        maker.run()

    convertedEvents += maker.tree.GetEntries()

#    # Writing to file
    maker.tree.Write()

    outputfile.Close()
    # Destroy the TTree
    maker.clear()

logger.info( "Converted %i events of %i, cloned %i",  convertedEvents, reader.nEvents , clonedEvents)
