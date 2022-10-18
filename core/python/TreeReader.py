''' Class for a TreeReader of an instance of Sample.
'''

# Standard imports
import ROOT
import os
import inspect

# Logging
import logging
logger = logging.getLogger(__name__)

# RootTools
from RootTools.core.FlatTreeLooperBase import FlatTreeLooperBase
from RootTools.core.Sample import Sample
import RootTools.core.helpers as helpers
from RootTools.core.TreeVariable import TreeVariable, ScalarTreeVariable, VectorTreeVariable
from RootTools.core.helpers import shortTypeDict

class TreeReader( FlatTreeLooperBase ):

    def __init__(self, sample, variables=[], sequence = [], selectionString = None, allBranchesActive = False, ttreeFormulas = None):

        # The following checks are 'look before you leap' but I rather have the user know if the input is non-sensical
        if not isinstance(sample, Sample):
            raise ValueError( "Need instance of Sample to initialize any Looper instance. Got %r."%sample )
        if not type(variables) == type([]):
            raise ValueError( "Argument 'variables' must be list. Got %r."%variables )
        if selectionString is not None and not type(selectionString) == type(""):
            raise ValueError( "Don't know what to do with selectionString %r"%selectionString )
        # Selection string to be applied to the chain
        self.selectionString = selectionString

        self.ttreeFormulas = None
        if ttreeFormulas is not None and type(ttreeFormulas)!=type({}):
            raise ValueError( "Argument 'ttreeFormulas' is not a dictionary. Should be {'name1':'formula1', 'name2':'formula2', ...}" )
        else: 
            self.ttreeFormulas = ttreeFormulas

        # Sequence of precomputed attributes for event
        for i, s in enumerate(sequence):
            if not (hasattr(s, '__call__') and len( inspect.getargspec( s ).args )<=2):
                raise ValueError( "Element %i in sequence is not a function with less than two arguments." % i )
        self.sequence = sequence

        self.sample = sample

        # Whether all branches are to be read or whether that information should come from the variables
        self.allBranchesActive = allBranchesActive

        ## Read branch information from the chain -> Will be useful when using auto-type
        #self.readLeafInfo()

        # 'variables' are read from the chain
        super(TreeReader, self).__init__( variables = list(set(variables)) ) 

        for s in list(self.variables):
            logger.debug( "Making class with variable %s" %s)

        # make class
        self.makeClass( "event", list(self.variables), useSTDVectors = False, addVectorCounters = False)

        # set the addresses of the branches corresponding to 'variables'
        self.setAddresses()

        # make eList from cutString
        # Turn on everything for flexibility with the selectionString
        logger.debug("Initializing TreeReader for sample %s", self.sample.name)
        self.activateAllBranches()
        self._eList = self.sample.getEventList(selectionString = self.selectionString)
        self.activateBranches()
        self.nEvents = self._eList.GetN() if  self._eList else self.sample.chain.GetEntries()
        logger.debug("Found %i events in  %s", self.nEvents, self.sample.name)

        #  default event range of the reader
        self.eventRange = (0, self.nEvents)

    def setAddresses(self):
        ''' Set all the branch addresses to the members in the class instance
        '''
        #for s in LooperBase._branchInfo(self.variables, addVectorCounters = False):
        if ROOT.gROOT.GetVersion()>='6.22':
            from cppyy.ll import cast
            for s in self.variables:
                if isinstance(s, ScalarTreeVariable ):
                    self.sample.chain.SetBranchAddress(s.name, cast['void*'](ROOT.addressof(self.event, s.name )) )
                elif isinstance(s, VectorTreeVariable ):
                    for comp in s.components:
                        try:
                            self.sample.chain.SetBranchAddress(comp.name, cast['void*'](ROOT.addressof(self.event, comp.name )))
                        except TypeError as e:
                            print("Problem with: %s"%comp.name)
                            raise e
                else:
                    raise ValueError( "Don't know what variable %r is." % s )
        else:
            for s in self.variables:
                if isinstance(s, ScalarTreeVariable ):
                    self.sample.chain.SetBranchAddress(s.name, ROOT.AddressOf(self.event, s.name ))
                elif isinstance(s, VectorTreeVariable ):
                    for comp in s.components:
                        self.sample.chain.SetBranchAddress(comp.name, ROOT.AddressOf(self.event, comp.name ))
                else:
                    raise ValueError( "Don't know what variable %r is." % s )
 
    def cloneTree(self, branchList = [], newTreename = None, rootfile = None):
        '''Clone tree after preselection and event range
        '''
        selectionString = self.selectionString if self.selectionString is not None else "1"
        if self._eList:
            # If there is an eList, first restrict it to the event range, then clone
            import uuid
            name = str(uuid.uuid4())
            list_to_copy = ROOT.TEventList("tmp","tmp")
            for i_ev in range(*self.eventRange):
                list_to_copy.Enter(self._eList.GetEntry(i_ev))

            self.sample.chain.GetEntry(list_to_copy.GetEntry(0)) #This is needed to keep branch addresses when running over a few events and >=1 file

            # activate branches that we want to copy, disable the ones we only need for reading
            self.activateBranches( turnOnReadBranches = False, branchList = branchList )

            # Copy only the selected events

            # Create the new tree in a file (if there is one)
            tmp_directory = ROOT.gDirectory
            if rootfile is not None: 
                logger.debug( "cd to file %r", rootfile )
                rootfile.cd() 

            # Copying tree

            logger.debug("Copying %i events in a loop.", list_to_copy.GetN())
            res = self.sample.chain.GetTree().CloneTree( 0 )
            for i_event in range(list_to_copy.GetN()):
                self.sample.chain.GetEntry( list_to_copy.GetEntry(i_event) )
                res.Fill()

            res.Write()

            logger.debug("Number of events: list_to_copy %i res.GetEntries() %i", list_to_copy.GetN(), res.GetEntries())

            # Change back to previous gDirectory
            tmp_directory.cd()

            # activate what we read, don't activate the ones we just copied
            self.activateBranches( turnOnReadBranches = True, branchList = [] )

            list_to_copy.Delete()

            if newTreename is not None: res.SetName( newTreename )

            return res 

        else:

            tmp_directory = ROOT.gDirectory
            if rootfile is not None: 
                logger.debug( "cd to file %r", rootfile )
                rootfile.cd() 

            res = self.sample.chain.CopyTree( selectionString, "", self.eventRange[1] - self.eventRange[0], self.eventRange[0] )
            # Change back to previous gDirectory
            tmp_directory.cd()

            return res

    def activateBranches(self, turnOnReadBranches = True, branchList = []):
        ''' Set status of all needed branches in sample chain to '1' 
        '''
        self.sample.chain.SetBranchStatus("*", 0)
        if turnOnReadBranches:
            #Turn on all branches?
            if self.allBranchesActive:
                self.activateAllBranches()
                return

            # Turn on all branches
            for s in self.variables:
                if isinstance(s, ScalarTreeVariable ):
                    self.sample.chain.SetBranchStatus(s.name, 1)
                elif isinstance(s, VectorTreeVariable ):
                    for comp in s.components:
                        self.sample.chain.SetBranchStatus(comp.name, 1)

        for b in branchList:
            self.sample.chain.SetBranchStatus(b, 1)

    def activateAllBranches(self):
        '''Set status of all branches in the sample chain to 1
        '''
        self.sample.chain.SetBranchStatus("*", 1)

