''' Sample class.
    Implements definition and handling of the TChain.
'''

# Standard imports
import ROOT
import uuid
import os
import random
from array import array
from math import sqrt
# Logging
import logging
logger = logging.getLogger(__name__)

# RootTools imports
import RootTools.core.helpers as helpers
import RootTools.plot.Plot as Plot

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

class Sample ( object ): # 'object' argument will disappear in Python 3

    def __init__(self, 
            name, 
            treeName , 
            files = [], 
            normalization = None, 
            selectionString = None, 
            weightString = None, 
            isData = False, 
            color = 0, 
            texName = None):
        ''' Handling of sample. Uses a TChain to handle root files with flat trees.
            'name': Name of the sample, 
            'treeName': name of the TTree in the input files
            'normalization': can be set in order to later calculate weights, 
            e.g. to total number of events befor all cuts or the sum of NLO gen weights
            'selectionString': sample specific string based selection (can be list of strings)
            'weightString': sample specific string based weight (can be list of strings)
            'isData': Whether the sample is real data or not (simulation)
            'color': ROOT color to be used in plot scripts
            'texName': ROOT TeX string to be used in legends etc.
        '''

        self.name = name
        self.treeName = treeName
        self.files = files

        if not len(self.files)>0:
          raise helpers.EmptySampleError( "No ROOT files for sample %s! Files: %s" % (self.name, self.files) )

        self.normalization = normalization
        self._chain = None
       
        self.__selectionStrings = [] 
        self.setSelectionString( selectionString )

        self.__weightStrings = [] 
        self.setWeightString( weightString )

        self.isData = isData
        self.color = color
        self.texName = texName if not texName is None else name

        # Other samples. Add friend elements (friend, treeName)
        self.friends = []
             
        logger.debug("Created new sample %s with %i files, treeName %s,  selectionStrings %r and weightStrings %r.", 
            name, len(self.files), treeName, self.__selectionStrings, self.__weightStrings)

    def setSelectionString(self, selectionString):
        if type(selectionString)==type(""):
            self.__selectionStrings = [ selectionString ]
        elif type(selectionString)==type([]): 
            self.__selectionStrings =  selectionString 
        elif selectionString is None:
            self.__selectionStrings = []
        else:
            raise ValueError( "Don't know what to do with selectionString %r"%selectionString )
        logger.debug("Sample now has selectionString: %s", self.selectionString)
        self.clear()

    def addSelectionString(self, selectionString):
        if type(selectionString)==type(""):
            self.__selectionStrings += [ selectionString ] 
            self.clear()
        elif type(selectionString)==type([]): 
            self.__selectionStrings +=  selectionString 
            self.clear()
        elif (selectionString is None ) or selectionString == []:
            pass 
        else:
            raise ValueError( "Don't know what to do with selectionString %r"%selectionString )

    def setWeightString(self, weightString):
        if type(weightString)==type(""):
            self.__weightStrings = [ weightString ]
        elif type(weightString)==type([]): 
            self.__weightStrings =  weightString 
        elif weightString is None:
            self.__weightStrings = []
        else:
            raise ValueError( "Don't know what to do with weightString %r"%weightString )
        logger.debug("Sample now has weightString: %s", self.weightString)
        self.clear()

    def addWeightString(self, weightString):
        if type(weightString)==type(""):
            self.__weightStrings += [ weightString ] 
            self.clear()
        elif type(weightString)==type([]): 
            self.__weightStrings +=  weightString 
            self.clear()
        elif (weightString is None ) or weightString == []:
            pass 
        else:
            raise ValueError( "Don't know what to do with weightString %r"%weightString )

    @property
    def selectionString(self):
        return self.__selectionStrings if type(self.__selectionStrings)==type("") else helpers.combineStrings(self.__selectionStrings, stringOperator = "&&") 

    @property
    def weightString(self):
        return self.__weightStrings if type(self.__weightStrings)==type("") else helpers.combineStrings(self.__weightStrings, stringOperator = "*") 

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
                   treeName = check_equal_([s.treeName for s in samples]),
                   normalization = normalization,
                   files = files,
                   selectionString = check_equal_([s.selectionString for s in samples]),
                   isData = check_equal_([s.isData for s in samples]),
                   color = color, 
                   texName = texName
            )
 
    @classmethod
    def fromFiles(cls, name, files, 
        treeName = "Events", normalization = None, 
        selectionString = None, weightString = None, 
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

        sample =  cls(name = name, treeName = treeName, files = files, normalization = normalization, \
                selectionString = selectionString, weightString = weightString,
                isData = isData, color=color, texName = texName)

        logger.debug("Loaded sample %s from %i files.", name, len(files))
        return sample

    @classmethod
    def fromDPMDirectory(cls, name, directory, treeName = "Events", normalization = None, \
                selectionString = None, weightString = None,
                isData = False, color = 0, texName = None, maxN = None, noCheckProxy=False):

        import subprocess
        if not directory.startswith("/dpm"): raise ValueError( "DPM directory does not start with /dpm/: %s" % directory )

        # Renew proxy
        from RootTools.core.helpers import renew_proxy
        proxy_path = os.path.expandvars('$HOME/private/.proxy')
        if not noCheckProxy:
            proxy = renew_proxy(proxy_path)
        else:
            proxy = proxy_path
            logger.info("Not checking your proxy. Asuming you know it's still valid.")
        logger.info( "Using proxy %s"%proxy )

        p = subprocess.Popen(["dpns-ls -l %s" % directory], shell = True , stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        files = []
        for line in p.stdout.readlines():
                line = line[:-1]
                filename = line.split()[-1] # The filename is the last string of the output of dpns-ls
                if filename.endswith(".root"):
                    files.append( "root://hephyse.oeaw.ac.at/" + os.path.join( directory, filename ) )
                if maxN is not None and maxN>0 and len(files)>=maxN:
                    break
        sample =  cls(name = name, treeName = treeName, files = files, normalization = normalization, \
            selectionString = selectionString, weightString = weightString,
            isData = isData, color=color, texName = texName)
        logger.debug("Loaded sample %s from %i files.", name, len(files))
        return sample

    @classmethod
    def fromDirectory(cls, name, directory, treeName = "Events", normalization = None, \
                selectionString = None, weightString = None,
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
            fileNames = [ os.path.join(d, f) for f in os.listdir(d) if f.endswith('.root') ]
            if len(fileNames) == 0:
                raise helpers.EmptySampleError( "No root files found in directory %s." %d )
            files.extend( fileNames )
        if not treeName: 
            treeName = "Events"
            logger.debug("Argument 'treeName' not provided, using 'Events'.") 

        # restrict files 
        maxN = maxN if maxN is not None and maxN>0 else None
        files = files[:maxN]

        sample =  cls(name = name, treeName = treeName, files = files, normalization = normalization, \
            selectionString = selectionString, weightString = weightString,
            isData = isData, color=color, texName = texName)
        logger.debug("Loaded sample %s from %i files.", name, len(files))
        return sample

    @classmethod
    def fromCMGOutput(cls, name, baseDirectory, treeFilename = 'tree.root', chunkString = None, treeName = 'tree', maxN = None, \
            selectionString = None, weightString = None, 
            isData = False, color = 0, texName = None):
        '''Load a CMG output directory from e.g. unzipped crab output in the 'Chunks' directory structure. 
           Expects the presence of the tree root file and the SkimReport.txt
        ''' 
        from cmg_helpers import read_cmg_normalization
        maxN = maxN if maxN is not None and maxN>0 else None

        # Reading all subdirectories in base directory. If chunkString != None, require cmg output name formatting
        chunkDirectories = []

        # FIXME: Better to loop only over subdirectories in base directory?
        for x in os.listdir(baseDirectory): 
            if os.path.isdir(os.path.join(baseDirectory, x)):
                if not chunkString or (x.startswith(chunkString) and x.endswith('_Chunk')) or x==chunkString:
                    chunkDirectories.append(os.path.join(baseDirectory, x))
                    if len(chunkDirectories)==maxN:break

        logger.debug( "Found %i chunk directories with chunkString %s in base directory %s", \
                           len(chunkDirectories), chunkString, baseDirectory )
        normalization = 0
        files = []
        failedChunks=[]
        goodChunks  =[]

        for i, chunkDirectory in enumerate( chunkDirectories ):
            success = False
            logger.debug("Reading chunk %s", chunkDirectory)

            # Find normalization
            sumW = None
            for root, subFolders, filenames in os.walk( chunkDirectory ):
                # Determine normalization constant
                if 'SkimReport.txt' in filenames:
                    skimReportFilename = os.path.join(root, 'SkimReport.txt')
                    with open(skimReportFilename, 'r') as fin:
                      sumW = read_cmg_normalization(fin)
                      if not sumW:
                          logger.warning( "Read chunk %s and found report '%s' but could not read normalization.",
                                               chunkDirectory, skimReportFilename )
            # Find treefile
            treeFile = None
            for root, subFolders, filenames in os.walk( chunkDirectory ):
                # Load tree file 
                if treeFilename in filenames:
                    treeFile = os.path.join(root, treeFilename)
                    # Checking whether root file is OG and contains a tree
                    if not helpers.checkRootFile(treeFile, checkForObjects=[treeName] ):
                        logger.warning( "Read chunk %s and found tree file '%s' but file looks broken.",  chunkDirectory, treeFile )

            # If both, normalization and treefile are OK call it successful.
            if sumW and treeFile:
                files.append( treeFile )
                normalization += sumW
                logger.debug( "Successfully read chunk %s and incremented normalization by %7.2f",  chunkDirectory, sumW )
                success = True
                goodChunks.append( chunkDirectory )

            if not success:
                failedChunks.append( chunkDirectory )

        # Don't allow empty samples
        if len(goodChunks) == 0:
            raise helpers.EmptySampleError("Could not find good CMGOutput chunks for sample {0}. Total number of chunks: {1}. baseDirectory: {2}"\
                  .format(name, len(chunkDirectories), baseDirectory))

        # Log statements
        eff = 100*len(failedChunks)/float( len(chunkDirectories) )
        logger.debug("Loaded CMGOutput sample %s. Total number of chunks : %i. Normalization: %7.2f Bad: %i. Inefficiency: %3.3f", \
                          name, len(chunkDirectories), normalization, len(failedChunks), eff)

        for chunk in failedChunks:
            logger.debug( "Failed to load chunk %s", chunk)
        logger.debug( "Read %i chunks and total normalization of %f", len(files), normalization )
        return cls( name = name, treeName = treeName, files = files, normalization = normalization, 
            selectionString = selectionString, weightString = weightString,
            isData = isData, color = color, texName = texName )

    @classmethod
    def fromCMGCrabDirectory(cls, name, baseDirectory, treeFilename = 'tree.root', treeName = 'tree', maxN = None, \
            selectionString = None, weightString = None,
            isData = False, color = 0, texName = None):
        '''Load a CMG crab output directory
        ''' 
        import tarfile
        from cmg_helpers import read_cmg_normalization

        maxN = maxN if maxN is not None and maxN>0 else None

        # Walk through all subdirectories and pick up pairs of files '..._n.root and ..._n.tgz where n is the job number'
        treeFiles = {}
        zipFiles  = {}
        for root, subFolders, filenames in os.walk( baseDirectory ):
            for filename in filenames:
                base, ext = os.path.splitext( filename )
                try:
                    n = int(base.split('_')[-1])
                except:
                    # filename is not of the form 'xyz_n' where n is the job number
                    continue
                # add the tgz and files to the dict.   
                filename_ = os.path.join(root, filename)
                if ext=='.root':
                    treeFiles[n] = filename_
                if ext=='.tgz':
                    zipFiles[n] = filename_
        # Find pairs of zip and root files
        pairs = set(zipFiles.keys()) & set(treeFiles.keys())
        n_jobs = len( set(zipFiles.keys()) | set(treeFiles.keys()) )

        normalization = 0
        files = []
        failedJobs = []
        for n in pairs:
            sumW = None
            tf = tarfile.open( zipFiles[n], 'r:gz' )
            for f in tf.getmembers():
                if "SkimReport.txt" in f.name:
                    sumW = read_cmg_normalization(tf.extractfile(f))
                if sumW is not None: break
            if sumW is None:
                logger.warning( "No normalization found when reading tar file %s", zipFiles[n] )
            tf.close()

            # Check treefile for whether the tree 'treeName' can be found.
            # This is an implicit check for broken, recovered or otherwise corrupted root files.
            treeFile = treeFiles[n] if helpers.checkRootFile(treeFiles[n], checkForObjects = [treeName] ) else None

            if treeFile is None: logger.warning( "File %s looks broken. Checked for presence of tree %s.", treeFiles[n] , treeName )

            # If both, normalization and treefile are OK call it successful.
            if sumW and treeFile:
                files.append( treeFile )
                normalization += sumW
                logger.debug( "Successfully read job %i and incremented normalization by %7.2f",  n, sumW )
            else:
                failedJobs.append( n )

        # Don't allow empty samples
        if len(files) == 0:
            raise helpers.EmptySampleError("Could not find valid crab CMG output for sample {0}. Total number of jobs: {1}. baseDirectory: {2}"\
                  .format(name, len(pairs), baseDirectory))

        # Log statements
        eff = 100*len(failedJobs)/float( n_jobs )
        logger.debug("Loaded CMGOutput sample %s. Total number of  jobs: %i, both tgz and root: %i. Normalization: %7.2f Bad: %i. Inefficiency: %3.3f", \
                          name, len(pairs), n_jobs, normalization, len(failedJobs), eff)

        logger.debug( "Read %i chunks and total normalization of %f", len(files), normalization )
        return cls( name = name, treeName = treeName, files = files, normalization = normalization, 
                selectionString = selectionString, weightString = weightString, 
                isData = isData, color = color, texName = texName )

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
            return [ Sample( 
                    name            = self.name+"_%i" % n_sample, 
                    treeName        = self.treeName, 
                    files           = chunks[n_sample], 
                    normalization   = self.normalization, 
                    selectionString = self.selectionString, 
                    weightString    = self.weightString, 
                    isData          = self.isData, 
                    color           = self.color, 
                    texName         = self.texName ) for n_sample in xrange(len(chunks)) ]
        else:
            return Sample(
                    name            = self.name,
                    treeName        = self.treeName,
                    files           = chunks[nSub],
                    normalization   = self.normalization,
                    selectionString = self.selectionString,
                    weightString    = self.weightString,
                    isData          = self.isData,
                    color           = self.color,
                    texName         = self.texName )
        

    # Handle loading of chain -> load it when first used 
    @property
    def chain(self):
        if not self._chain: 
            logger.debug("First request of attribute 'chain' for sample %s. Calling __loadChain", self.name)
            self.__loadChain()
        return self._chain

    # "Private" method that loads the chain from self.files
    def __loadChain(self):
        ''' Load the TChain. Private.
        '''
        if len(self.files) == 0:
            raise helpers.EmptySampleError("Sample {name} has no input files! Can not load.".format(name = self.name) )
        else:
            self._chain = ROOT.TChain(self.treeName)
            counter = 0
            for f in self.files:
                logger.debug("Now adding file %s to sample '%s'", f, self.name)
                try:
                    if helpers.checkRootFile(f, checkForObjects=[self.treeName]):
                        self._chain.Add(f)
                        counter+=1
                    else:
                        logger.error( "Check of root file failed. Skipping. File: %s", f )
                except IOError as e:
                    logger.error( "Could not load file %s", f )
                    #raise e

            logger.debug( "Loaded %i files for sample '%s'.", counter, self.name )

        # Add friends
        if hasattr( self, 'friends'):  # Catch cases where cached samples have no default value for friends attribute
            for friend_sample, friend_treeName in self.friends:
                self.chain.AddFriend(friend_sample.chain, friend_treeName)

    # branch information
    @property
    def leaves( self ):
        ''' Get the leaves in the chain
        '''
        if hasattr( self, "__leaves" ):
            return self.__leaves
        else:
            self.__leaves = [ {'name':s.GetName(), 'type':s.GetTypeName()} for s in  self.chain.GetListOfLeaves() ]
            return self.__leaves 

    def clear(self): 
        ''' Really (in the ROOT namespace) delete the chain
        '''
        if self._chain:

            self._chain.IsA().Destructor( self._chain )
            logger.debug("Called TChain Destructor for sample '%s'.", self.name)

            self._chain = None

        if hasattr(self, "__leaves"):
            del self.__leaves

        return

    def reduceFiles( self, factor = 1, to = None ):
        ''' Reduce number of files in the sample
        '''
        len_before = len(self.files)
        norm_before = self.normalization

        if factor!=1:
            self.files = self.files[:len_before/factor]
            if len(self.files)==0:
                raise helpers.EmptySampleError( "No ROOT files for sample %s after reducing by factor %f" % (self.name, factor) )
        elif to is not None:
            if to>=len(self.files):
                return
            self.files = self.files[:to] 
        else:
            return

        # Keeping track of reduceFile factors
        factor = len(self.files)/float(len_before)
        if hasattr(self, "reduce_files_factor"):
            self.reduce_files_factor *= factor
        else:
            self.reduce_files_factor = factor
        self.normalization = factor*self.normalization if self.normalization is not None else None

        logger.info("Sample %s: Reduced number of files from %i to %i. Old normalization: %r. New normalization: %r. factor: %3.3f", self.name, len_before, len(self.files), norm_before, self.normalization, factor) 

        return


    def sortFiles( self, sample, filename_modifier = None):
        ''' Remake chain from files sorted wrt. to another sample (e.g. for friend trees)
        '''

        # Check if file lists are identical
        filenames       = map(os.path.basename, self.files)
        other_filenames = [ f if filename_modifier is None else filename_modifier(f) for f in map(os.path.basename, sample.files) ]

        # Check if we have the same number of files
        if len(filenames)!=len(other_filenames):
            raise RuntimeError( "Can not sort files of sample %s according to sample %s because lengths are different: %i != %i", self.name, sample.name, len(self.files), len(sample.files) ) 

        new_filelist = []
        for f in other_filenames:
            # find position of file from other sample
            try:
                index = filenames.index(f)
            except ValueError:
                logger.error("Can not file %s from sample %s in files of sample %s", f, sample.name, self.name)
                raise

            new_filelist.append( self.files[index]  )

        # Destroy 
        self.clear()
        # Recreate files
        self.files = new_filelist
        return self

    def addFriend( self, other_sample, treeName, sortFiles = False):
        ''' Friend a chain from another sample.
        '''
        if sortFiles:
            other_sample.sortFiles( self )

        # Add Chains 
        self.friends.append( (other_sample, treeName) )

    def treeReader(self, *args, **kwargs):
        ''' Return a Reader class for the sample
        '''
        from TreeReader import TreeReader
        logger.debug("Creating TreeReader object for sample '%s'.", self.name)
        return TreeReader( self, *args, **kwargs )

    # Below some helper functions to get useful 

    def combineWithSampleSelection(self, selectionString):
        if selectionString is None: return self.selectionString
        if not type(selectionString)==type(""): raise ValueError( "Need 'None' or string for selectionString, got %s" % selectionString )
        if self.__selectionStrings:
            logger.debug("For Sample %s: Combining selectionString %s with sample selectionString %s", \
                self.name, selectionString, self.selectionString )
            return helpers.combineStrings( [selectionString]+self.__selectionStrings, stringOperator = "&&")
        else:
            logger.debug("For Sample %s: Return selectionString %s because sample has no selectionString", \
                self.name, selectionString )
            return selectionString

    def combineWithSampleWeight(self, weightString):
        if weightString is None: return self.weightString
        if not type(weightString)==type(""): raise ValueError( "Need 'None' or string for weightString, got %s" % weightString )
        if self.__weightStrings:
            logger.debug("For Sample %s: Combining weightString %s with sample weightString %s", \
                self.name, weightString, self.weightString )
            return helpers.combineStrings( [weightString]+self.__weightStrings, stringOperator = "*")
        else:
            logger.debug("For Sample %s: Return weightString %s because sample has no weightString", \
                self.name, weightString )
            return weightString

    def getEventList(self, selectionString=None):
        ''' Get a TEventList from a selectionString (combined with self.selectionString, if exists).
        '''

        selectionString_ = self.combineWithSampleSelection( selectionString )

        tmp=str(uuid.uuid4())
        logger.debug( "Making event list for sample %s and selectionString %s", self.name, selectionString_ )
        self.chain.Draw('>>'+tmp, selectionString_ if selectionString_ else "(1)")
        elistTMP_t = ROOT.gDirectory.Get(tmp)

        return elistTMP_t

    def getYieldFromDraw(self, selectionString = None, weightString = None, split = 1):
        ''' Get yield from self.chain according to a selectionString and a weightString
        ''' 

        if split > 1:
            results = [ subsample.getYieldFromDraw( selectionString = selectionString, weightString = weightString) for subsample in self.split( n = split, shuffle = True ) ]
            return {'val':sum( [r['val'] for r in results], ), 'sigma':sqrt( sum( [r['sigma']**2 for r in results], 0 ) ) }
        elif split == 1:
            selectionString_ = self.combineWithSampleSelection( selectionString )
            weightString_    = self.combineWithSampleWeight( weightString )

            tmp=str(uuid.uuid4())
            h = ROOT.TH1D(tmp, tmp, 1,0,2)
            h.Sumw2()
            #weight = weightString if weightString else "1"
            logger.debug( "getYieldFromDraw for sample %s with chain %r", self.name, self.chain )
            self.chain.Draw("1>>"+tmp, "("+weightString_+")*("+selectionString_+")", 'goff')
            res = h.GetBinContent(1)
            resErr = h.GetBinError(1)
            del h

            ## Should remove this unecessary dependency
            #return u_float.u_float( res, resErr )
            
            return {'val': res, 'sigma':resErr}
        else:
            raise ValueError( "Can't split into %r. Need positive integer." % split )

    def get1DHistoFromDraw(self, variableString, binning, selectionString = None, weightString = None, binningIsExplicit = False, addOverFlowBin = None, isProfile = False):
        ''' Get TH1D/TProfile1D from draw command using selectionString, weight. If binningIsExplicit is true, 
            the binning argument (a list) is translated into variable bin widths. 
            addOverFlowBin can be 'upper', 'lower', 'both' and will add 
            the corresponding overflow bin to the last bin of a 1D histogram'''

        selectionString_ = self.combineWithSampleSelection( selectionString )
        weightString_    = self.combineWithSampleWeight( weightString )

        tmp=str(uuid.uuid4())
        if binningIsExplicit:
            binningArgs = (len(binning)-1, array('d', binning))
        else:
            binningArgs = binning

        cls = ROOT.TProfile if isProfile else ROOT.TH1D

        res = cls(tmp, tmp, *binningArgs)

        #weight = weightString if weightString else "1"

        self.chain.Draw(variableString+">>"+tmp, "("+weightString_+")*("+selectionString_+")", 'goff')
       
        Plot.addOverFlowBin1D( res, addOverFlowBin )
 
        return res

    def get2DHistoFromDraw(self, variableString, binning, selectionString = None, weightString = None, binningIsExplicit = False, isProfile = False):
        ''' Get TH2D/TProfile2D from draw command using selectionString, weight. If binningIsExplicit is true, 
            the binning argument (a tuple of two lists) is translated into variable bin widths. 
        '''

        selectionString_ = self.combineWithSampleSelection( selectionString )
        weightString_    = self.combineWithSampleWeight( weightString )

        tmp=str(uuid.uuid4())
        if binningIsExplicit:
            if not len(binning)==2 and type(binning)==type(()):
                raise ValueError( "Need a tuple with two lists corresponding to variable bin thresholds for x and y axis. Got % s"% binning )
            binningArgs = (len(binning[0])-1, array('d', binning[0]), len(binning[1])-1, array('d', binning[1]))
        else:
            if not len(binning)==6:
                raise ValueError( "Need binning in standard 2D form: [nBinsx,xLow,xHigh,nBinsy,yLow,yHigh]. Got %s" % binning )
            binningArgs = binning

        if isProfile:
            cls = ROOT.TProfile2D 
        else:
            cls = ROOT.TH2D

        res = cls(tmp, tmp, *binningArgs)
        self.chain.Draw(variableString+">>"+tmp, "("+weightString_+")*("+selectionString_+")", 'goff')

        return res

    def get3DHistoFromDraw(self, variableString, binning, selectionString = None, weightString = None, binningIsExplicit = False, isProfile = False):
        ''' Get TH3D/TProfile3D from draw command using selectionString, weight. If binningIsExplicit is true, 
            the binning argument (a tuple of two lists) is translated into variable bin widths. 
        '''

        selectionString_ = self.combineWithSampleSelection( selectionString )
        weightString_    = self.combineWithSampleWeight( weightString )

        tmp=str(uuid.uuid4())
        if binningIsExplicit:
            if not len(binning)==3 and type(binning)==type(()):
                raise ValueError( "Need a tuple with three lists corresponding to variable bin thresholds for x, y and z axis. Got % s"% binning )
            binningArgs = (len(binning[0])-1, array('d', binning[0]), len(binning[1])-1, array('d', binning[1]),  len(binning[2])-1, array('d', binning[2]))
        else:
            if not len(binning)==9:
                raise ValueError( "Need binning in standard 3D form: [nBinsx,xLow,xHigh,nBinsy,yLow,yHigh,nBinsz,zLow,zHigh]. Got %s" % binning )
            binningArgs = binning

        if isProfile:
            cls = ROOT.TProfile3D 
        else:
            cls = ROOT.TH3D

        res = cls(tmp, tmp, *binningArgs)
        self.chain.Draw(variableString+">>"+tmp, "("+weightString_+")*("+selectionString_+")", 'goff')

        return res
