''' Create and fill histograms
'''

# Logging
import logging
logger = logging.getLogger(__name__)

# Standard imports
import ROOT
import os
import copy
from math import log
#import uuid
import operator
import functools

# RootTools
import RootTools.core.TreeVariable as TreeVariable
import RootTools.plot.Plot as Plot
import RootTools.core.helpers as helpers
import RootTools.plot.helpers as plot_helpers


def getLegendMaskedArea(legend_coordinates, pad):

    def constrain(x, interval=[0,1]):
        if x<interval[0]: return interval[0]
        elif x>=interval[0] and x<interval[1]: return x
        else: return interval[1]

    return {
        'yLowerEdge': constrain( 1.-(1.-legend_coordinates[1] - pad.GetTopMargin())/(1.-pad.GetTopMargin()-pad.GetBottomMargin()), interval=[0.3, 1] ),
        'xLowerEdge': constrain( (legend_coordinates[0] - pad.GetLeftMargin())/(1.-pad.GetLeftMargin()-pad.GetRightMargin()), interval = [0, 1] ),
        'xUpperEdge':constrain( (legend_coordinates[2] - pad.GetLeftMargin())/(1.-pad.GetLeftMargin()-pad.GetRightMargin()), interval = [0, 1] )
        }

def fill(plots, read_variables = [], sequence=[], ttreeFormulas = {}, max_events = -1 ):
    '''Create histos and fill all plots
    '''

    # Unique list of selection strings
    selectionStrings    = list(set(p.selectionString for p in plots))

    # Collect all tree variables 
    read_variables_ = []
    for v in read_variables:
        if type(v) == type(""):
            read_variables_.extend( helpers.fromString( v ) )
        else: 
            read_variables_.append( v )
        
    for selectionString in selectionStrings:
        logger.info( "Now working on selection string %s"% selectionString )

        # find all plots with current selection
        plots_for_selection = [p for p in plots if p.selectionString == selectionString]

        # Find all samples we have to loop over
        samples = list(set(sum([p.stack.samples for p in plots_for_selection], [])))
        logger.info( "Found %i different samples for this selectionString."%len(samples) )
        logger.debug("The samples are: %s", ",".join([s.name for s in samples]))        

        # Give histos to plot
        for p in plots_for_selection:
            p.histos = p.stack.make_histos(p)

        for sample in samples:
            logger.info( "Now working on sample %s" % sample.name )
            # find all plots whose stack contains the current sample
            plots_for_sample = [p for p in plots_for_selection if sample in p.stack.samples]

            # find the positions (indices)  of the stack in each plot
            for plot in plots_for_sample:
                plot.sample_indices = plot.stack.getSampleIndicesInStack( sample )

                # Weight can be global, or, if it is a list, it is per sample, that is : [[w1, w2, ...],[w3, ...], ...]
                # test the structure
                if isinstance( plot.weight, (tuple, list)):
                    if not len( plot.weight ) == len( plot.stack ):
                        raise RuntimeError( "Length of plot.weight (%i) and plot.stack (%i) not identical for plot %s" % (len(plot.weight), len(plot.stack), plot.name) )
                    for si, s in enumerate(plot.stack):
                        if not len( plot.weight[si] ) == len( plot.stack[si] ):
                            raise RuntimeError( "Plot {plotname} at pos {pos} in stack: plot.weight[{pos}] has len {lenposw} and plot.stack[{pos}] has len {lenposs}.".format(
                                plotname = plot.name,
                                pos = str(si), 
                                lenposw = str(len(plot.weight[si])), 
                                lenposs = str(len(plot.stack[si])) ) 
                            )
                    plot.tmp_weight_ = plot.weight
                else:
                    plot.tmp_weight_ = [[plot.weight for s in s2] for s2 in plot.stack ]
                
            # Make reader
            # Add variables from the plots (if any)
            read_variables_plot = [] 
            for p in plots_for_sample:
                for variable in p.tree_variables:
                    if variable not in read_variables_plot:  read_variables_plot.append( variable )

            # Check if we need to add sample dependend variables
            read_variables_sample = []
            if hasattr(sample, "read_variables"): 
                for v in sample.read_variables:
                    if type(v) == type(""):
                        read_variables_sample.extend( helpers.fromString( v ) )
                    else: 
                        read_variables_sample.append( v )
            # Create reader and run it over sample, fill the plots
            r = sample.treeReader( variables = read_variables_ + read_variables_plot + read_variables_sample, sequence = sequence, selectionString = selectionString, ttreeFormulas = ttreeFormulas)

            # Scaling sample
            sample_scale_factor = 1 if not hasattr(sample, "scale") else sample.scale

            # make a list of weights
            if not hasattr(sample, "weight"):
                sample.__weight = None
            else:
                if callable(sample.weight):
                    sample.__weight = [sample.weight]
                elif type(sample.weight)==type([]):
                    sample.__weight = sample.weight

            # Buffer the fillers for the event loop ... could be done with a decorator but prefer to be explicit. 
            for plot in plots_for_sample:
                plot.store_fillers = plot.fillers

            r.start()
            counter = 0
            while r.run():
                for plot in plots_for_sample:
                    for index in plot.sample_indices:

                        #Get weight
                        tmp_weight_ = plot.tmp_weight_[index[0]][index[1]]
                        weight  = 1 if tmp_weight_ is None else tmp_weight_( r.event, sample )

                        #if plot.name.startswith('V_pt'):
                        #    print "A", plot.name, index[0], index[1], tmp_weight_, weight
                        if sample.__weight is not None: 
                            # https://www.youtube.com/watch?v=8iYdJH1i4rc&feature=youtu.be&t=79 
                            weight *= reduce( operator.mul, map( operator.methodcaller('__call__', r.event, sample ), sample.__weight) )
                        weight*=sample_scale_factor

                        #Get x,y or just x which could be lists
                        TH_fill_args = [ filler( r.event, sample ) for filler in plot.store_fillers ]
                        # loop over vector args
                        if isinstance( TH_fill_args[0], (tuple, list) ):
                            for args in zip( *TH_fill_args ):
                                args += (weight,)
                                plot.histos[index[0]][index[1]].Fill( *args )
                        # scalar args
                        else:
                            # Experimental. Can make a cut by having an attribute return None 
                            if None in TH_fill_args: continue
                            TH_fill_args.append(weight)
                            plot.histos[index[0]][index[1]].Fill( *TH_fill_args )

                if max_events > 0: 
                    counter += 1
                    if counter > max_events: 
                        logger.debug( "Stop filling histograms because counter is %i and max_events is %i", counter, max_events )
                        break

            # Clean up
            for plot in plots_for_sample:
                del plot.sample_indices
                del plot.store_fillers

            r.cleanUpTempFiles() #FIXME improved cleanup logic

