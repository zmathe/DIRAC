"""
It is used to test client->db-> service
"""

from DIRAC.MonitoringSystem.Client.MonitoringClient import MonitoringClient
from DIRAC.Core.DISET.RPCClient                     import RPCClient
from DIRAC.Core.DISET.TransferClient                import TransferClient
# from DIRAC.MonitoringSystem.DB.MonitoringDB         import MonitoringDB
from DIRAC                                          import gLogger
from datetime                                       import datetime
import unittest
import tempfile

class MonitoringTestCase( unittest.TestCase ):
  
  def setUp( self ):
    gLogger.setLevel( 'INFO' )
    
    self.client = MonitoringClient( rpcClient = RPCClient( 'dips://dmonitor.cern.ch:9201/Monitoring/Monitoring' ) )
    
    self.data = [{u'Status': u'Waiting', 'Jobs': 2, u'time': 1458130176, u'JobSplitType': u'MCStripping', u'MinorStatus': u'unset', u'Site': u'LCG.GRIDKA.de', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049848', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458130176, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'LCG.PIC.es', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'olupton', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458130176, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'LCG.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'olupton', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458130176, u'JobSplitType': u'MCStripping', u'MinorStatus': u'unset', u'Site': u'LCG.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049845', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 34, u'time': 1458141578, u'JobSplitType': u'DataStripping', u'MinorStatus': u'unset', u'Site': u'Group.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050299', u'UserGroup': u'lhcb_data', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 120, u'time': 1458141578, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'LCG.CERN.ch', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'mvesteri', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458141578, u'JobSplitType': u'MCStripping', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049845', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 2, u'time': 1458141578, u'JobSplitType': u'MCStripping', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049848', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458141578, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050286', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 95, u'time': 1458199202, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'Multiple', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'mamartin', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 3, u'time': 1458199202, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'Multiple', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'olupton', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 129, u'time': 1458199202, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'Multiple', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049844', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 5, u'time': 1458217812, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.IHEP.su', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050232', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 7, u'time': 1458217812, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.IHEP.su', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050234', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 1, u'time': 1458217812, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.IHEP.su', u'Reschedules': 1, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050236', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 3, u'time': 1458217812, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.IHEP.su', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050238', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 2, u'time': 1458217812, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.IHEP.su', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050248', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 12, u'time': 1458218413, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050248', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 5, u'time': 1458218413, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050250', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 4, u'time': 1458218413, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050251', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 1, u'time': 1458218413, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.CNAF.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050280', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 24, u'time': 1458219012, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.NIKHEF.nl', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050248', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 3, u'time': 1458219012, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.NIKHEF.nl', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050251', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 1, u'time': 1458222013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.Bologna.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050303', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 7, u'time': 1458222013, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'LCG.Bristol.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'clangenb', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 2, u'time': 1458222013, u'JobSplitType': u'User', u'MinorStatus': u'unset', u'Site': u'LCG.Bristol.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'mrwillia', u'JobGroup': u'lhcb', u'UserGroup': u'lhcb_user', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 1, u'time': 1458222013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.Bari.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050244', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 11, u'time': 1458222013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.Bari.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050246', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 22, u'time': 1458222013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.Bari.it', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050248', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 23, u'time': 1458225013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.DESYZN.de', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049844', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 18, u'time': 1458225013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.DESYZN.de', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00049847', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 1, u'time': 1458225013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.DESYZN.de', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050238', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Running', 'Jobs': 1, u'time': 1458225013, u'JobSplitType': u'MCSimulation', u'MinorStatus': u'unset', u'Site': u'LCG.DESYZN.de', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050246', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458226213, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.RRCKI.ru', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050243', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458226213, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.RRCKI.ru', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050251', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458226213, u'JobSplitType': u'MCStripping', u'MinorStatus': u'unset', u'Site': u'LCG.RRCKI.ru', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050256', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458226213, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050229', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458226213, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050241', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 1, u'time': 1458226213, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050243', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'},
                 {u'Status': u'Waiting', 'Jobs': 2, u'time': 1458226213, u'JobSplitType': u'MCReconstruction', u'MinorStatus': u'unset', u'Site': u'LCG.RAL.uk', u'Reschedules': 0, u'ApplicationStatus': u'unset', u'User': u'phicharp', u'JobGroup': u'00050247', u'UserGroup': u'lhcb_mc', u'metric': u'WMSHistory'}]
  
  def tearDown( self ):
    pass
  
