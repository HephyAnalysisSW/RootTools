''' Abstract Class for a looping over an instance of Sample.
'''
#Abstract Base Class
import abc

# Standard imports
import ROOT
import uuid
import os

# Logging
import logging
logger      = logging.getLogger(__name__)
#root_logger = logging.getLogger('RootTools')

# RootTools
from RootTools.core.LooperBase import LooperBase
from RootTools.core.LooperHelpers import createClassString
from RootTools.core.TreeVariable import TreeVariable, ScalarTreeVariable, VectorTreeVariable

class FlatTreeLooperBase( LooperBase, metaclass=abc.ABCMeta ):
    def __init__(self, variables):

        if not type(variables) == type([]):
            raise ValueError( "Argument 'variables' must be list. Got %r"%variables )

        self.variables = [v if isinstance(v, TreeVariable) else TreeVariable.fromString(v) for v in variables]

        # Keep track of uuids in order to clean up
        self.classUUIDs = []

        # directory where the class is compiled
        self.tmpDir = '/tmp/'

        self._eList = None

        super(FlatTreeLooperBase, self).__init__( )


    def makeClass(self, attr, variables, addVectorCounters, useSTDVectors = False):

        if not os.path.exists(self.tmpDir):
            logger.info("Creating %s directory for temporary files for class compilation.", self.tmpDir)
            os.path.makedirs(self.tmpDir)

        classUUID = str(uuid.uuid4()).replace('-','_')
        self.classUUIDs.append( classUUID )

        tmpFileName = os.path.join(self.tmpDir, classUUID+'.C')
        className = "Class_"+classUUID

        with open( tmpFileName, 'w' ) as f:
            logger.debug("Creating temporary file %s for class compilation.", tmpFileName)
            f.write(
                createClassString( variables = variables, useSTDVectors = useSTDVectors, addVectorCounters = addVectorCounters)
                .replace( "className", className )
            )

        # Compiling. A less dirty solution possible?
        logger.debug("Compiling file %s", tmpFileName)
        ROOT.gROOT.ProcessLine('.L %s'%tmpFileName )

        logger.debug("Importing class %s", className)
        exec( "from ROOT import %s" % className )

        logger.debug("Creating instance of class %s", className)
        setattr(self, attr, eval("%s()" % className) )

        ##FIXME: Doesn't work. Wanted to  clean up, except we're debugging (only root logger keeps track of level)
        #if root_logger.level > logging.DEBUG:
        #    self.cleanUpTempFiles()
        #    #logger.info( "Log-level is %i. Deleting temporary files in %s", level, self.tmpDir )
        #else:
        #    logger.debug( "Log-level is %i <= 'DEBUG'. NOT deleting temporary files in %s", root_logger.level, self.tmpDir )

        return self

    def cleanUpTempFiles(self):
        ''' Delete all temporary files.
        '''
        files = os.listdir(self.tmpDir)
        toBeDeleted = []
        for uuid in self.classUUIDs:
            for f in files:
                if uuid in f:
                    toBeDeleted.append(f)
        for f in toBeDeleted:
            filename = os.path.join(self.tmpDir, f)
            os.remove(filename)
            logger.debug( "Deleted temporary file %s"%filename )

