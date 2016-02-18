########################################################################
# $Id: $
########################################################################

"""
It is a wrapper on top of Elasticsearch. It is used to manage the DIRAC monitoring types. 
"""
__RCSID__ = "$Id$"

from DIRAC.Core.Base.ElasticDB import ElasticDB
from DIRAC.MonitoringSystem.private.TypeLoader import TypeLoader
from DIRAC import S_OK, S_ERROR, gConfig, gLogger

########################################################################
class MonitoringDB( ElasticDB ):

  def __init__( self, name = 'Monitoring/MonitoringDB', readOnly = False ):
    ElasticDB.__init__( self, 'MonitoringDB', name )
    self.__readonly = readOnly
    self.__documents = {}
    self.__loadIndexes()
    
    
  def __loadIndexes( self ):
    """
    It loads all monitoring indexes and types.
    """
    retVal = gConfig.getSections( "/DIRAC/Setups" )
    if not retVal[ 'OK' ]:
      return S_ERROR( "Can't get a list of setups: %s" % retVal[ 'Message' ] )
    
    setupsList = retVal[ 'Value' ]
    objectsLoaded = TypeLoader().getTypes()

    # Load the files
    for pythonClassName in sorted( objectsLoaded ):
      typeClass = objectsLoaded[ pythonClassName ]
      for setup in setupsList:
        indexName = "%s_%s" % ( setup.lower(), typeClass().getIndex() )
        doc_type =  typeClass().getDocType() 
        mapping = typeClass().getMapping()
        monfields = typeClass().getMonitoringFields()
        self.__documents[doc_type] = {indexName:mapping,'monitoringFields':monfields}
        print "DDDD", self.__documents
        if self.__readonly:
          gLogger.info("Read only mode is okay")
        else:
          self.registerType( doc_type, indexName, mapping )
  
  def getIndexName(self, typeName):
    
    indexName = None
    
    if typeName in self.__documents and len(self.__documents[typeName].keys()) > 0:
      indexName = self.__documents[typeName].keys()[0]
    return indexName
  
  def registerType( self, mtype, index, mapping ):
    """
    It register the type and index, if does not exists
    :param str type: Type of the documents
    :param str index: name of the index
    """ 
    
    all_index = "%s-*" % index
    
    if self.checkIndex( all_index ):  
      indexes = self.getIndexes()
      if len(indexes) > 0:
        actualindexName = self.createFullIndexName(index)
        if self.checkIndex( actualindexName ):  
          self.log.info("The index is exists:", actualindexName)
        else:
          result = self.createIndex( index, mapping )
          if not result['OK']:
            self.log.error( result['Message'] )
          self.log.info("The index is created", actualindexName)
    else:
      #in that case no index exists
      result = self.createIndex( index, mapping )
      if not result['OK']:
        self.log.error( result['Message'] )
      
  def getKeyValues( self, typeName, setup ):
    """
    Get all values for a given key field in a type
    """
    keyValuesDict = {}
    
    indexName = "%s*" % (self.getIndexName( typeName ) )
    retVal = self.getDocTypes( indexName )
    if not retVal['OK']:
      return retVal
    docs = retVal['Value']
    monfields =  self.__documents[typeName]['monitoringFields']
    print 'docs', docs
    keys =  docs[typeName]['properties'].keys() 
    print 'dsdsds', keys 
    return S_OK( keys )                                            
    