class MonitoringInsertData ( MonitoringTestCase ):
  
  def test_bulkinsert( self ):
    result = self.client.addRecords( "wmshistory_index", "WMSHistory", self.data )
    self.assert_( result['OK'] )
    self.assertEqual( result['Value'], len( self.data ) )

class MonitoringTestChain ( MonitoringTestCase ):
  
  def test_listReports( self ):
    result = self.client.listReports( 'WMSHistory' )
    self.assert_( result['OK'] )
    self.assertEqual( result['Value'], ['AverageNumberOfJobs', 'NumberOfJobs', 'NumberOfReschedules'] )
  
  def test_listUniqueKeyValues( self ):
    result = self.client.listUniqueKeyValues( 'WMSHistory' )
    self.assert_( result['OK'] )
    self.assert_( 'Status' in result['Value'] )
    self.assert_( 'JobSplitType' in result['Value'] )
    self.assert_( 'MinorStatus' in result['Value'] )
    self.assert_( 'Site' in result['Value'] ) 
    self.assert_( 'ApplicationStatus' in  result['Value'] )
    self.assert_( 'User' in result['Value'] )
    self.assert_( 'JobGroup' in result['Value'] )
    self.assert_( 'UserGroup' in result['Value'] )
    self.assert_( 'metric' in result['Value'] )
    
  def test_generatePlot( self ):
    params = ( 'WMSHistory', 'NumberOfJobs', datetime( 2016, 3, 16, 12, 30, 0, 0 ), datetime( 2016, 3, 17, 19, 29, 0, 0 ), {'grouping': ['Site']}, 'Site', {} )
    result = self.client.generateDelayedPlot( *params )
    self.assert_( result['OK'] )
    self.assertEqual( result['Value'], {'plot': 'Z:eNpljcEKwjAQRH8piWLbvQkeRLAeKnhOm7Us2CTsbsH69UYUFIQZZvawb4LUMKQYdjRoKH3kNGeK403W0JEiolSAMZxpwodXcsZukFZItipukFyxeSmiNIB3Zb_lUQL-wD4ssQYYc2Jt_VQuB-089cin6yH1Ur5FPev_UgnrSjXfpRp0yfjGGLgcuz2JJl7wCYg6Slo=', 'thumbnail': False} )
  
  def test_getPlot( self ):
    tempFile = tempfile.TemporaryFile()
    transferClient = TransferClient( 'Monitoring/Monitoring' )
    params = ( 'WMSHistory', 'NumberOfJobs', datetime( 2016, 3, 16, 12, 30, 0, 0 ), datetime( 2016, 3, 17, 19, 29, 0, 0 ), {'grouping': ['Site']}, 'Site', {} )
    result = self.client.generateDelayedPlot( *params )
    self.assert_( result['OK'] )
    result = transferClient.receiveFile( tempFile, result['Value']['plot'] )
    self.assert_( result['OK'] )

class MonitoringDeleteChain( MonitoringTestCase ):
  
  def test_deleteNonExistingIndex( self ): 
    res = self.client.deleteIndex( "alllaaaaa" )
    self.assert_( res['Message'] )
    
  def test_deleteIndex( self ):
    today = datetime.today().strftime( "%Y-%m-%d" )
    result = "%s-%s" % ( 'wmshistory_index', today ) 
    res = self.client.deleteIndex( result )
    self.assert_( res['OK'] )
    self.assertEqual( res['Value'], 'test_wmshistory-index-%s' % today )
    

if __name__ == '__main__':
  testSuite = unittest.defaultTestLoader.loadTestsFromTestCase( MonitoringTestCase )
  #testSuite.addTest( unittest.defaultTestLoader.loadTestsFromTestCase( MonitoringInsertData ) )
  testSuite.addTest( unittest.defaultTestLoader.loadTestsFromTestCase( MonitoringTestChain ) )
  #testSuite.addTest( unittest.defaultTestLoader.loadTestsFromTestCase( MonitoringDeleteChain ) )
  unittest.TextTestRunner( verbosity = 2 ).run( testSuite )
