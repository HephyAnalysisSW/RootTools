# RootTools imports

from RootTools.core.TreeVariable import TreeVariable, VectorTreeVariable, ScalarTreeVariable
from RootTools.core.helpers import cStringTypeDict, defaultCTypeDict

def getCTypeString(typeString):
    '''Translate ROOT shortcuts for branch description to proper C types
    '''
    if typeString in list(cStringTypeDict.keys()):
        return cStringTypeDict[typeString]
    else:
        raise Exception( "Cann ot determine C type for type '%s'"%typeString )

def getCDefaultString(typeString):
    '''Get default string from ROOT branch description shortcut
    '''
    if typeString in list(defaultCTypeDict.keys()):
        return defaultCTypeDict[typeString]
    else:
        raise Exception( "Can not determine C type for type '%s'"%typeString )

def createClassString(variables, useSTDVectors = False, addVectorCounters = False):
    '''Create class string from scalar and vector variables
    '''

    vectors = [v for v in variables if isinstance(v, VectorTreeVariable) ]
    scalars = [s for s in variables if isinstance(s, ScalarTreeVariable) ]

    # Adding default counterVariable 'nVectorname/I' if specified
    if addVectorCounters: scalars += [v.counterVariable() for v in vectors]
    
    # for removing duplicates:
    declared_components = []
    # Create the class string
    scalarDeclaration = ""
    scalarInitString  = ""
    for scalar in scalars:
        # checking for duplicates.
        # This is necessary since I can't define __eq__ for Variables ignoring the filler function 
        # The filler function makes variables be different when their class name is identical
        # Safer to check for duplicate class names at the lowest level
        if scalar.name in declared_components:
            continue
        else:
            declared_components.append(scalar.name)
        scalarDeclaration += "  %s %s;\n"% ( getCTypeString(scalar.type), scalar.name )
        scalarInitString  += "  %s = %s;\n"%( scalar.name, getCDefaultString(scalar.type) )
        
    vectorDeclaration = ""
    vectorInitString  = ""
    if useSTDVectors:
        for vector in vectors:
            for c in vector.components:
                if c.name in declared_components:
                    continue
                else:
                    declared_components.append(c.name)
                # FIXME Rewritten, but never actually checked for std vectors 
                vectorDeclaration += "  std::vector< %s > %s;\n" % ( getCTypeString(c.type), c.name)
                vectorInitString  += "  %s.clear();\n" % c.name 
    else:
        for vector in vectors:
            if not hasattr( vector, 'nMax' ):
                raise ValueError ("Vector definition needs nMax if using C arrays: %r"%vector)
            vectorCompInitString = ""
            for c in vector.components:
                if c.name in declared_components:
                    continue
                else:
                    declared_components.append(c.name)
                vectorDeclaration    +=  "  %s %s[%3i];\n" % ( getCTypeString(c.type), c.name, vector.nMax)
                vectorCompInitString +=  "    %s[i] = %15s;\n"%(c.name, getCDefaultString(c.type)) 
            if vectorCompInitString != "":
                vectorInitString += """\n  for(UInt_t i=0;i<{nMax};i++){{\n{vectorCompInitString}     }}; //End for loop"""\
                    .format(nMax = vector.nMax, vectorCompInitString = vectorCompInitString)

    return \
"""#ifndef __className__
#define __className__

#include<vector>
#include<TMath.h>


class className{{
  public:
{scalarDeclaration}
{vectorDeclaration}
  void init(){{

{scalarInitString}
{vectorInitString}
  }}; // End init
}}; // End class declaration
#endif""".format(scalarDeclaration = scalarDeclaration,\
                 scalarInitString = scalarInitString, vectorDeclaration=vectorDeclaration, 
                 vectorInitString=vectorInitString)
