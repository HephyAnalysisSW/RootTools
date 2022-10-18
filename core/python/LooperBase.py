''' Abstract Class for a looping over an instance of Sample.
'''
#Abstract Base Class
import abc

# Logging
import logging
logger      = logging.getLogger(__name__)

class LooperBase( object, metaclass=abc.ABCMeta ):
    def __init__(self):

        # Internal state for running
        self.position = -1

    def start(self):
        ''' Call before starting a loop.
        '''
        logger.debug("Starting to run.")
        self._initialize()

    def run(self, **kwargs):
        ''' Incrementing the loop.
            Load event into self.entry. Return 0, if last event has been reached
        '''

        assert self.position>=0, "Not initialized!"
        success = self._execute( **kwargs )

        self.position += 1
        return success

    @abc.abstractmethod
    def _initialize(self):
        return

    @abc.abstractmethod
    def _execute(self):
        return
