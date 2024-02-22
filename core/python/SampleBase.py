''' Abstract Class for a Sample.
'''
#Abstract Base Class
import abc

# standard imports
import os

# Logging
import logging
logger      = logging.getLogger(__name__)

# RootTools imports
import RootTools.core.helpers as helpers

def copy_file_with_selection( filename, target_file, selection, treeName="Events", overwrite=True, skipCheck=False):
    import ROOT
    # https://root-forum.cern.ch/t/copytree-with-selection/44662/5
    tmp_directory = ROOT.gDirectory

    try:
        if os.path.exists(target_file) and (not overwrite) and ( skipCheck or helpers.checkRootFile(target_file, checkForObjects=[treeName] )):
            logger.info( "Found file %s. Do not copy %s with selection %s", target_file, filename, selection )
            return
    except IOError:
        pass
 
    logger.info( "Copy file %s -> %s with selection %s", filename, target_file, selection )

    file = ROOT.TFile(filename)
    tree = file.Get(treeName)
    tree.SetBranchStatus('*', 1) # read too few bytes: 6 instead of 12
    file_filtered = ROOT.TFile(target_file, 'recreate')
    tree_filtered = tree.CopyTree(selection)
    tree_filtered.Write()
    file_filtered.Close() # automatically deletes "tree_filtered", too
    file.Close() # automatically deletes "tree", too
    tmp_directory.cd()

class SampleBase( object ):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, files, normalization, xSection, isData, color, texName):
        self.name = name
        self.files = files

        if not len(self.files)>0:
          raise helpers.EmptySampleError( "No files for sample %s! Files: %s" % (self.name, self.files) )

        self.normalization = normalization
        self.xSection = xSection
        self.isData = isData
        self.color = color
        self.texName = texName if not texName is None else name

    def copy_files(self, target, update=True, selection=None, overwrite=True, skipCheck=False):
        if not os.path.exists(target):
            os.makedirs(target)

        new_files = []
        for i_filename, filename in enumerate(self.files):
            target_file = os.path.join( target, os.path.basename(filename) )
            if filename.startswith('root://'):
                import subprocess
                if selection is None:
                    if not os.path.exists( target_file ) or overwrite:
                        logger.info( "Copy (xrdcp) file %i/%i: %s -> %s", i_filename, len(self.files), filename, target_file )
                        subprocess.call(['xrdcp', '-f', filename, target_file])
                    else:
                        logger.info( "File %i/%i %s exists. Do not copy %s. ", i_filename, len(self.files), target_file, filename)
 
                else:
                    tmp_file = os.path.splitext(target_file)[0]+'_tmp.root'
                    logger.info( "Copy (xrdcp) file %i/%i: %s -> %s", i_filename, len(self.files), filename, tmp_file )
                    subprocess.call(['xrdcp', '-f', filename, tmp_file]) 
                    copy_file_with_selection( tmp_file, target_file, selection=selection, overwrite=overwrite, skipCheck=skipCheck)
                    os.remove(tmp_file)

                new_files.append( target_file )
            else:
                import shutil
                logger.info( "Copy file %i/%i: %s -> %s", i_filename, len(self.files), filename, target_file )
                if selection is None: 
                    shutil.copy( filename, target_file )
                else:
                    copy_file_with_selection( filename, target_file, selection=selection, overwrite=overwrite, skipCheck=skipCheck)
                 
                new_files.append( target_file )

        if update:
            self.files = new_files


    def reduceFiles( self, factor = 1, to = None ):
        ''' Reduce number of files in the sample
        '''
        len_before = len(self.files)
        norm_before = self.normalization

        if factor!=1:
            #self.files = self.files[:len_before/factor]
            self.files = self.files[0::factor]
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

