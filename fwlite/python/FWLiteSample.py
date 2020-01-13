''' FWLite Sample class.
    Implements definition and handling of the TChain.
'''

# Standard imports
import ROOT
import os

#FWLite and CMSSW tools
from PhysicsTools.PythonAnalysis import *

# Logging
import logging
logger = logging.getLogger(__name__)

# RootTools imports
import RootTools.core.helpers as helpers
from RootTools.fwlite.Database import Database

@helpers.static_vars(sampleCounter = 0)
def newName():
    result = "FWLiteSample_"+str(newName.sampleCounter)
    newName.sampleCounter += 1
    return result

class FWLiteSample ( object ): 

    def __init__(self, name, files = [],  color = 0, texName = None):
        ''' Base class constructor for all sample classes.
            'name': Name of the sample, 
            'color': ROOT color to be used in plot scripts
            'texName': ROOT TeX string to be used in legends etc.
        '''

        self.name  = name
        self.files = files

        if not len(self.files)>0:
           raise helpers.EmptySampleError( "No ROOT files for sample %s! Files: %s" % (self.name, self.files) )
 
        self.color = color
        self.texName = texName if not texName is None else name
             
        logger.debug("Created new sample %s with %i files.", name, len(self.files))

    @classmethod
    def fromFiles(cls, name, files,  color = 0, texName = None, maxN = None):
        '''Load sample from files or list of files. If the name is "", enumerate the sample
        '''

        # Work with files and list of files
        files = [files] if type(files)==type("") else files

        # restrict files 
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        # If no name, enumerate them.
        if not name: name = newName()

        sample =  cls(name = name, files = files, color = color, texName = texName)
        return sample

    @classmethod
    def fromDirectory(cls, name, directory, color = 0, texName = None, maxN = None):
        '''Load sample from directory or list of directories. If the name is "", enumerate the sample
        '''
        # Work with directories and list of directories
        directories = [directory] if type(directory)==type("") else directory 

        # If no name, enumerate them.
        if not name: name = newName()

        # find all files
        files = [] 
        for d in directories:
            fileNames = [ os.path.join(d, f) for f in os.listdir(d) if f.endswith('.root') ]
            if len(fileNames) == 0:
                raise helpers.EmptySampleError( "No root files found in directory %s." %d )
            files.extend( fileNames )

        # restrict files 
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        return cls(name = name, files = files, color=color, texName = texName)

    @classmethod
    def fromDPMDirectory(cls, name, directory, prefix='root://hephyse.oeaw.ac.at/', texName = None, maxN = None, dbFile=None, overwrite=False, skipCheck = False):

        maxN = maxN if maxN is not None and maxN>0 else None
        limit = maxN if maxN else 0

        n_cache_files = 0 
        # Don't use the cache on partial queries
        if dbFile is not None and ( maxN<0 or maxN is None ):
            cache = Database(dbFile, "fileCache", ["name"]) 
            n_cache_files = cache.contains({'name':name})
        else:
            cache = None

        if n_cache_files and not overwrite:
            files = [ f["value"] for f in cache.getDicts({'name':name}) ]
            logger.info('Found sample %s in cache %s, return %i files.', name, dbFile, len(files))
        else:
            if overwrite:
                cache.removeObjects({"name":name})

            def _dasPopen(dbs):
                if 'LSB_JOBID' in os.environ:
                    raise RuntimeError, "Trying to do a DAS query while in a LXBatch job (env variable LSB_JOBID defined)\nquery was: %s" % dbs
                logger.info('DAS query\t: %s',  dbs)
                return os.popen(dbs)

            files = []
            dbs='xrdfs %s ls %s'%(prefix,directory)
            dbsOut = _dasPopen(dbs).readlines()
            
            for line in dbsOut:
                if line.startswith('/store/'):
                    line = line.rstrip()
                    filename = line
                    try:
                        if skipCheck or helpers.checkRootFile(prefix+filename):
                            files.append(filename)
                    except IOError:
                        logger.warning( "IOError for file %s. Skipping.", filename )

                    if cache is not None:
                        cache.add({"name":name}, filename, save=True)

        if limit>0: files=files[:limit]

        result = cls(name, files=[prefix+file for file in files], texName = texName)
        result.DASname = prefix + directory.rstrip("/")
        return result


    @classmethod
    def fromDAS(cls, name, dataset, instance = 'global', prefix='root://cms-xrd-global.cern.ch/', texName = None, maxN = None, dbFile=None, overwrite=False, skipCheck = False):
        ''' Make sample from DAS. 
        '''
        # https://github.com/CERN-PH-CMG/cmg-cmssw/blob/0f1d3bf62e7ec91c2e249af1555644b7f414ab50/CMGTools/Production/python/dataset.py#L437

        maxN = maxN if maxN is not None and maxN>0 else None
        limit = maxN if maxN else 0
        DASname = dataset.rstrip('/')

        n_cache_files = 0 
        # Don't use the cache on partial queries
        if dbFile is not None and ( maxN<0 or maxN is None ):
            cache = Database(dbFile, "fileCache", ["name"]) 
            n_cache_files = cache.contains({'name':name})
        else:
            cache = None

        if n_cache_files and not overwrite:
            files = [ f["value"] for f in cache.getDicts({'name':name}) ]
            logger.info('Found sample %s in cache %s, return %i files.', name, dbFile, len(files))
        else:
