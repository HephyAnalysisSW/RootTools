import ROOT

def errorStyle( color, markerStyle = 20, markerSize = 1, width = 1):
    def func( histo ):
        histo.SetLineColor( color )
        histo.SetMarkerSize( markerSize )
        histo.SetMarkerStyle( markerStyle )
        histo.SetMarkerColor( color )
#        histo.SetFillColor( color )
        histo.SetLineWidth( width )
        histo.drawOption = "e1"
        return 
    return func

def invisibleStyle ( ):
    def func( histo ):
        histo.SetMarkerSize(0)
        histo.SetLineWidth(0)
        return
    return func

def lineStyle( color, width = None, dotted=False, dashed=False, errors = False):
    def func( histo ):
        histo.SetLineColor( color )
        histo.SetMarkerSize( 0 )
        histo.SetMarkerStyle( 0 )
        histo.SetMarkerColor( color )
        histo.SetFillColor( 0 )
        if dotted: histo.SetLineStyle( 3 )
        if dashed: histo.SetLineStyle( 7 )
        if width: histo.SetLineWidth( width )
        histo.drawOption = "hist"
        if errors: histo.drawOption+='E'
        return 
    return func

def fillStyle( color, lineColor = ROOT.kBlack, lineWidth = 1, errors = False):
    def func( histo ):
        lc = lineColor if lineColor is not None else color
        histo.SetLineColor( lc )
        histo.SetMarkerSize( 0 )
        histo.SetMarkerStyle( 0 )
        histo.SetMarkerColor( lc )
        histo.SetFillColor( color )
        histo.SetLineWidth( lineWidth )
        histo.drawOption = "hist"
        if errors: histo.drawOption+='E'
        return 
    return func


def hashStyle( hashCode=3644, color=ROOT.kGray+2, lineColor = ROOT.kBlack, lineWidth = 0):
    def func( histo ):
        lc = lineColor if lineColor is not None else color
        histo.SetLineColor( lc )
        histo.SetMarkerSize( 0 )
        histo.SetMarkerStyle( 0 )
        histo.SetFillStyle( hashCode )
        histo.SetLineWidth( lineWidth )
        histo.SetFillColor( color )
        histo.drawOption = "hist"
        return 
    return func