def fill_with_draw(plots, weight_string = "(1)"):
    '''Create and fill all plots using Sample.chain.Draw
    '''

    # Unique list of selection strings
    selectionStrings    = list(set(p.selectionString for p in plots))

    for selectionString in selectionStrings:
        logger.info( "Now working on selection string %s"% selectionString )

        # find all plots with current selection
        plots_for_selection = [p for p in plots if p.selectionString == selectionString]

        # Find all samples we have to loop over
        samples = list(set(sum([p.stack.samples for p in plots_for_selection], [])))
        logger.info( "Found %i different samples for this selectionString."%len(samples) )

        # Give histos to plot
        for p in plots_for_selection:
            p.histos = p.stack.make_histos(p)

        for sample in samples:
            weight_string_ = sample.combineWithSampleWeight( weight_string )
            logger.info( "Now working on sample %s with weight_string %s",  sample.name, weight_string_ )
            # find all plots whose stack contains the current sample
            plots_for_sample = [p for p in plots_for_selection if sample in p.stack.samples]

            # find the positions (indices)  of the stack in each plot
            for plot in plots_for_sample:
                plot.sample_indices = plot.stack.getSampleIndicesInStack(sample)

            # Scaling sample
            sample_scale_factor = 1 if not hasattr(sample, "scale") else sample.scale

            if hasattr(sample, "weight") and sample.weight is not None:
                raise ValueError( "Sample %s has weight. Can't do that in fill_with-draw.", s.name )

            for plot in plots_for_sample:
                for index in plot.sample_indices:

                    if len(plot.attributes)>1:
                        raise NotImplementedError( "So far can only do 1D plots with fill_with_draw.")
                    if plot.weight is not None:
                        raise ValueError( "Plot %s has weight function. Can't do that in fill_with_draw. Use 'weight_string' argument of fill_with_draw." % plot.name )
                    if type(plot.attributes[0])!=str:
                        raise NotImplementedError( "Please provide a string to draw. Got %r." % plot.attributes[0] ) 

                    args = ( plot.attributes[0]+">>"+plot.histos[index[0]][index[1]].GetName(), "("+weight_string_+")*("+sample.combineWithSampleSelection( plot.selectionString )+")", 'goff')

                    logger.debug( "Draw arguments: %s", ", ".join(args) )

                    sample.chain.Draw( *args )

                    logger.info( "Sample %s plot %s has integral %3.2f. weight_string %s", sample.name, plot.name, plot.histos[index[0]][index[1]].Integral(), weight_string_ )

                    if sample_scale_factor != 1:
                        logger.debug( "Scaling sample %s plot %s with factor %3.2f", sample.name, plot.name, sample_scale_factor )
                        plot.histos[index[0]][index[1]].Scale( sample_scale_factor )

            # Clean up
            for plot in plots_for_sample:
                del plot.sample_indices

