''' Class for a making a new tree based in a TChain in a Sample.
'''

# Standard imports
import ROOT
import copy

# Logging
import logging
logger = logging.getLogger(__name__)

# RootTools
from RootTools.core.FlatTreeLooperBase import FlatTreeLooperBase
from RootTools.core.TreeVariable import ScalarTreeVariable, VectorTreeVariable, TreeVariable
class TreeMaker( FlatTreeLooperBase ):

    def __init__(self, variables, sequence = [], treeName = "Events"):
        
        super(TreeMaker, self).__init__( variables = variables)

        self.makeClass( "event", variables = variables, useSTDVectors = False, addVectorCounters = True)

        # Create tree to store the information and store also the branches
        self.treeIsExternal = False
        self.tree = ROOT.TTree( treeName, treeName )
        self.branches = []
        self.makeBranches()

        # function to fill the event 
        self.sequence = sequence

    def debugBranchAddresses( self, prefix = ""):
        ''' If strings are empty, there is an issue with memory. Only for debugging purposes.
        '''
        for b in self.branches:
            print prefix, b.GetName(), repr(b.GetAddress())

    def cloneWithoutCompile(self, externalTree = None):
        ''' make a deep copy of self to e.g. avoid re-compilation of class in a loop. 
            Reset TTree as to not create a memory leak.
        '''
        # deep copy by default
        res = copy.deepcopy(self)
        res.branches = []

        # remake TTree
        treeName = self.tree.GetName()
        if res.tree: res.tree.IsA().Destructor( res.tree )
        if externalTree:
            res.treeIsExternal = True
            assert self.tree.GetName() == externalTree.GetName(),\
                "Treename inconsistency (instance: %s, externalTree: %s). Change one of the two"%(treeName, externalTree.GetName())
            res.tree = externalTree
        else:
            res.treeIsExternal = False
            res.tree = ROOT.TTree( treeName, treeName )

        res.makeBranches()
        #self.debugBranchAddresses(prefix = "cloneWithoutCompile")

        return res

    def makeBranches(self):

        scalerCount = 0
        vectorCount = 0
        addressof = ROOT.addressof if  ROOT.gROOT.GetVersion()>="6.22" else ROOT.AddressOf
        for s in self.variables:
            if isinstance(s, ScalarTreeVariable):
                self.branches.append( 
                    self.tree.Branch(s.name, addressof( self.event, s.name), '%s/%s'%(s.name, s.type))
                )
                scalerCount+=1
            elif isinstance(s, VectorTreeVariable):
                # first add counter counter
                counter = s.counterVariable()
                self.branches.append( 
                    self.tree.Branch(counter.name, addressof( self.event, counter.name ), '%s/%s'%(counter.name, counter.type))
                )
                # then add vector components
                for comp in s.components:
                    self.branches.append(
                        self.tree.Branch(comp.name, addressof( self.event, comp.name ), "%s[%s]/%s"%(comp.name, counter.name, comp.type) )
                    )
                vectorCount+=1
            else:
                raise ValueError( "Don't know what variable %r is." % s )
        #self.debugBranchAddresses(prefix = "makeBranches")
        logger.debug( "TreeMaker created %i new scalars and %i new vectors.", scalerCount, vectorCount )

    def clear(self):
        if self.tree: self.tree.IsA().Destructor( self.tree )

    def fill(self):
        # Write to TTree
        #self.debugBranchAddresses( prefix = "Filling")
        if self.treeIsExternal:
            for b in self.branches:
                b.Fill()
        else:
            self.tree.Fill()

    def _initialize(self):
        self.position = 0
        # Initialize struct
        self.event.init()
        pass

    def _execute(self):
        ''' Use sequence to fill struct and then fill struct to tree'''

        if (self.position % 10000)==0:
            logger.info("TreeMaker is at position %6i", self.position)

        for func in self.sequence:
            func( event = self.event )

        self.fill()

        # Initialize struct
        self.event.init()
 
        return 1 