#            def _dasPopen(dbs):
#                if 'LSB_JOBID' in os.environ:
#                    raise RuntimeError, "Trying to do a DAS query while in a LXBatch job (env variable LSB_JOBID defined)\nquery was: %s" % dbs
#                if 'X509_USER_PROXY' in os.environ:
#                    dbs += " --key {0} --cert {0}".format(os.environ['X509_USER_PROXY'])
#                logger.info('DAS query\t: %s',  dbs)
#                return os.popen(dbs)
#
#            sampleName = dataset.rstrip('/')
#            query, qwhat = sampleName, "dataset"
#            if "#" in sampleName: qwhat = "block"
#
#            dbs='das_client --query="file %s=%s instance=prod/%s" --limit %i'%(qwhat,query, instance, limit)
#            dbsOut = _dasPopen(dbs).readlines()
            
            if overwrite:
                cache.removeObjects({"name":name})

            def _dasPopen(dbs):
                if 'LSB_JOBID' in os.environ:
                    raise RuntimeError, "Trying to do a DAS query while in a LXBatch job (env variable LSB_JOBID defined)\nquery was: %s" % dbs
                logger.info('DAS query\t: %s',  dbs)
                return os.popen(dbs)

            query, qwhat = DASname, "dataset"
            if "#" in DASname: qwhat = "block"

            dbs='dasgoclient -query="file %s=%s instance=prod/%s" --limit %i'%(qwhat,query, instance, limit)
            dbsOut = _dasPopen(dbs).readlines()
            
            files = []
            for line in dbsOut:
                if line.startswith('/store/'):
                    line = line.rstrip()
                    filename = line
                    try:
                        if skipCheck or helpers.checkRootFile(prefix+filename):
                            files.append(filename)
                    except IOError:
                        logger.warning( "IOError for file %s. Skipping.", filename )

                    if cache is not None:
                        cache.add({"name":name}, filename, save=True)

        if limit>0: files=files[:limit]

        result = cls(name, files=[prefix+file for file in files], texName = texName)
        result.DASname = DASname
        return result

    @classmethod
    def combine(cls, name, samples, texName = None, maxN = None, color = 0):
        '''Make new sample from a list of samples.
        '''
        if not (type(samples) in [type([]), type(())]) or len(samples)<1:
            raise ValueError( "Need non-empty list of samples. Got %r"% samples)

        files = sum([s.files for s in samples], [])
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        return cls(name = name, \
                   files = files,
                   color = color, 
                   texName = texName
            )

    def split( self, n, nSub = None):
        ''' Split sample into n sub-samples
        '''

        if n==1: return self

        if not n>=1:
            raise ValueError( "Can not split into: '%r'" % n )
       
        chunks = helpers.partition( self.files, min(n , len(self.files) ) ) 

        splitSamps = [ FWLiteSample( 
                name            = self.name+"_%i" % n_sample, 
                files           = chunks[n_sample], 
                color           = self.color, 
                texName         = self.texName ) for n_sample in xrange(len(chunks)) ]

        if nSub == None:
            return splitSamps
        else:
            if nSub<len(chunks):
                return splitSamps[nSub]
            else:
                return None

    def fwliteReader(self, **kwargs):
        ''' Return a FWLiteReader class for the sample
        '''
        from FWLiteReader import FWLiteReader
        logger.debug("Creating FWLiteReader object for sample '%s'.", self.name)
        return FWLiteReader( self, **kwargs )
