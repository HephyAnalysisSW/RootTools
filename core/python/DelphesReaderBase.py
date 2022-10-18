''' Base class for reading Delphes files.
'''

# Standard imports
import ROOT
import uuid
import os
import shutil
import abc
import inspect

# RootTools
from RootTools.core.LooperBase import LooperBase
from RootTools.core.Sample     import Sample

# Logging
import logging
logger = logging.getLogger(__name__)

class DelphesReaderBase( LooperBase, metaclass=abc.ABCMeta ):
    def __init__( self, sample,  selectionString = None, sequence = []):
        ''' Return an instance of a MakeClass object
        '''

        if not isinstance(sample, Sample):
            raise ValueError( "Need instance of Sample to initialize any Looper instance. Got %r."%sample )
        self.sample = sample

        # Make Delphes reader from first file
        self.tmpdir_delphes = "/tmp/"
        self.tmpname_delphes = "Delphes_"+uuid.uuid4().hex
        first_file = ROOT.TFile(self.sample.files[0])
        tree = first_file.Get("Delphes")
        tree.MakeClass( self.tmpname_delphes )

        self.tmp_filenames = [ "%s.C"%self.tmpname_delphes, "%s.h"%self.tmpname_delphes ]

        # move files to tmp area
        for file in self.tmp_filenames:
            shutil.move( file, os.path.join( self.tmpdir_delphes, file ) )
        # load the newly created files as macro
        ROOT.gROOT.LoadMacro( os.path.join( self.tmpdir_delphes, self.tmpname_delphes+'.C' ) )
        # make instance
        self.event = getattr(ROOT, "%s" % self.tmpname_delphes )( self.sample.chain )

        if selectionString is not None and not type(selectionString) == type(""):
            raise ValueError( "Don't know what to do with selectionString %r"%selectionString )
        # Selection string to be applied to the chain
        self.selectionString = selectionString

        logger.debug("Initializing TreeReader for sample %s", self.sample.name)
        self._eList = self.sample.getEventList(selectionString = self.selectionString)
        #  default event range of the reader
        self.nEvents = self._eList.GetN() if  self._eList else self.sample.chain.GetEntries()
        logger.debug("Found %i events in  %s", self.nEvents, self.sample.name)
        self.eventRange = (0, self.nEvents)

        # Sequence of precomputed attributes for event
        for i, s in enumerate(sequence):
            if not (hasattr(s, '__call__') and len( inspect.getargspec( s ).args )<=2):
                raise ValueError( "Element %i in sequence is not a function with less than two arguments." % i )
        self.sequence = sequence


    # Clean up the tmp files
    def __del__(self):
       for file in self.tmp_filenames:
           filename = os.path.join( self.tmpdir_delphes, file ) 
           if os.path.exists( filename ):
                os.remove( filename )
 
    # Read a vector collection from the Delphes event
    def read_collection( self, collection, variables ):
        ''' read delphes collection and rename leaves'''
        nColl   = getattr( self.event, collection+"_size" )
        buffers = {var_old: getattr( self.event, collection+'_'+var_old) for var_old, var_new in variables}
        return [{var_new:buffers[var_old][i] for var_old, var_new in variables} for i in range(nColl)]
    
    def getEventRanges(self, maxFileSizeMB = None, maxNEvents = None, nJobs = None, minJobs = None):
        '''For convinience: Define splitting of sample according to various criteria
        '''
        if maxFileSizeMB is not None:
            nSplit = sum( os.path.getsize(f) for f in self.sample.files ) // ( 1024**2*maxFileSizeMB )
        elif maxNEvents is not None:
            nSplit = self.nEvents // maxNEvents 
        elif nJobs is not None:
            nSplit = nJobs
        else:
            nSplit = 0
        if minJobs is not None and nSplit < minJobs: 
            nSplit = minJobs
        if nSplit==0:
            logger.debug( "Returning full event range because no splitting is specified" )
            return [(0, self.nEvents)]
        thresholds = [i*self.nEvents//nSplit for i in range(nSplit)]+[self.nEvents]
        return [(thresholds[i], thresholds[i+1]) for i in range(len(thresholds)-1)]

    def setEventRange( self, evtRange ):
        ''' Specify an event range that the reader will run over. 
            Bounded by (0, nEvents).
        '''
        old_eventRange = self.eventRange
        self.eventRange = ( max(0, evtRange[0]), min( self.nEvents, evtRange[1]) )
        logger.debug( "[setEventRange] Set eventRange %r (was: %r) for reader of sample %s", self.eventRange, old_eventRange, self.sample.name )

    def _initialize(self):
        ''' This method is called from the Base class start method.
            Initializes the reader, sets position to lower event range.
        '''
        # set to the first position, either 0 or the lower eventRange deliminator
        self.position = self.eventRange[0]

        # Check if we need to run a sequence for our sample. 
        self.__sequence = self.sequence + self.sample.sequence if hasattr(self.sample, "sequence") else self.sequence

        return

    def _execute(self):
        ''' Does what a reader should do: 'GetEntry' into the event struct.
            Returns 0 if upper eventRange is hit. 
        '''

        if self.position == self.eventRange[1]: return 0
        if self.position==0:
            logger.info("TreeReader for sample %s starting at position %i (max: %i events).",
                self.sample.name, self.position, self.nEvents)
        elif (self.position % 10000)==0:
            logger.info("TreeReader for sample %s is at position %6i/%6i",
                self.sample.name, self.position, self.nEvents )

        # get entry 
        errorLevel = ROOT.gErrorIgnoreLevel
        ROOT.gErrorIgnoreLevel = 3000
        self.event.GetEntry ( self._eList.GetEntry( self.position ) ) if self._eList else self.event.GetEntry( self.position )
        ROOT.gErrorIgnoreLevel = errorLevel

        # sequence
        for func in self.__sequence:
            func ( event = self.event, sample = self.sample )

        return 1

    def goToPosition(self, position):
        self.position = position
        self._execute()

    # Example
    #def met( self ):
    #    return self.read_collection( 'PuppiMissingET', [('MET', 'pt'), ('Phi', 'phi')] )