def draw(plot, \
        yRange = "auto", 
        extensions = ["pdf", "png", "root"], 
        plot_directory = ".", 
        logX = False, logY = True, 
        ratio = None, 
        scaling = {}, 
        sorting = False, 
        legend = "auto", 
        drawObjects = [],
        widths = {},
        canvasModifications = [],
        histModifications = [],
        legendModifications = [],
        copyIndexPHP = False,
        redrawHistos = False,
        ):
    ''' yRange: 'auto' (default) or [low, high] where low/high can be 'auto'
        extensions: ["pdf", "png", "root"] (default)
        logX: True/False (default), logY: True(default)/False
        ratio: 'auto'(default) corresponds to {'histos':[(1,0)], 'logY':False, 'style':None, 'texY': 'Data / MC', 'yRange': (0.5, 1.5), 'drawObjects': []}
        scaling: {} (default). Scaling the i-th stack to the j-th is done by scaling = {i:j} with i,j integers
        sorting: True/False(default) Whether or not to sort the components of a stack wrt Integral
        legend: "auto" (default) or [x_low, y_low, x_high, y_high] or None. ([<legend_coordinates>], n) divides the legend into n columns. 
        drawObjects = [] Additional ROOT objects that are called by .Draw() 
        widths = {} (default) to update the widths. Values are {'y_width':500, 'x_width':500, 'y_ratio_width':200}
        canvasModifications = [] could be used to pass on lambdas to modify the canvas. histModifications similar for histos.
        copyIndexPHP: whether or not to copy index.php to the plot directory
    '''
    # FIXME -> Introduces CMSSW dependence
    ROOT.gROOT.LoadMacro("$CMSSW_BASE/src/RootTools/plot/scripts/tdrstyle.C")
    ROOT.setTDRStyle()
    defaultRatioStyle = {'histos':[(1,0)], 'logY':False, 'style':None, 'texY': 'Data / MC', 'yRange': (0.5, 1.5), 'drawObjects':[]}

    if ratio is not None and not type(ratio)==type({}):
        raise ValueError( "'ratio' must be dict (default: {}). General form is '%r'." % defaultRatioStyle)

    # default_widths    
    default_widths = {'y_width':500, 'x_width':500, 'y_ratio_width':200}
    if ratio is not None: default_widths['x_width'] = 520
    # Updating with width arguments 
    default_widths.update(widths)

    if not isinstance(scaling, dict):
        raise ValueError( "'scaling' must be of the form {0:1, 2:3} which normalizes stack[0] to stack[1] etc. Got '%r'" % scaling )
            
    # Make sure ratio dict has all the keys by updating the default
    if ratio is not None:
        defaultRatioStyle.update(ratio)
        ratio = defaultRatioStyle

    # Clone (including any attributes) and add up histos in stack
    histos = map(lambda l:map(lambda h:helpers.clone(h), l), plot.histos)

    # Add overflow bins for 1D plots
    if isinstance(plot, Plot.Plot):
        if plot.addOverFlowBin is not None:
           for s in histos:
                for p in s:
                    Plot.addOverFlowBin1D( p, plot.addOverFlowBin )

    for i, l in enumerate(histos):

        # recall the sample for use in the legend
        for j, h in enumerate(l):
            h.sample = plot.stack[i][j] if plot.stack is not None else None

            # Exectute style function on histo, therefore histo styler has precendence over stack styler
            if hasattr(h, "style"):
                h.style(h)

        # sort 
        if sorting:
            l.sort(key=lambda h: -h.Integral())

        # Add up stacks
        for j, h in enumerate(l):
            for k in range(j+1, len(l) ):
                l[j].Add(l[k])
    # Scaling
    for source, target in scaling.iteritems():
        if not ( isinstance(source, int) and isinstance(target, int) ):
            raise ValueError( "Scaling should be {0:1, 1:2, ...}. Expected ints, got %r %r"%( source, target ) ) 

        source_yield = histos[source][0].Integral()

        if source_yield == 0:
            logger.warning( "Requested to scale empty Stack? Do nothing." )
            continue

        factor = histos[target][0].Integral()/source_yield
        for h in histos[source]:
            h.Scale( factor )

    # Make canvas and if there is a ratio plot adjust the size of the pads

    if ratio is not None:
        default_widths['y_width'] += default_widths['y_ratio_width']
        scaleFacRatioPad = default_widths['y_width']/float( default_widths['y_ratio_width'] )
        y_border = default_widths['y_ratio_width']/float( default_widths['y_width'] )

    # delete canvas if it exists
    if hasattr("ROOT","c1"): 
        del ROOT.c1 

    c1 = ROOT.TCanvas("canvas", "drawHistos",200,10, default_widths['x_width'], default_widths['y_width'])

    if ratio is not None:
        c1.Divide(1,2,0,0)
        topPad = c1.cd(1)
        topPad.SetBottomMargin(0)
        topPad.SetLeftMargin(0.15)
        topPad.SetTopMargin(0.07)
        topPad.SetRightMargin(0.05)
        topPad.SetPad(topPad.GetX1(), y_border, topPad.GetX2(), topPad.GetY2())
        bottomPad = c1.cd(2)
        bottomPad.SetTopMargin(0)
        bottomPad.SetRightMargin(0.05)
        bottomPad.SetLeftMargin(0.15)
        bottomPad.SetBottomMargin(scaleFacRatioPad*0.13)
        bottomPad.SetPad(bottomPad.GetX1(), bottomPad.GetY1(), bottomPad.GetX2(), y_border)
    else:
        topPad = c1
        topPad.SetBottomMargin(0.13)
        topPad.SetLeftMargin(0.15)
        topPad.SetTopMargin(0.07)
        topPad.SetRightMargin(0.05)

    topPad.cd()

    for modification in canvasModifications: modification(c1)

    # Range on y axis: Start with default
    if not yRange=="auto" and not (type(yRange)==type(()) and len(yRange)==2):
        raise ValueError( "'yRange' must bei either 'auto' or (yMin, yMax) where yMin/Max can be 'auto'. Got: %r"%yRange )

    max_ = max( l[0].GetMaximum() for l in histos )
    min_ = min( l[0].GetMinimum() for l in histos )

    # If legend is in the form (tuple, int) then the number of columns is provided
    legendColumns = 1
    if legend is not None and len(legend) == 2:
       legendColumns = legend[1]
       legend        = legend[0]

    #Calculate legend coordinates in gPad coordinates
    if legend is not None:
        if legend=="auto":
            legendCoordinates = (0.50,0.93-0.05*sum(map(len, plot.histos)),0.92,0.93)
        else:
            legendCoordinates = legend 

    if logY:
        yMax_ = 10**0.5*max_
        yMin_ = 0.7
    else:
        yMax_ = 1.2*max_
        yMin_ = 0 if min_>0 else 1.2*min_
    if type(yRange)==type(()) and len(yRange)==2:
        yMin_ = yRange[0] if not yRange[0]=="auto" else yMin_
        yMax_ = yRange[1] if not yRange[1]=="auto" else yMax_

    #Avoid overlap with the legend
    if (yRange=="auto" or yRange[1]=="auto") and (legend is not None):
        scaleFactor = 1
        # Get x-range and y
        legendMaskedArea = getLegendMaskedArea(legendCoordinates, topPad)
        for i, l in enumerate(histos):
            histo = histos[i][0]
            for i_bin in range(1, 1 + histo.GetNbinsX()):
                # low/high bin edge in the units of the x axis
                xLowerEdge_axis, xUpperEdge_axis = histo.GetBinLowEdge(i_bin), histo.GetBinLowEdge(i_bin)+histo.GetBinWidth(i_bin) 
                # linear transformation to gPad system
                xLowerEdge  = (xLowerEdge_axis  -  histo.GetXaxis().GetXmin())/(histo.GetXaxis().GetXmax() - histo.GetXaxis().GetXmin())
                xUpperEdge  = (xUpperEdge_axis -  histo.GetXaxis().GetXmin())/(histo.GetXaxis().GetXmax() - histo.GetXaxis().GetXmin())
                # maximum allowed fraction in given bin wrt to the legendMaskedArea: Either all (1) or legendMaskedArea['yLowerEdge']
                maxFraction = legendMaskedArea['yLowerEdge'] if xUpperEdge>legendMaskedArea['xLowerEdge'] and xLowerEdge<legendMaskedArea['xUpperEdge'] else 1
                # Save 20%
                maxFraction*=0.8
                # Use: (y - yMin_) / (sf*yMax_ - yMin_) = maxFraction (and y->log(y) in log case). 
                # Compute the maximum required scale factor s. 
                y = histo.GetBinContent(i_bin)
                try:
                    if logY:
                        new_sf = yMin_/yMax_*(y/yMin_)**(1./maxFraction) if y>0 else 1 
                    else:
                        new_sf = 1./yMax_*(yMin_ + (y-yMin_)/maxFraction ) 
                    scaleFactor = new_sf if new_sf>scaleFactor else scaleFactor
                except ZeroDivisionError:
                    pass 
                # print i_bin, xLowerEdge, xUpperEdge, 'yMin', yMin_, 'yMax', yMax_, 'y', y, 'maxFraction', maxFraction, scaleFactor, new_sf

        # Apply scale factor to avoid legend
        yMax_ = scaleFactor*yMax_

    # Draw the histos
    same = ""
    for i, l in enumerate(histos):
        for j, h in enumerate(l):
            # Get draw option. Neither Clone nor copy preserves attributes of histo
            drawOption = histos[i][j].drawOption if hasattr(histos[i][j], "drawOption") else "hist"
            topPad.SetLogy(logY)
            topPad.SetLogx(logX)
            #print yMin_, yMax_
            h.GetYaxis().SetRangeUser(yMin_, yMax_)
            h.GetXaxis().SetTitle(plot.texX)
            h.GetYaxis().SetTitle(plot.texY)
            # precision 3 fonts. see https://root.cern.ch/root/htmldoc//TAttText.html#T5
            h.GetXaxis().SetTitleFont(43)
            h.GetYaxis().SetTitleFont(43)
            h.GetXaxis().SetLabelFont(43)
            h.GetYaxis().SetLabelFont(43)
            h.GetXaxis().SetTitleSize(24)
            h.GetYaxis().SetTitleSize(24)
            h.GetXaxis().SetLabelSize(20)
            h.GetYaxis().SetLabelSize(20)

            if ratio is None:
                h.GetYaxis().SetTitleOffset( 1.3 )
            else:
                h.GetYaxis().SetTitleOffset( 1.6 )

            for modification in histModifications: modification(h)
            if hasattr( plot, "histModifications") and type( plot.histModifications ) == type([]):
                for modification in plot.histModifications:
                    modification(h)
            #if drawOption=="e1": dataHist = h
            h.Draw(drawOption+same)
            same = "same"

    topPad.RedrawAxis()
    # Make the legend
    if legend is not None:
        legend_ = ROOT.TLegend(*legendCoordinates)
        legend_.SetNColumns(legendColumns)
        legend_.SetFillStyle(0)
