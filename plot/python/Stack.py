''' A stack of samples (not plots).
Must be a list of lists.
'''
# Standard imports
import uuid
import array

# RootTools
from RootTools.core.Sample import Sample
from RootTools.plot.Plot import Plot
from RootTools.plot.Immutable import Immutable
from RootTools.plot.Binning import Binning

class Stack ( list ):
        
    def __init__(self, *stackList):

        # change [[...], X, [...] ...]  to [[...], [X], [...], ...]
        stackList = [ s if type(s)==type([]) else [s] for s in stackList]

        # Check the input. LBYL.
        for s in stackList:
            if not type(s)==type([]) or not all(isinstance(p, Sample) for p in s):
                raise ValueError("Stack should be a list of lists of Sample instances. Got %r."%( stackList ) )

        # Make Immutable
        # stackList = map(lambda l: map(lambda s:Immutable(s), l), stackList)

        super(Stack, self).__init__( stackList )

    @property
    def samples(self):
        ''' Get all unique samples for this stack
        '''
        return list(set(sum(self,[])))

    def make_histos(self, plot):
        '''Make histograms for plot for this stack. Structure is list of lists of histos parallel to the stack object
        '''
        res = []
        for i, l in enumerate(self):
            histos = [] 
            for j, s in enumerate(l):
                # 1D binning
                if isinstance(plot.binning, Binning):
                    # explicit 1D binning with thresholds
                    if plot.binning.binning_is_explicit:
                        histo = plot.histo_class(\
                            "_".join([plot.name, s.name, str(uuid.uuid4()).replace('-','_')]), 
                            "_".join([plot.name, s.name]), 
                             len(plot.binning.binning)-1, array.array('d', plot.binning.binning) )
                    # implicit 1D binning 
                    else:
                        histo = plot.histo_class(\
                            "_".join([plot.name, s.name, str(uuid.uuid4()).replace('-','_')]), 
                            "_".join([plot.name, s.name]), 
                             *plot.binning.binning )
                elif type(plot.binning)==type([]) or type(plot.binning)==type(()): 
                    # 2D binning with Binning class
                    if len(plot.binning)==2 and isinstance(plot.binning[0], Binning) and isinstance(plot.binning[1], Binning):
                        # both are explicit:
                        if plot.binning[0].binning_is_explicit and plot.binning[1].binning_is_explicit:
                            histo = plot.histo_class(\
                                "_".join([plot.name, s.name, str(uuid.uuid4()).replace('-','_')]), 
                                "_".join([plot.name, s.name]), 
                                 len(plot.binning[0].binning)-1, array.array('d', plot.binning[0].binning),
                                 len(plot.binning[1].binning)-1, array.array('d', plot.binning[1].binning))
                        # both are implicit:
                        elif not plot.binning[0].binning_is_explicit and not plot.binning[1].binning_is_explicit:
                            histo = plot.histo_class(\
                                "_".join([plot.name, s.name, str(uuid.uuid4()).replace('-','_')]), 
                                "_".join([plot.name, s.name]), 
                                 *(plot.binning[0].binning+plot.binning[1].binning) )
            
                    # 1D (and 2D) Binning is specified as [n, x0, x1] or [n, x0, x1, m, y0, y1]
                    else:
                        histo = plot.histo_class(\
                            "_".join([plot.name, s.name, str(uuid.uuid4()).replace('-','_')]), 
                            "_".join([plot.name, s.name]), 
                             *plot.binning )
                else:
                    raise ValueError( "Don't know what to do with binning of plot %s: %r"%( plot.name, plot.binning ) )

                histo.Reset()

                # Default sumW2
                try: histo.Sumw2()
                except: pass

                # Exectute style function on histo
                if hasattr(s, "style"):
                    s.style(histo)

                histos.append(histo)
            res.append(histos)
            
        return res 

    def getSampleIndicesInStack(self, sample):
        ''' Find the indices of a sample in the stack
        '''
        indices = []
        for i, l in enumerate(self):
            for j, s in enumerate(l):
                if s==sample: indices.append((i,j))
        return indices
