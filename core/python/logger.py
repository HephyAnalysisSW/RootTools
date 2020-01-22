import logging
import sys
def get_logger(logLevel, logFile = None):
    ''' Logger for post-processing module.
    
    '''

    # add TRACE (numerical level 5, less than DEBUG) to logging (similar to apache) 
    # see default levels at https://docs.python.org/2/library/logging.html#logging-levels
    logging.TRACE = 5
    logging.addLevelName(logging.TRACE, 'TRACE')
    
    logging.Logger.trace = lambda inst, msg, *args, **kwargs: inst.log(logging.TRACE, msg, *args, **kwargs)
    logging.trace = lambda msg, *args, **kwargs: logging.log(logging.TRACE, msg, *args, **kwargs)

    logger = logging.getLogger('RootTools')

    numeric_level = getattr(logging, logLevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % logLevel)
     
    logger.setLevel(numeric_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if logFile: 
      # create the logging file handler
      fileHandler = logging.FileHandler(logFile, mode='w')
      fileHandler.setFormatter(formatter)
      # add handler to logger object
      logger.addHandler(fileHandler)
 

    # create console handler and set level to debug
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)
 
    # log the exceptions to the logger
    def excepthook(*args):
        logger.error("Uncaught exception:", exc_info=args)

    sys.excepthook = excepthook
    return logger

def add_fileHandler( logFile, logLevel ):
    fileHandler = logging.FileHandler(logFile, mode='w')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fileHandler.setFormatter(formatter)
    logger = logging.getLogger('RootTools')
    logger.addHandler(fileHandler)
