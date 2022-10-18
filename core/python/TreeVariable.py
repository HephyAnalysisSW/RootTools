''' Implementation of scalar and vector types.
Used in the Loopers and for plotting.
'''

# Standard imports
import abc
import uuid

import RootTools.core.helpers as helpers 

allTypes  = set(helpers.cStringTypeDict.keys())
allCTypes = set(helpers.cStringTypeDict.values())

class TreeVariable( object, metaclass=abc.ABCMeta ):
    @abc.abstractmethod
    def __init__(self):
        return 

    @classmethod
    def fromString( cls, string ):
        try:
            return VectorTreeVariable.fromString( string )

        except ( ValueError, AssertionError ):
            return ScalarTreeVariable.fromString( string )

class ScalarTreeVariable( TreeVariable ):

    def __init__( self, name, tp, defaultCString = None ):
        ''' Initialize variable. 
            tp: shortcut for ROOT type (b/s/S/I/i/F/D/L/l/O) or the corresponding C ROOT types, 
            'defaultCString': value the variable will be initialized with in a string representing  C code (!), 
                i.e. '-1' or 'TMath::QuietNaN()'
        '''
        self.name = name

        if not  tp in allTypes.union( allCTypes ):
            raise ValueError( "Type %r not known"%tp )
        # translate type to short form
        self.tp = tp if tp in allTypes else helpers.shortTypeDict[tp]

        # store default
        self.defaultCString = defaultCString if defaultCString is not None else helpers.defaultCTypeDict[self.tp]

    @property
    def type(self):
        return self.tp

    @classmethod
    def fromString( cls, string ):
        '''Create scalar variable from syntax 'name/type'
        '''
        if not type(string)==type(""): raise ValueError( "Expected string got %r"%string )
        string = string.replace(' ', '')
        if not string.count('/')==1:
            raise ValueError( "Could not parse string '%s', format is 'name/type'."%string )
            
        name, tp = string.split('/')
        return cls( name = name, tp = tp )

    @classmethod
    def uniqueFloat(cls):
        return cls(name = "float_"+str(uuid.uuid4()), tp='F' )

    @classmethod
    def uniqueInt(cls):
        return cls(name = "int_"+str(uuid.uuid4()), tp='I' )

    def __str__(self):
        return "%s(scalar, type: %s)" %(self. name, self.tp)

class VectorTreeVariable( TreeVariable ):

    def __init__( self, name, components, nMax = None):
        ''' Initialize variable.
            'components': list of ScalarTreeVariable 
            default is the value the variable will be initialized with,
            nMax is the maximal length of the vector in memory (if not specified: 100)
        '''
        self.name = name
        # Scalar components
        self._components = [ ScalarTreeVariable.fromString("%s_%s"%(self.name, x) ) if type(x)==type("") else x for x in components ]

        self.nMax = int(nMax) if nMax is not None else 100

    @classmethod
    def fromString(cls, string, nMax = None):
        '''Create vector variable from syntax 'name[c1/type1,c2/type2,...]'
        '''
        if not type(string)==type(""): raise ValueError( "Expected string got %r"%string )
        string = string.replace(' ', '')

        name_ = string[:string.find("[")]

        ts_ = string[string.find("[")+1:string.find("]")]
        componentStrings_ = ts_.split(',')

        return cls( name = name_, components = componentStrings_, nMax = nMax )

    @property 
    def components(self):
        return self._components

    def counterVariable(self):
        ''' Return a scalar counter variable 'nVectorname/I'
        '''
        return ScalarTreeVariable('n'+self.name, 'I')

    def __str__(self):
        return "%s(vector[%s], components: %s )" %(self. name, self.nMax, ",".join(str(c) for c in self.components) )
