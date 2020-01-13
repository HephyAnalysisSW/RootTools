'''
Implementation for CMS analyses
'''

# Standard imports
import os
import time
import sqlite3

# Logger
import logging
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database, tableName, columns):
        '''
        Will create a table with name tableName, with the provided columns (as a list) and two additional columns: value and time_stamp
        '''
        self.database_file = database
        self.connect()
        self.tableName      = tableName
        self.columns        = columns + ["value"]
        self.columnString   = ", ".join([ s+" text" for s in self.columns ])
        executeString = '''CREATE TABLE %s (%s, time_stamp real )'''%(self.tableName, self.columnString)
        try:
            self.cursor.execute(executeString)
        except sqlite3.OperationalError:
            pass
        # try to aviod database malform problems
        self.cursor.execute('''PRAGMA journal_mode = DELETE''') # WAL doesn't work on network filesystems
        self.cursor.execute('''PRAGMA synchronus = 2''')
        self.close()

    def connect(self):

        # Create database directory if it doesn't exist
        path = os.path.abspath( os.path.dirname( self.database_file ) )
        if not os.path.exists( path ):
            os.makedirs( path )
            logger.debug( "Created directory for Database file: %s", path )

        # Connect
        self.database = sqlite3.connect("%s::memory:?cache=shared"%self.database_file)
        self.cursor = self.database.cursor()

    def close(self):
        self.cursor.close()
        self.database.close()
        del self.cursor
        del self.database
        
    def getObjects(self, key):
        '''
        Get all entries in the database matching the provided key.
        '''
        columns = key.keys()+["value", "time_stamp"]
        selection = " AND ".join([ "%s = '%s'"%(k, key[k]) for k in key.keys() ])

        selectionString = "SELECT * FROM {} ".format(self.tableName) + " WHERE {} ".format(selection) + " ORDER BY time_stamp"
        self.connect()
        
        for i in range(60):

            try:
                obj = self.cursor.execute(selectionString)
                objs = [o for o in obj]
                self.close()
                return objs

            except sqlite3.DatabaseError as e:
                logger.error( "There seems to be an issue with the database, trying to read again from %s.", self.database_file )
                logger.info( "Attempt no %i", i )
                self.close()
                self.connect()
                time.sleep(1.0)

        self.close()
        raise e

    def getDicts(self, key):
        objs = self.getObjects(key)
        o = []
        for obj in objs:
            o.append({c:str(v) for c,v in zip( self.columns, obj ) })
        return o
    
    def contains(self, key):
        objs = self.getObjects(key)
        return len(objs)

    def getObject(self, key):
        objs = self.getObjects(key)
        try:
            return objs[-1]
        except IndexError:
            return 0

    def add(self, key, value, save, overwriteOldest=False):
        '''
        new DB structure. key needs to be a python dictionary. Save doesn't do anything here
        '''
        if os.environ['HOSTNAME'].startswith('worker'):
            raise RuntimeError( "I'm running on the hephy batch. I shall not fill the db file from here." ) 

        columns = key.keys()+["value", "time_stamp"]
        values  = key.values()+[str(value), time.time()]
        
        # check if number of columns matches. By default, there is no error if not, but better be save than sorry.
        if len(key.keys())+1 < len(self.columns):
            raise(ValueError("The length of the given key doesn't match the number of columns in the table. The following columns (excluding value and time_stamp) are part of the table: %s"%", ".join(self.columns)))

        selectionString = "INSERT INTO {} ".format(self.tableName) + " ({}) ".format(", ".join( columns )) + " VALUES ({})".format(", ".join([ "'%s'"%i for i in values ]))
        self.connect()

        for i in range(60):
            try:
                self.cursor.execute(selectionString)
                self.database.commit()
                logger.debug("Added value %s to database",value)
                self.close()
                return

            except sqlite3.OperationalError as e:
                logger.warning( "Database locked, waiting." )
                time.sleep(1.0)

            except sqlite3.DatabaseError as e:
                logger.error( "There seems to be an issue with the database, trying to write again." )
                logger.info( "Attempt no %i", i )
                self.close()
                self.connect()
                time.sleep(1.0)
        
        self.close()
        raise e
    
    def removeObjects(self, key):
        '''
        Remove entries matching the key. Careful when not all columns are specified!
        '''
        selection = " AND ".join([ "%s = '%s'"%(k, key[k]) for k in key.keys() ])

        selectionString = "DELETE FROM {} ".format(self.tableName) + " WHERE {} ".format(selection)
        self.connect()
        
        for i in range(60):

            try:
                self.cursor.execute(selectionString)
                self.database.commit()
                self.close()
                return

            except sqlite3.DatabaseError as e:
                logger.info( "There seems to be an issue with the database, trying again." )
                logger.info( "Attempt no %i", i )
                self.close()
                self.connect()
                time.sleep(1.0)

        self.close()
        raise e


    def resetDatabase(self):
        if os.path.isfile(self.database_file):
            os.remove(self.database_file)
        self.__init__(self.database_file, self.tableName, self.columns[:-1])