#    def readLeafInfo(self):
#        ''' Read information on the leaves from the chain and store in dict
#            FIXME: Pretty sure this doesn't yet work for fixed sized vectors
#        '''
#        leafInfo = []
#        for s in self.sample.chain.GetListOfLeaves():
#            leaf = {'type':shortTypeDict[s.GetTypeName()], 'name':s.GetName()}
#            countval = array.array('i',[-9999])
#            pointer = s.GetLeafCounter(countval)
#            leaf['dim'] = 'scalar'
#            if pointer:
#                # Vector
#                # GetLeafCounter returns countval==1 if a counter leaf was found and pointer points to that leaf
#                # https://root.cern.ch/doc/master/classTLeaf.html#a062bd89a11fd1f922c096e66d2601ab6
#                if countval[0]==1:
#                    leaf['counterInt'] = pointer.GetName()
#                leaf['dim'] = 'vector'
#            else:
#                # For fixed size arrays, the pointer is zero and the countval is the size of the array
#                leaf['nMax'] = countval[0]
#            leafInfo.append(leaf)
#        return leafInfo

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
    
    #def reduceEventRange( self, reduction_factor ):
    #    ''' Reduce event range by a given factor. 
    #    '''
    #    old_eventRange = self.eventRange if hasattr(self, "eventRange") else None
    #    self.eventRange = ( self.eventRange[0], self.eventRange[0] + (self.eventRange[1] - self.eventRange[0])/reduction_factor ) 
    #    logger.debug( "[reduceEventRange] Set new eventRange %r (was: %r) for reader of sample %s", self.eventRange, old_eventRange, self.sample.name )

    def _initialize(self):
        ''' This method is called from the Base class start method.
            Initializes the reader, sets position to lower event range.
        '''
        # set to the first position, either 0 or the lower eventRange deliminator
        self.position = self.eventRange[0]

        # Check if we need to run a sequence for our sample. 
        self.__sequence = self.sequence + self.sample.sequence if hasattr(self.sample, "sequence") else self.sequence

        # Book TTreeFormula objects if needed

        self.__ttreeFormulas = None
        if self.ttreeFormulas is not None:
            self.__ttreeFormulas = {}
            for i_name, (name, formula) in enumerate( self.ttreeFormulas.items() ):
                logger.debug( "Create  %s <- ROOT.TTreeFormula('TTF_%i', '%s', chain" % (name, i_name, formula) )
                self.__ttreeFormulas[name] = ROOT.TTreeFormula("TTF_%i"%i_name, formula, self.sample.chain)

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

        # init struct
        self.event.init()

        # get entry 
        errorLevel = ROOT.gErrorIgnoreLevel
        ROOT.gErrorIgnoreLevel = 3000
        self.sample.chain.GetEntry ( self._eList.GetEntry( self.position ) ) if self._eList else self.sample.chain.GetEntry( self.position )
        ROOT.gErrorIgnoreLevel = errorLevel

        # sequence
        for func in self.__sequence:
            func ( event = self.event, sample = self.sample ) 

        # TTreeFormulas
        if self.__ttreeFormulas is not None:
            
            if (not hasattr( self, "last_tchain_filename")) or self.sample.chain.GetCurrentFile().GetName() != self.last_tchain_filename:
                to_be_updated = True
                self.last_tchain_filename = self.sample.chain.GetCurrentFile().GetName()
            else:
                to_be_updated = False
                
            for name, formula in list(self.__ttreeFormulas.items()):
                if to_be_updated:
                    formula.UpdateFormulaLeaves()
                    logger.debug( "Updating TTreeFormulas to new file in TChain: %s", self.last_tchain_filename )
                setattr( self.event, name, formula.EvalInstance() )

        return 1

    def goToPosition(self, position):
        self.position = position
        self._execute()
