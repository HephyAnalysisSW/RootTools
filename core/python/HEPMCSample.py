''' HEPMC Sample class.
    Implements definition and handling of HEP MC files.
'''

# Standard imports
import os
import random

# Logging
import logging
logger = logging.getLogger(__name__)

# RootTools imports
import RootTools.core.helpers as helpers
import RootTools.plot.Plot as Plot
from RootTools.core.SampleBase import SampleBase

# new_name method for sample counting
@helpers.static_vars( sample_counter = 0 )
def new_name():
    result = "Sample_"+str( new_name.sample_counter )
    new_name.sample_counter += 1
    return result

def check_equal_(vals):
    if not len(set(vals)) == 1:
        raise ValueError( "Sample combine check failed on: %r"%vals )
    else:
        return vals[0]

class HEPMCSample ( SampleBase ): # 'object' argument will disappear in Python 3

    def __init__(self, 
            name, 
            files = [], 
            normalization = None,
            xSection = -1, 
            isData = False,
            color = 0, 
            texName = None):
        ''' Handling of sample. Uses a TChain to handle root files with flat trees.
            'name': Name of the sample, 
            'normalization': can be set in order to later calculate weights, 
            e.g. to total number of events befor all cuts or the sum of NLO gen weights
            'isData': Whether the sample is real data or not (simulation)
            'color': ROOT color to be used in plot scripts
            'texName': ROOT TeX string to be used in legends etc.
        '''
        
        super(HEPMCSample, self).__init__( name=name, files=files, normalization=normalization, xSection = xSection, isData=isData, color=color, texName=texName)
        logger.debug("Created new HEPMC Sample %s with %i files.", 
            name, len(self.files))

    @classmethod
    def combine(cls, name, samples, texName = None, maxN = None, color = 0):
        '''Make new sample from a list of samples.
           Adds normalizations if neither is None
        '''
        if not (type(samples) in [type([]), type(())]) or len(samples)<1:
            raise ValueError( "Need non-empty list of samples. Got %r"% samples)

        normalizations = [s.normalization for s in samples]
        if None not in normalizations:
            normalization = sum(normalizations)
        else:
            normalization = None

        files = sum([s.files for s in samples], [])
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        return cls(name = name, \
                   normalization = normalization,
                   files = files,
                   isData = check_equal_([s.isData for s in samples]),
                   color = color, 
                   texName = texName
            )
 
    @classmethod
    def fromFiles(cls, name, files, 
        normalization = None, 
        isData = False, color = 0, texName = None, maxN = None):
        '''Load sample from files or list of files. If the name is "", enumerate the sample
        '''

        # Work with files and list of files
        files = [files] if type(files)==type("") else files

        # If no name, enumerate them.
        if not name: name = new_name()

        # restrict files 
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        sample =  cls(name = name, files = files, normalization = normalization, \
                isData = isData, color=color, texName = texName)

        logger.debug("Loaded sample %s from %i files.", name, len(files))
        return sample

    @classmethod
    def fromDirectory(cls, name, directory, normalization = None, \
                isData = False, color = 0, texName = None, maxN = None):
        '''Load sample from directory or list of directories. If the name is "", enumerate the sample
        '''
        # Work with directories and list of directories
        directories = [directory] if type(directory)==type("") else directory 

        # If no name, enumerate them.
        if not name: name = new_name()

        # find all files
        files = [] 
        for d in directories:
            fileNames = [ os.path.join(d, f) for f in os.listdir(d) if f.endswith('.hepmc') ]
            if len(fileNames) == 0:
                raise helpers.EmptySampleError( "No root files found in directory %s." %d )
            files.extend( fileNames )

        # restrict files 
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        sample =  cls(name = name, files = files, normalization = normalization, \
            isData = isData, color=color, texName = texName)
        logger.debug("Loaded sample %s from %i files.", name, len(files))
        return sample

    def split( self, n, nSub=None, clear = True, shuffle = False):
        ''' Split sample into n sub-samples
        '''
        
        if n==1: return self

        if not n>=1:
            raise ValueError( "Can not split into: '%r'" % n )

        files = self.files
        if shuffle: random.shuffle( files ) 
        chunks = helpers.partition( files, min(n , len(files) ) ) 

        if clear: self.clear() # Kill yourself.

        if nSub == None:
            return [ HEPMCSample( 
                    name            = self.name+"_%i" % n_sample, 
                    files           = chunks[n_sample], 
                    normalization   = self.normalization, 
                    isData          = self.isData, 
                    color           = self.color, 
                    texName         = self.texName ) for n_sample in xrange(len(chunks)) ]
        else:
            return HEPMCSample(
                    name            = self.name,
                    files           = chunks[nSub],
                    normalization   = self.normalization,
                    isData          = self.isData,
                    color           = self.color,
                    texName         = self.texName )
        

    def clear(self): 
        ''' Need not do anayhting for HEPMC file. 
        '''
        return