#        legend_.SetFillColor(0)
        legend_.SetShadowColor(ROOT.kWhite)
        legend_.SetBorderSize(0)
#        legend_.SetBorderSize(1)
        for l in histos:
            for h in l:
                if hasattr(h.sample, "notInLegend"):
                    if h.sample.notInLegend: continue
                elif hasattr(h, "texName") and not h.texName:
                    continue
                elif hasattr(h, "legendText") and not h.legendText:
                    continue
                elif hasattr(h, "texName") and h.texName:
                    legend_text = h.texName
                elif hasattr(h, "legendText") and h.legendText:
                    legend_text = h.legendText
                elif h.sample is not None:
                    legend_text = h.sample.texName if hasattr(h.sample, "texName") else h.sample.name
                else:
                    continue #legend_text = "No title"   
                if hasattr(h, "legendOption"):
                    legend_option = h.legendOption
                    legend_.AddEntry(h, legend_text, legend_option)
                else:
                    legend_.AddEntry(h, legend_text)

        for modification in legendModifications: modification(legend_)

        legend_.Draw()

    for o in drawObjects:
        if o:
            if type(o) in [ ROOT.TF1, ROOT.TGraph ]:
                o.Draw('same')
            elif type(o) in [ ROOT.TEfficiency ]:
                o.Draw('Psame')
            else:
                #print 2, drawObjects
                o.Draw()
        else:
            logger.debug( "drawObjects has something I can't Draw(): %r", o)

    if redrawHistos:
        for i, l in enumerate(histos):
            drawOption = histos[i][j].drawOption if hasattr(histos[i][j], "drawOption") else "hist"
            for j, h in enumerate(l):
                h.Draw(drawOption+"same")
        topPad.RedrawAxis()

    # Make a ratio plot
    drawn_histos=[]
    if ratio is not None:
        bottomPad.cd()

        # Make all the ratio histograms
        same=''
        for i_num, i_den in ratio['histos']:
            num = histos[i_num][0]
            den = histos[i_den][0]
            h_ratio = helpers.clone( num )
            drawn_histos.append(h_ratio)
            # For a ratio of profiles, use projection (preserve attributes)
            if isinstance( h_ratio, ROOT.TProfile ):
                attrs = h_ratio.__dict__
                h_ratio = h_ratio.ProjectionX()
                h_ratio.__dict__.update( attrs )
                h_ratio.Divide( den.ProjectionX() )
            else:
                h_ratio.Divide( den )

            #if ratio['style'] is not None: ratio['style'](h_ratio) 

            h_ratio.GetXaxis().SetTitle(plot.texX)
            h_ratio.GetYaxis().SetTitle(ratio['texY'])

            h_ratio.GetXaxis().SetTitleFont(43)
            h_ratio.GetYaxis().SetTitleFont(43)
            h_ratio.GetXaxis().SetLabelFont(43)
            h_ratio.GetYaxis().SetLabelFont(43)
            h_ratio.GetXaxis().SetTitleSize(24)
            h_ratio.GetYaxis().SetTitleSize(24)
            h_ratio.GetXaxis().SetLabelSize(20)
            h_ratio.GetYaxis().SetLabelSize(20)

            h_ratio.GetXaxis().SetTitleOffset( 3.2 )
            h_ratio.GetYaxis().SetTitleOffset( 1.6 )

            h_ratio.GetXaxis().SetTickLength( 0.03*3 )
            h_ratio.GetYaxis().SetTickLength( 0.03*2 )


            h_ratio.GetYaxis().SetRangeUser( *ratio['yRange'] )
            h_ratio.GetYaxis().SetNdivisions(505)

            if ratio.has_key('histModifications'):
                for modification in ratio['histModifications']: modification(h_ratio)
            drawOption = h_ratio.drawOption if hasattr(h_ratio, "drawOption") else "hist"
            if drawOption == "e1":                          # hacking to show error bars within panel when central value is off scale
              graph = ROOT.TGraphAsymmErrors(h_ratio)       # cloning in order to get layout
              graph.Set(0)
              for bin in range(1, h_ratio.GetNbinsX()+1):   # do not show error bars on hist
                h_ratio.SetBinError(bin, 0.0001)
                center  = h_ratio.GetBinCenter(bin)
                val     = h_ratio.GetBinContent(bin)
                errUp   = num.GetBinErrorUp(bin)/den.GetBinContent(bin) if val > 0 else 0
                errDown = num.GetBinErrorLow(bin)/den.GetBinContent(bin) if val > 0 else 0
                graph.SetPoint(bin, center, val)
                graph.SetPointError(bin, 0, 0, errDown, errUp)
              h_ratio.Draw("e0"+same)
              graph.Draw("P0 same")
              drawn_histos.append( graph )
            else:
              h_ratio.Draw(drawOption+same)
            same = 'same'

        bottomPad.SetLogx(logX)
        bottomPad.SetLogy(ratio['logY'])

        line = ROOT.TPolyLine(2)
        line.SetPoint(0, h_ratio.GetXaxis().GetXmin(), 1.)
        line.SetPoint(1, h_ratio.GetXaxis().GetXmax(), 1.)
        line.SetLineWidth(1)
        line.Draw()

        for o in ratio['drawObjects']:
            if o:
                o.Draw()
            else:
                logger.debug( "ratio['drawObjects'] has something I can't Draw(): %r", o)

        bottomPad.RedrawAxis()
        if redrawHistos:
            for s in drawn_histos:
                drawOption = s.drawOption if hasattr(s, "drawOption") else "hist"
                if type(s) == ROOT.TGraphAsymmErrors: drawOption = "P0"
                if drawOption == "e1":                          # hacking to show error bars within panel when central value is off scale
                  s.Draw("e0 same")
                else:
                  s.Draw(drawOption+"same")
            bottomPad.RedrawAxis()

    if not os.path.exists(plot_directory):
        try:
            os.makedirs(plot_directory)
        except OSError: # Resolve rare race condition
            pass

    if copyIndexPHP: plot_helpers.copyIndexPHP( plot_directory )

    c1.cd()

    for extension in extensions:
        filename = plot.name# if plot.name is not None else plot.variable.name #FIXME -> the replacement with variable.name should already be in the Plot constructors
        ofile = os.path.join( plot_directory, "%s.%s"%(filename, extension) )
        c1.Print( ofile )
    del c1

