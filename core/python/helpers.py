import ROOT
import os

# Logging
import logging
logger = logging.getLogger(__name__)

# Error handling
class EmptySampleError(Exception):
    '''Accessing a sample without ROOT files.
    '''
    pass

# List helper
def partition(lst, n):
    ''' Partition list into chunks of approximately equal size'''
    # http://stackoverflow.com/questions/2659900/python-slicing-a-list-into-n-nearly-equal-length-partitions
    n_division = len(lst) / float(n)
    return [ lst[int(round(n_division * i)): int(round(n_division * (i + 1)))] for i in range(n) ]

# Translation of short types to ROOT C types
cStringTypeDict = {
    'b': 'UChar_t',
    'B': 'Char_t',
    'S': 'Short_t',
    's': 'UShort_t',
    'I': 'Int_t',
    'i': 'UInt_t',
    'F': 'Float_t',
    'D': 'Double_t',
    'L': 'Long64_t',
    'l': 'ULong64_t',
    'O': 'Bool_t',
}
# reversed
shortTypeDict = {v: k for k, v in list(cStringTypeDict.items())}

# defaults
defaultCTypeDict = {
    'b': '0',
    'B': '0',
    'S': '-1',
    's': '0',
    'I': '-1',
    'i': '0',
    'F': 'TMath::QuietNaN()',
    'D': 'TMath::QuietNaN()',
    'L': '-1',
    'l': '-1',
    'O': '0',
}


# Decorator to have smth like a static variable
def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

def checkRootFile(f, checkForObjects=[] ):
    ''' Checks whether a root file exists, was not recoverd or otherwise broken and
    contains the objects in 'checkForObjects'
    '''
    if not f.startswith('root://'):
        if not os.path.exists(f): raise IOError("File {0} not found".format(f))
    rf = ROOT.TFile.Open(f)
    if not rf: raise IOError("File {0} could not be opened. Not a root file?".format(f))
    good = (not rf.IsZombie()) and (not rf.TestBit(ROOT.TFile.kRecovered))

    if not good: 
        rf.Close()
        return False

    for o in checkForObjects:
        if not rf.GetListOfKeys().Contains(o):
            rf.Close()
            return False 

    rf.Close()
    return True

def combineStrings( stringList = [], stringOperator = "&&"):
    '''Expects a list of string based cuts and combines them to a single string using stringOperator
    '''
    if stringList is None: return "(1)"

    if not all( (type(s) == type("") or s is None) for s in stringList):
        raise ValueError( "Don't know what to do with stringList %r"%stringList)

    list_ = [s for s in stringList if not s is None ]
    if len(list_)==0:
        return "(1)"
    elif len(list_)==1:
        return list_[0]
    else:
        return stringOperator.join('('+s+')' for s in list_)

def fromString(*args):
    ''' Make a list of Variables from the input arguments
    '''
    from RootTools.core.TreeVariable import TreeVariable
    args = sum( [ [s] if type(s)==type("") else s for s in args if s is not None], [])
    if not all(type(s)==type("") or isinstance(s, TreeVariable) for s in args):
        raise ValueError( "Need string or TreeVariable instance or list of these as argument, got %r"%args)
    return tuple([TreeVariable.fromString(s) if type(s)==type("") else s for s in args])

def clone(root_object, new_name = None):
    ''' Cloning a ROOT class instance and preserving attributes
    '''
    new = root_object.Clone() if new_name is None else root_object.Clone(new_name)
    new.__dict__.update(root_object.__dict__)
    return new 

def add_to_sequence( func, sequence ):
    sequence.append( func )
    return func

def read_from_subprocess(arglist):
    ''' Read line by line from subprocess
    '''
    import subprocess

    proc = subprocess.Popen(arglist,stdout=subprocess.PIPE)
    res = []
    while True:
        l = proc.stdout.readline()
        if l !=  '':
            res.append( l.rstrip() )
        else:
            break
    return res

def renew_proxy( filename = None, rfc = False, request_time = 192, min_time = 0):
    import os, subprocess

    proxy = None
    timeleft = 0

    # Make voms-proxy-info look for a specific proxy
    if filename is not None:
        os.environ["X509_USER_PROXY"] = filename

    # Check proxy path
    try:
        proxy     = read_from_subprocess( 'voms-proxy-info --path'.split() )[0]
    except IndexError:
        pass

    try:
        tl = read_from_subprocess( 'voms-proxy-info --timeleft'.split() )
        timeleft = int(float( tl[0] ))
    except IndexError:
        pass
    except ValueError:
        pass

    # Return existing proxy from $X509_USER_PROXY, the default location or filename
    if proxy is not None and os.path.exists( proxy ):
        if filename is None or os.path.abspath( filename ) == proxy:
            logger.info( "Found proxy %s with lifetime %i hours", proxy, timeleft/3600)
            if timeleft > 0 and timeleft >= min_time*3600 :
                os.environ["X509_USER_PROXY"] = proxy
                return proxy
            else:
                logger.info( "Lifetime %i not sufficient (require %i, will request %i hours).", timeleft/3600, min_time, request_time )

    
    arg_list = ['voms-proxy-init', '-voms', 'cms']

    if filename is not None:
        arg_list += [ '-out', filename ]

    arg_list += ['--valid', "%i:0"%request_time ]

    if rfc:
        arg_list += ['-rfc']

    # make proxy
    p = subprocess.call( arg_list )

    # read path
    new_proxy = None
    try:
        new_proxy     = read_from_subprocess( 'voms-proxy-info --path'.split() )[0]
    except IndexError:
        pass

    if new_proxy is not None and os.path.exists( new_proxy ):
        os.environ["X509_USER_PROXY"] = new_proxy
        logger.info( "Successfully created new proxy %s", new_proxy )
        return new_proxy
    else:
        raise RuntimeError( "Failed to make proxy %s" % new_proxy )

