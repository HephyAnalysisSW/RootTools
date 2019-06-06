''' What is a 2D plot?
'''

# Standard imports
import ROOT

#RootTools
from RootTools.plot.PlotBase import PlotBase

class Plot2D( PlotBase ):

    defaultStack           = None
    defaultAttributes      = None
    defaultBinning         = None
    defaultName            = None
    defaultSelectionString = None
    defaultWeight          = None
    defaultHistoClass      = ROOT.TH2F
    defaultTexX            = "attribute x"
    defaultTexY            = "attribute y"

    @staticmethod
    def setDefaults(stack = None, attribute = None, binning = None, name = None, selectionString = None, weight = None, histo_class = ROOT.TH2F,
                 texX = "", texY = "Number of events"):
        Plot2D.defaultStack           = stack
        Plot2D.defaultAttributes      = attribute
        Plot2D.defaultBinning         = binning
        Plot2D.defaultName            = name
        Plot2D.defaultSelectionString = selectionString
        #Plot2D.defaultWeight          = staticmethod(weight) if not isinstance( weight, (list, tuple)) else [map(staticmethod, w2) for w2 in weight ]
        Plot2D.defaultWeight          = weight #if not isinstance( weight, (list, tuple)) else [map(staticmethod, w2) for w2 in weight ]
        Plot2D.defaultHistoClass      = histo_class
        Plot2D.defaultTexX            = texX
        Plot2D.defaultTexY            = texY

    def __init__(self, stack = None, attribute = None, binning = None, name = None, selectionString = None, weight = None, histo_class = None,
                 texX = None, texY = None, read_variables = []):
        ''' A 2D plot needs a
        'stack' of Sample instances, e.g. [[mc1, mc2, ...], [data], [signal1, signal2,...]], a
        'attribute' list or tuple of attributes to draw (same as class Plot) 
        'selectionString' to be used on top of each samples selectionString, a
        'weight' function, a 
        'histo_class', e.g. ROOT.TH2F or ROOT.TProfile2D
        'texX', 'texY' labels for x and y axis and a
        ''' 

        try:
            def_name = "_vs_".join(att.name for att in attribute)
        except:
            def_name = None

        plot_name = name   if name  is not None else Plot2D.defaultName if Plot2D.defaultName is not None else def_name
        if plot_name is None: raise ValueError( "Plot2D needs to have a name. Found 'None'" )

        super(Plot2D, self).__init__( \
            stack           = stack            if stack           is not None else Plot2D.defaultStack,
            selectionString = selectionString  if selectionString is not None else Plot2D.defaultSelectionString,
            weight          = weight           if weight          is not None else Plot2D.defaultWeight,
            texX            = texX             if texX            is not None else Plot2D.defaultTexX,
            texY            = texY             if texY            is not None else Plot2D.defaultTexY,
            name            = plot_name,
            read_variables  = read_variables 
        )

        self.attributes      = attribute        if attribute       is not None else Plot2D.defaultAttributes
        self.binning         = binning          if binning         is not None else Plot2D.defaultBinning
        self.histo_class     = histo_class      if histo_class     is not None else Plot2D.defaultHistoClass

    @classmethod
    def fromHisto(cls, name, histos, texX = defaultTexX, texY = defaultTexY):
        res = cls(stack=None, name=name, attribute=None, binning=None, selectionString = None, weight = None, histo_class = None,\
            texX = texX, texY = texY)
        res.histos = histos
        return res