def draw2D(plot, \
        extensions = ["pdf", "png", "root"], 
        plot_directory = ".", 
        logX = False, logY = False, logZ = True, 
        zRange = None,
        drawObjects = [],
        widths = {},
        canvasModifications = [],
        histModifications = [],
        copyIndexPHP = False,
        ):
    ''' plot: a Plot2D instance
        zRange: None ( = ROOT default) or [low, high] 
        extensions: ["pdf", "png", "root"] (default)
        logX: True/False (default), logY: True/False(default), logZ: True/False(default)
        drawObjects = [] Additional ROOT objects that are called by .Draw() 
        widths = {} (default) to update the widths. Values are {'y_width':500, 'x_width':500, 'y_ratio_width':200}
        canvasModifications = [] could be used to pass on lambdas to modify the canvas. histModifications similar for histos.
        copyIndexPHP: whether or not to copy index.php to the plot directory
    '''

    # FIXME -> Introduces CMSSW dependence
    ROOT.gROOT.LoadMacro("$CMSSW_BASE/src/RootTools/plot/scripts/tdrstyle.C")
    ROOT.setTDRStyle()

    # default_widths    
    default_widths = {'y_width':500, 'x_width':500, 'y_ratio_width':200}

    # Updating with width arguments 
    default_widths.update(widths)

    # Adding up all components
    histos = plot.histos_added
    histo = histos[0][0].Clone()
    if len(histos)>1:
        logger.warning( "Adding %i histos for 2D plot %s", len(histos), plot.name )
        for h in histos[1:]:
            histo.Add( h[0] )
                
    ## Clone (including any attributes) and add up histos in stack
    #if hasattr(histo, "style"):
    #    histo.style(histo)
    c1 = ROOT.TCanvas("ROOT.c1", "drawHistos", 200,10, default_widths['x_width'], default_widths['y_width'])

    c1.SetBottomMargin(0.13)
    c1.SetLeftMargin(0.15)
    c1.SetTopMargin(0.07)
    c1.SetRightMargin(0.05)

    for modification in canvasModifications: modification(c1)

    drawOption = plot.drawOption if hasattr(plot, "drawOption") else "COLZ"

    c1.SetLogx(logX)
    c1.SetLogy(logY)
    c1.SetLogz(logZ)
    histo.GetXaxis().SetTitle(plot.texX)
    histo.GetYaxis().SetTitle(plot.texY)

    # Range on z axis: Start with default
    if zRange is not None:
        if not (type(zRange)==type(()) and len(zRange)==2):
            raise ValueError( "'zRange' must be (zMin, zMax). Got: %r"%zRange )

        if (type(zRange)==type(()) and len(zRange)==2):
            histo.SetMinimum(zRange[0])
            histo.SetMaximum(zRange[1])

    # precision 3 fonts. see https://root.cern.ch/root/htmldoc//TAttText.html#T5
    histo.GetXaxis().SetTitleFont(43)
    histo.GetYaxis().SetTitleFont(43)
    histo.GetXaxis().SetLabelFont(43)
    histo.GetYaxis().SetLabelFont(43)
    histo.GetXaxis().SetTitleSize(24)
    histo.GetYaxis().SetTitleSize(24)
    histo.GetXaxis().SetLabelSize(20)
    histo.GetYaxis().SetLabelSize(20)

    # should probably go into a styler
    ROOT.gROOT.LoadMacro("$CMSSW_BASE/src/RootTools/plot/scripts/niceColorPalette.C")
    ROOT.niceColorPalette(255)
    #ROOT.gStyle.SetPalette(1)
    ROOT.gPad.SetRightMargin(0.15)

    for modification in histModifications: modification(histo)
    if hasattr( plot, "histModifications") and type( plot.histModifications ) == type([]):
        for modification in plot.histModifications:
            modification(histo)
        
    histo.Draw(drawOption)

    c1.RedrawAxis()

    for o in drawObjects:
        if o:
            o.Draw()
        else:
            logger.debug( "drawObjects has something I can't Draw(): %r", o)

    if not os.path.exists(plot_directory):
        os.makedirs(plot_directory)

    if copyIndexPHP: plot_helpers.copyIndexPHP( plot_directory )

    for extension in extensions:
        filename = plot.name# if plot.name is not None else plot.variable.name #FIXME -> the replacement with variable.name should already be in the Plot constructors
        c1.Print( os.path.join( plot_directory, "%s.%s"%(filename, extension) ) )

    del c1
