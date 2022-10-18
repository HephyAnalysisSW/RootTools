''' FWLiteReader example: Loop over a sample and write some data to a histogram.
'''
# Standard imports
import os
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

## 8X mAOD, assumes eos mount in home directory 
## from Directory
#dirname = "~/eos/cms/store/relval/CMSSW_8_0_0_pre6/JetHT/MINIAOD/80X_dataRun2_v4_RelVal_jetHT2015HLHT-v1/10000/" 
#s0 = FWLiteSample.fromDirectory("jetHT", directory = os.path.expanduser(dirname) )
## from files
#filename = "~/eos/cms/store/relval/CMSSW_8_0_0_pre6/JetHT/MINIAOD/80X_dataRun2_v4_RelVal_jetHT2015HLHT-v1/10000/02EF6290-71D6-E511-AF4F-0025905B858A.root"
#s1 = FWLiteSample.fromFiles("test", files = os.path.expanduser(filename) )

## from DAS
s2 = FWLiteSample.fromDAS("hltPhysics", "/HLTPhysics/CMSSW_7_4_14-2015_10_20_reference_74X_dataRun2_HLT_v2-v1/RECO", instance = 'global', prefix='root://xrootd.unl.edu/', maxN = 1)

products = {
#    'slimmedJets':{'type':'vector<pat::Jet>', 'label':("slimmedJets", "", "reRECO")} 
'pfJets':{'type':'vector<reco::PFJet>', 'label':( "ak4PFJets" ) }
    }

r = s2.fwliteReader( products = products )

h=ROOT.TH1F('met','met',100,0,0)
r.start()

runs = set()
while r.run():
    runs.add(r.evt[0])
    print(r.event.evt, r.event.lumi, r.event.run, "Number of pfJets", r.event.pfJets.size())

logger.info( "Found the following run(s): %s", ",".join(str(run) for run in runs) )

