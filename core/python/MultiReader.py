''' MultiReader implementation. Run readers in parallel and align events according to keys.
'''

# Logging
import logging
logger      = logging.getLogger(__name__)

# RootTools
from RootTools.core.LooperBase import LooperBase
from RootTools.fwlite.FWLiteReader import FWLiteReader

default_key = lambda event: ( event.run, event.lumi, event.evt )

class MultiReader( LooperBase ):

    def __init__(self, *args):
        ''' Initialize with 'MultiReader( (reader1, key1), (reader2, key2), ... )'
            key1, ... should each return '(run, lumi, event)' and in this order for higher speed (Note: don't start with event).
            Will run over all common events defined by the return value of keys.
        '''

        if len(args)==0:
            logger.error( "Can't initialze MultiReader. Need 'MultiReader( (reader1, key1), (reader2, key2), ... )', got %s", repr( args ) )
            raise ValueError( "Can't create MultiReader instance." )

        self.readers = []
        self.keys    = []
        for i_arg, arg in enumerate( args ):
            self.readers.append( arg[0] )
            self.keys.append( default_key if len(arg)==1 else arg[1] ) 

        logger.debug( "Created MultiReader from %i samples", len(self.readers) )

        super(MultiReader, self).__init__()

    def _initialize(self):

        # Loop over all readers and create common list
        # FIXME: If reading many branches from a flat tree, there is currently a performance loss in the first loop
        # which in fact only needs the branches for the key.  

        logger.info( "Intersecting %i readers", len(self.readers) )
        reader_positions = {}        
        for i_reader, reader in enumerate(self.readers):
            reader_positions[i_reader] = {}

            # Let's at least not read all FWLite arguments if we're running for the first time.
            kwargs = {'readProducts': False} if isinstance( reader, FWLiteReader ) else {}

            reader.start()
            while reader.run( **kwargs ):
                reader_positions[i_reader][ self.keys[i_reader](reader.event) ] = reader.position-1

            if i_reader == 0:
                intersec = set(reader_positions[i_reader].keys())
                logger.info( "Reader %i has %i different reader_positions.", i_reader, len( intersec )  )
            else:
                before = len(intersec)
                len_i  = len(reader_positions[i_reader])
                intersec = set(reader_positions[i_reader].keys()).intersection(intersec)
                logger.info( "Intersecting with reader %i ( %i different positions) gives %i common positions (before: %i).", i_reader, len_i, len( intersec ), before )

        x_readers       = list(range( len( self.readers )))
        self.reader_positions  = [tuple(reader_positions[i_reader][i] for i_reader in x_readers ) for i in intersec ]

        # FIXME: Sorting is important for performance. The key should be chosen such that if it's sorted 
        # we don't jump between files unnecessarily. 
        # I.e. use (run, lumi, evt) but not (evt, lumi, run) etc.

        self.reader_positions.sort() 
        self.nEvents    = len( self.reader_positions )

        # Initialize
        self.position = 0

        return 1

    def _execute(self):

        if self.position==0:
            logger.info("MultiReader starting at position %i and processing %i events.", 
                self.position, self.nEvents)
        elif (self.position % 10000)==0:
            logger.info("MultiReader is at position %6i/%6i", 
                self.position, self.nEvents )

        for i_reader, reader in enumerate( self.readers):
            reader.goToPosition( self.reader_positions[self.position][i_reader] )
               
        if self.position==self.nEvents-1: 
            return 0

        return 1
