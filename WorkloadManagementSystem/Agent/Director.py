########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/WorkloadManagementSystem/Agent/Attic/Director.py,v 1.4 2008/07/09 16:19:34 rgracian Exp $
# File :   Director.py
# Author : Stuart Paterson, Ricardo Graciani
########################################################################

"""  The Director Agent controls the submission of pilots via the 
     PilotDirectors and Grid-specific PilotDirector sub-classes.  
     This is a simple wrapper that performs the instantiation and monitoring
     of the PilotDirector instances and add workload to them via ThreadPool
     mechanism.

     From the base Agent class it uses the following configuration Parameters
       - WorkDir:
       - PollingTime:
       - ControlDirectory:
       - MaxCycles:

     The following parameters are searched for in WorkloadManagement/Director:
       - threadStartDelay:
       - JobSelectLimit:

     It looks in the WorkloadManagement/Director section for the 
     list of Directors to be instantiated (one for each defined Flavour)
       - Flavours

     It will use those Directors to submit pilots for each of the Supported Platforms
       - Platforms
     For every Platform there must be a corresponding Section with the 
     necessary paramenters:
       
       - Flavour: <Flavour>PilotDirector module from the PilotAgent directory will 
               be used, currently LCG and gLite types are supported
       - Pool: if a dedicated Threadpool is desired for this Platform

     For every Flavour there must be a corresponding Section with the 
     necessary paramenters:
       gLite:
         
         
       LCG:

       The following paramenters will be taken from the Director section if not 
       present in the corresponding section
       - GenericPilotDN:
       - GenericPilotGroup:
       - DefaultPilotFlavour:

"""

__RCSID__ = "$Id: Director.py,v 1.4 2008/07/09 16:19:34 rgracian Exp $"

import types, time

from DIRAC.Core.Base.Agent                        import Agent
from DIRAC.Core.Utilities                         import List
from DIRAC.WorkloadManagementSystem.DB.JobDB      import JobDB
from DIRAC.WorkloadManagementSystem.DB.JobLoggingDB        import JobLoggingDB
from DIRAC.WorkloadManagementSystem.DB.ProxyRepositoryDB   import ProxyRepositoryDB
from DIRAC.WorkloadManagementSystem.DB.PilotAgentsDB       import PilotAgentsDB

from DIRAC.FrameworkSystem.Client.ProxyManagerClient       import gProxyManager

from DIRAC.Core.Utilities.ClassAd.ClassAdLight    import ClassAd
from DIRAC.Core.Utilities.ThreadPool              import ThreadPool
from DIRAC                                        import S_OK, S_ERROR, gConfig, gLogger, abort, Source, systemCall, Time
import DIRAC

MAJOR_WAIT     = 'Waiting'
MINOR_SUBMIT   = 'Pilot Submission'
MINOR_RESPONSE = 'Pilot Response'

import os, sys, re, string, time, shutil

AGENT_NAME = 'WorkloadManagement/Director'

jobDB             = JobDB()
jobLoggingDB      = JobLoggingDB()
pilotAgentsDB     = PilotAgentsDB()

class Director(Agent):

  #############################################################################
  def __init__(self):
    """ Standard constructor for Agent
    """
    Agent.__init__(self,AGENT_NAME)
    # some default values:
    self.threadStartDelay = 5
    self.jobDicts = {}
    self.log   = gLogger.getSubLogger('Director')
    # self.jobDB = JobDB()

  #############################################################################
  def initialize(self):
    """Sets defaults
    """
    result = Agent.initialize(self)
    if not result['OK']:
      return result

    self.directors = {}
    self.pools = {}
    self.__checkPlatforms()
    
    return S_OK()

  def execute(self):
    """
      The Director execution method.
      0.- Check DB status and look for changes in the configuration
      1.- Retrieve jobs Waiting for pilot submission from the WMS
      (eventually this should be modified to work with TaskQueues), all pending
      jobs are retrieved on each execution cycle, but not all will be considered, 
      sorted by their LastUpdate TimeStamp, older jobs will be handled first.
      2.- Loop over retrieved jobs.
        2.1.- Determine the requested Platform for the Job. This is an expensive
        operation and it is an inmutable Attribute of the Job, therefore it is
        kept to avoid further iteration with DB.
        2.2.- Attempt to insert the job into the corresponding Queue of the 
        TreadPool associated with the platform.
        2.3.- Stop considering a given Queue when first job find the Queue full
        2.4.- Iterate until all Qeueus are full
      3.- Reconfigure and Sleep
    """

    jobDB._connect()
    jobLoggingDB._connect()
    self.__checkPlatforms()

    for job in self.__getJobs():

      if  not job in self.jobDicts:
        if not self.__getJobDict(job):
          continue
      else:
        # We already have seen this job, do not check again constant Job Properties
        pass

      # Now try to process the job
      self.__submitPilot(job)

    return S_OK()

  def __submitPilot(self, job):
    """
      Try to insert the job in the corresponding Thread Pool, disable the Thread Pool
      until next itration once it becomes full
    """
    jobdict = self.jobDicts[job]
    platform = jobdict['Platform']

    if platform == 'ANY':
      # It is a special case, all platform should be considered
      platforms = List.randomize( self.self.directors.keys() )
    else:
      platforms = [platform]

    for platform in platforms:

      if not platform in self.directors or not self.directors[platform]['isEnabled']:
        continue
  
      pool = self.directors[platform]['pool']
      director = self.directors[platform]['director']
      ret = pool.generateJobAndQueueIt( director.submitPilot, 
                                        args=(jobdict, self ), 
                                        oCallback=director.callBack,
                                        oExceptionCallback=director.exceptionCallBack,
                                        blocking=False )
      if not ret['OK']:
        # Disable submission until next iteration 
        self.directors[platform]['isEnabled'] = False

  def __getJobs(self):
    """
      Retrieve all Jobs in "Waiting Pilot Submission" from WMS
    """

    selection = {'Status':'Waiting','MinorStatus':'Pilot Agent Submission'}
    result = jobDB.selectJobs(selection, orderAttribute='LastUpdateTime')
    if not result['OK']:
      self.log.warn(result['Message'])
      return []

    jobs = result['Value']
    if not jobs:
      self.log.info('No eligible jobs selected from DB')
    else:
      if len(jobs)>15:
        self.log.info( 'Selected jobs %s...' % string.join(jobs[0:14],', ') )
      else:
        self.log.info('Selected jobs %s' % string.join(jobs,', '))
        
    return jobs

  def __getJobDict(self, job):
    """
     Get job constant Properties and keep them local to avoid quering the DB each time
    """
    result = jobDB.getJobJDL(job)
    if not result['OK']:
      self.log.error(result['Message'])
      updateJobStatus( self.log, AGENT_NAME, job, 'Failed', 'No Job JDL Available', logRecord=True)
      return False

    # FIXME: this should be checked by the JobManager and the Optimizers
    jdl = result['Value']
    classAdJob = ClassAd(jdl)
    if not classAdJob.isOK():
      self.log.error( 'Illegal JDL for job:', job )
      updateJobStatus( self.log, AGENT_NAME, job, 'Failed', 'Job JDL Illegal', logRecord=True )
      return False

    jobDict = {'JobID': job}
    jobDict['JDL'] = jdl

    JobJDLStringMandatoryAttributes = [ 'Platform', 'Requirements' ]
    
    JobJDLStringAttributes = [ 'PilotType', 'GridExecutable' ]

    JobJDLListAttributes = [ 'SoftwareTag', 'Site', 'BannedSites', 'GridRequirements' ]

    JobJDLIntAttributes = [ 'MaxCPUTime' ]

    for attr in JobJDLStringMandatoryAttributes:
      jobDict[attr] = stringFromClassAd(classAdJob, attr)
      # FIXME: this should be checked by the JobManager and the Optimizers
      if not jobDict[attr]:
        self.log.error( '%s not defined for job:' % attr, job )
        updateJobStatus( self.log, AGENT_NAME, job, 'Failed', 'No %s Specified' % attr, logRecord=True )
        return False

    for attr in JobJDLStringAttributes:
      jobDict[attr] = stringFromClassAd(classAdJob, attr)

    for attr in JobJDLListAttributes:
      jobDict[attr] = stringFromClassAd(classAdJob, attr)
      jobDict[attr] = string.replace( string.replace(
                                               jobDict[attr], '{', '' ), '}', '' ) 
      jobDict[attr] = List.fromChar( jobDict[attr] )

    for attr in JobJDLIntAttributes:
      jobDict[attr] = intFromClassAd(classAdJob, attr)


    # Check now Job Attributes
    ret = jobDB.getJobAttributes(job)
    if not ret['OK']:
      self.log.warn(result['Message'])
      return False
    attributes = ret['Value']

    # FIXME: this should be checked by the JobManager and the Optimizers
    for attr in ['Owner','OwnerDN','JobType','OwnerGroup']:
      if not attributes.has_key(attr):
        updateJobStatus( self.log, AGENT_NAME, job, 'Failed', '%s Undefined' % attr, logRecord=True )
        self.log.error( 'Missing Job Attribute "%s":' %attr, job )
        return False
      jobDict[attr] = attributes[attr]


    self.jobDicts[job] = jobDict

    self.log.verbose('JobID: %s' % job)
    self.log.verbose('Owner: %s' % jobDict['Owner'])
    self.log.verbose('OwnerDN: %s' % jobDict['OwnerDN'])
    self.log.verbose('JobType: %s' % jobDict['JobType'])
    self.log.verbose('MaxCPUTime: %s' % jobDict['MaxCPUTime'])
    self.log.verbose('Requirements: %s' % jobDict['Requirements'])

    
    currentStatus = attributes['Value']['Status']
    if not currentStatus == MAJOR_WAIT:
      self.log.verbose('Job has changed status to %s and will be ignored:' % currentStatus, job )
      return False

    currentMinorStatus = attributes['Value']['MinorStatus']
    if not currentMinorStatus == MINOR_SUBMIT:
      self.log.verbose('Job has changed minor status to %s and will be ignored:' % currentMinorStatus, job )
      return False


  def __checkPlatforms(self):
    # this method is called at initalization and at the begining of each execution
    # in this way running parameters can be dynamically changed via the remote
    # configuration.

    # First update common Configuration for all Directors
    self.__configureDirector()
    
    # Now we need to initialize one thread for each Director in the List,
    # and check its configuration:
    platforms = gConfig.getValue( self.section+'/Platforms', [] )

    for platform in platforms:
      # check if the Director is initialized, then reconfigure
      if platform in self.directors:
        self.__configureDirector(platform)
      else:
        # instantiate a new Director
        self.__createDirector(platform)

      # Now enable the director for this iteration, if any RB is defined
      if platform in self.directors and self.directors[platform]['director'].resourceBrokers:
        self.directors[platform]['isEnabled'] = True

    # Now remove directors that are not Enable (they have been used but are no
    # longer required in the CS).
    pools = []
    for platform in self.directors.keys():
      if not self.directors[platform]['isEnabled']:
        self.log.info( 'Deleting Director for Platform:', platform )
        director = self.directors[platform]['director']
        del self.directors[platform]
        del director
      else:
        pools.append( self.directors[platform]['pool'] )

    # Finally delete ThreadPools that are no longer in use
    for pool in self.pools:
      if pool != 'Default' and not pool in pools:
        pool = self.pools[pool]
        del pool
        del self.pools[pool]


  def __createDirector(self,platform):
    # instantiate a new PilotDirector for the given Platform

    self.log.info( 'Creating Director for Platform:', platform )
    # 1. check the Flavour
    directorFlavour = gConfig.getValue( self.section+'/'+platform+'/Flavour','' )
    if not directorFlavour:
      self.log.error( 'No Director Flavour defined for Platform:', platform )
      return

    directorName = '%sPilotDirector' % directorFlavour
    
    try:
      self.log.info( 'Instantiating Director Object:', directorName )
      director = eval( '%s()' %  directorName )
    except Exception,x:
      self.log.exception(x)
      return
    
    self.log.info( 'Director Object instantiated:', directorName )

    # 2. check the requested ThreadPool (it not defined use the default one)
    directorPool = gConfig.getValue( self.section+'/'+platform+'/Pool','Default' )
    if not directorPool in self.pools:
      self.log.info( 'Adding Thread Pool:', directorPool)
      poolName = self.__addPool( directorPool )
      if not poolName:
        self.log.error( 'Can not create Thread Pool:', directorPool )
        return

    # 3. add New director
    self.directors[ platform ] = { 'director': director,
                                   'pool': directorPool, 
                                   'isEnabled': False,
                                   }

    self.log.verbose( 'Created Director for Platform', platform )

    return


    #Can be passed via a command line .cfg file for gLite
    self.type = gConfig.getValue(self.section+'/Middleware','LCG')

    self.threadStartDelay = gConfig.getValue(self.section+'/ThreadStartDelay',5)
    self.pdName = '%sPilotDirector' %(self.type)
    self.pdSection = '/%s/%s' % ( '/'.join( List.fromChar(self.section, '/' )[:-2] ), 'PilotAgent/%s' %(self.pdName))
    self.log.debug('%sPilotDirector CS section is: %s' %(self.type,self.pdSection))
    self.pdPath = gConfig.getValue(self.section+'/ModulePath','DIRAC.WorkloadManagementSystem.PilotAgent')
    self.started = False
    try:
      self.importModule = __import__('%s.%s' %(self.pdPath,self.pdName),globals(),locals(),[self.pdName])
    except Exception, x:
      msg = 'Could not import %s.%s' %(self.pdPath,self.pdName)
      self.log.warn(x)
      self.log.warn(msg)
      return S_ERROR(msg)



    return result

  def __configureDirector( self, platform=None ):
    # Update Configuration from CS
    # if platform == None then, only the do it for the Director
    # else do it for the PilotDirector of that Platform
    if not platform:
      # This are defined by the Base Class and thus will be available
      # on the first call
      self.workDir     = gConfig.getValue( self.section+'/WorkDir', self.workDir )
      self.pollingTime = gConfig.getValue( self.section+'/PollingTime', self.pollingTime )
      self.controlDir  = gConfig.getValue( self.section+'/ControlDirectory', self.controlDir )
      self.maxcount    = gConfig.getValue( self.section+'/MaxCycles', self.maxcount )
      
      # Default values are defined on the __init__
      self.threadStartDelay = gConfig.getValue(self.section+'/ThreadStartDelay', self.threadStartDelay )
      
      # By default disable all directors
      
      for director in self.directors:
        self.directors[director]['isEnabled'] = False
      
    else:
      if platform not in self.directors:
        abort(-1)
      director = self.directors[platform]['director']
      # pass reference to our CS section so that defaults can be taken from there
      director.configure( self.section, platform )
      # enable director
      self.directors[platform]['isEnabled'] = True

  def __addPool(self, poolName):
    # create a new thread Pool, by default it has 1 executing thread and 5 requests 
    # in the Queue
    # FIXME: get from CS
    if not poolName:
      return None
    if poolName in self.pools:
      return None
    pool = ThreadPool( 0,1,5 )
    pool.daemonize()
    self.pools[poolName] = pool
    return poolName


  #############################################################################
  def oldexecute(self):
    """The PilotAgent execution method.
    """
    agent = {}
    if not self.started:
      resourceBrokers = gConfig.getValue(self.pdSection+'/ResourceBrokers','lhcb-lcg-rb04.cern.ch')
  #  resourceBrokers = gConfig.getValue('LCGPilotDirector/ResourceBrokers','lcgrb03.gridpp.rl.ac.uk,lhcb-lcg-rb03.cern.ch')
      if not type(resourceBrokers)==type([]):
        resourceBrokers = resourceBrokers.split(',')

      for rb in resourceBrokers:
        gLogger.verbose('Starting thread for %s RB %s' %(self.type,rb))
        try:
          moduleStr = 'self.importModule.%s(self.pdSection,rb,self.type)' %(self.pdName)
          agent[rb] = eval(moduleStr)
        except Exception, x:
          msg = 'Could not instantiate %s()' %(self.pdName)
          self.log.warn(x)
          self.log.warn(msg)
          return S_ERROR(msg)

        agent[rb].start()
        time.sleep(self.threadStartDelay)

      self.started=True

    for rb,th in agent.items():
      if th.isAlive():
        gLogger.verbose('Thread for %s RB %s is alive' %(self.type,rb))
      else:
        gLogger.verbose('Thread isAlive() = %s' %(th.isAlive()))
        gLogger.warn('Thread for %s RB %s is dead, restarting ...' %(self.type,rb))
        th.start()

    return S_OK()


  def __initializeDirectors(self):
    """
     Initialize one Director for each requested Flavour
     This is done only once in the livetime of the Director. In order to add 
     new Flavours the Agent needs to be rebooted (could be fixed in the future)
    """

    self.flavours = gConfig.getValue( self.section+'/Flavours', ['gLite','LCG'] )

    for flavour in self.flavours:

      director = eval('%sDirector()' % flavour)
      self.directors[flavour] = director

    return

def stringFromClassAd( classAd, name ):
  value = ''
  if classAd.lookupAttribute( name ):
    value = string.replace(classAd.get_expression( name ), '"', '')
  return value

def intFromClassAd( classAd, name ):
  value = 0
  if classAd.lookupAttribute( name ):
    value = int(string.replace(classAd.get_expression( name ), '"', ''))
  return value



def updateJobStatus( logger, name, jobID, majorStatus, minorStatus=None, logRecord=False ):
  """This method updates the job status in the JobDB.
  """
  # FIXME: this log entry should go into JobDB
  logger.verbose("jobDB.setJobAttribute( %s, 'Status', '%s', update=True )" % ( jobID, majorStatus ) )
  result = jobDB.setJobAttribute( jobID, 'Status', majorStatus, update=True )

  if result['OK']:
    if minorStatus:
      # FIXME: this log entry should go into JobDB
      logger.verbose("jobDB.setJobAttribute( %s, 'MinorStatus', '%s', update=True)" % ( jobID, minorStatus) )
      result = jobDB.setJobAttribute( jobID, 'MinorStatus', minorStatus, update=True )

  if logRecord and result['OK']:
    result = jobLoggingDB.addLoggingRecord( jobID, majorStatus, minorStatus, name )

  if not result['OK']:
    logger.error(result['Message'])
    return False

  return True




# Some reasonable Defaults
DIRAC_PILOT   = os.path.join( DIRAC.rootPath, 'DIRAC', 'WorkloadManagementSystem', 'PilotAgent', 'dirac-pilot' )
DIRAC_INSTALL = os.path.join( DIRAC.rootPath, 'scripts', 'dirac-install' )
DIRAC_VERSION = 'Production'
DIRAC_SETUP   = 'LHCb-Development'

ENABLE_LISTMATCH = 1
LISTMATCH_DELAY  = 15
GRIDENV          = ''
PILOT_DN         = '/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=paterson/CN=607602/CN=Stuart Paterson'
PILOT_GROUP      = 'lhcb_pilot'
TIME_POLICY      = 'TimeRef * 500 / other.GlueHostBenchmarkSI00 / 60'
REQUIREMENTS     = ['other.GlueCEPolicyMaxCPUTime > MyPolicyTime','Rank > -2']
RANK             = '( other.GlueCEStateWaitingJobs == 0 ? other.GlueCEStateFreeCPUs * 10 / other.GlueCEInfoTotalCPUs : -other.GlueCEStateWaitingJobs * 4 / (other.GlueCEStateRunningJobs + 1 ) - 1 )'
FUZZY_RANK       = 'true'


LOGGING_SERVER   = 'lb101.cern.ch'

class PilotDirector:
  def __init__(self):
    self.log = gLogger.getSubLogger('%sPilotDirector' % self.flavour)
    if not  'log' in self.__dict__:
      self.log = gLogger.getSubLogger('PilotDirector')
    self.log.info('Initialized')
    self.resourceBrokers    = ['some.stupid.default']

  def configure(self, csSection, platform ):
    """
     Here goes common configuration for all PilotDirectors
    """
    self.install            = gConfig.getValue( csSection+'/InstallScript'     , DIRAC_INSTALL )
    """
     First define some defaults
    """
    self.diracSetup         = gConfig.getValue( '/DIRAC/Setup', DIRAC_SETUP )
    self.pilot              = DIRAC_PILOT
    self.diracVersion       = DIRAC_VERSION
    self.install            = DIRAC_INSTALL
    
    self.enableListMatch    = ENABLE_LISTMATCH
    self.listMatchDelay     = LISTMATCH_DELAY
    self.gridEnv            = GRIDENV
    self.loggingServers     = [ LOGGING_SERVER ]
    self.genericPilotDN     = PILOT_DN
    self.genericPilotGroup  = PILOT_GROUP
    self.timePolicy         = TIME_POLICY
    self.requirements       = REQUIREMENTS
    self.rank               = RANK
    self.fuzzyRank          = FUZZY_RANK
    
    self.configureFromSection( csSection )
    """
     Common Configuration can be overwriten for each Flavour
    """
    mySection   = csSection+'/'+self.flavour
    self.configureFromSection( mySection )
    """
     And Again for each Platform
    """
    mySection   = csSection+'/'+platform
    self.configureFromSection( mySection )

    self.log.info( '===============================================' )
    self.log.info( 'Configuration:' )
    self.log.info( '' )
    self.log.info( ' Install script: ', self.install )
    self.log.info( ' Pilot script:   ', self.pilot )
    self.log.info( ' DIRAC Version:  ', self.diracVersion )
    self.log.info( ' DIRAC Setup:    ', self.diracSetup )
    self.log.info( ' ListMatch:      ', self.enableListMatch )
    if self.enableListMatch:
      self.log.info( ' ListMatch Delay:', self.listMatchDelay )
    if self.gridEnv:
      self.log.info( ' GridEnv:        ', self.gridEnv )
    if self.resourceBrokers:
      self.log.info( ' ResourceBrokers:', ', '.join(self.resourceBrokers) )


  def configureFromSection( self, mySection ):

    self.pilot              = gConfig.getValue( mySection+'/PilotScript'       , self.pilot )
    self.diracVersion       = gConfig.getValue( mySection+'/DIRACVersion'      , self.diracVersion )
    self.diracSetup         = gConfig.getValue( mySection+'/Setup'             , self.diracSetup )
    self.install            = gConfig.getValue( mySection+'/InstallScript'     , self.install )

    self.enableListMatch    = gConfig.getValue( mySection+'/EnableListMatch'   , self.enableListMatch )
    self.listMatchDelay     = gConfig.getValue( mySection+'/ListMatchDelay'    , self.listMatchDelay )
    self.gridEnv            = gConfig.getValue( mySection+'/GridEnv     '      , self.gridEnv )
    self.resourceBrokers    = gConfig.getValue( mySection+'/ResourceBrokers'   , self.resourceBrokers )
    self.genericPilotDN     = gConfig.getValue( mySection+'/GenericPilotDN'    , self.genericPilotDN )
    self.genericPilotGroup  = gConfig.getValue( mySection+'/GenericPilotGroup' , self.genericPilotGroup )
    self.timePolicy         = gConfig.getValue( mySection+'/TimePolicy'        , self.timePolicy )
    self.requirements       = gConfig.getValue( mySection+'/Requirements'      , self.requirements )
    self.rank               = gConfig.getValue( mySection+'/Rank'              , self.rank )
    self.fuzzyRank          = gConfig.getValue( mySection+'/FuzzyRank'         , self.fuzzyRank )

  def submitPilot(self, jobDict, director):
    """
      Submit pilot for the given job, this is done from the Thread Pool job
    """
    ceMask = self.__resolveCECandidates( jobDict )
    if not ceMask: return S_ERROR( 'No CE available for job' )

    job = jobDict['JobID']
    workingDirectory = os.path.join( self.workDir, job)

    if os.path.isdir( workingDirectory ):
      shutil.rmtree( workingDirectory )
    elif os.path.lexists( workingDirectory ):
      os.remove( workingDirectory )

    os.makedirs(workingDirectory)

    inputSandbox = []
    pilotOptions = []
    if jobDict['PilotType'].lower()=='private':
      self.log.verbose('Job %s will be submitted with a privat pilot' % job)
      # Owner requirement
      pilotOptions.append( '-O %s' % jobDict['Owner'] )
      ownerDN    = jobDict['OwnerDN']
      ownerGroup = jobDict['OwnerGroup']
    else:
      self.log.verbose('Job %s will be submitted with a generic pilot' % job)
      ownerDN    = self.genericPilotDN
      ownerGroup = self.genericPilotGroup

    # User Group requirement
    pilotOptions.append( '-G %s' % ownerGroup )
    # Requested version of DIRAC
    pilotOptions.append( '-v %s' % self.diracVersion )
    # Requested CPU time
    pilotOptions.append( '-T %s' % jobDict['MaxCPUTime'] )
    # Default Setup. It may be overwriten by the Arguments in the Job JDL
    pilotOptions.append( '-o /DIRAC/Setup=%s' % self.diracSetup )

    # Write JDL
    jdl, jobRequirements = self.__prepareJDL( jobDict, pilotOptions, ceMask )
    if not jdl:
      shutil.rmtree( workingDirectory )
      return S_ERROR( 'Could not create JDL:', job )

    # get a valid proxy
    ret = gProxyManager.downloadVOMSProxy( ownerDN, ownerGroup, requiredVOMSAttribute = True )
    if not ret['OK']:
      self.log.error( ret['Message'] )
      self.log.error( 'Could not get proxy:', 'User "%s", Group "%s"' % ( ownerDN, ownerGroup ) )
      shutil.rmtree( workingDirectory )
      return S_ERROR( 'Could not get proxy' )
    proxy = ret['Value']

    # Check that there are available queues for the Job:
    if self.enableListMatch:
      availableCEs = False
      now = Time.datetime()
      if not 'AvailableCEs' in jobDict:
        availableCEs = self.__listMatch( proxy, job, jdl )
        jobDict['LastListMatch'] = now
      else:
        avaliableCEs = jobDict['AvailableCEs']
        if not Time.timeInterval( jobDict['LastListMatch'], 
                                  self.listMatchDelay * Time.minute  ).includes( now ):
          availableCEs = self.__listMatch( proxy, job, jdl )
          jobDict['LastListMatch'] = now

      jobDict['AvailableCEs']  = availableCEs

      if type(availableCEs) == types.ListType :
        jobDB.setJobParameter( job, 'Available_CEs' , '%s CEs returned from list-match on %s' %
                               ( len(availableCEs), Time.toString() ) )
      if not availableCEs:
        # FIXME: set Job Minor Status
        shutil.rmtree( workingDirectory )
        return S_ERROR( 'No queue available for job' )

    # Now we are ready for the actual submission, so 

    self.log.verbose('Submitting Pilot Agent for job:', job )
    pilotReference = self.__submitPilot( proxy, job, jdl )
    shutil.rmtree( workingDirectory )

    # Now, update the job Minor Status 
    for ref in pilotReference:
      ret = pilotAgentsDB.addPilotReference( job, ref, ownerDN, ownerGroup, jobRequirements )
    
    return

  def _JobJDL(self, jobDict, pilotOptions, ceMask ):
    """
     The Job JDL is the same for LCG and GLite
    """

    if 'GridExecutable' in jobDict:
      # if an executable is given it is assume to be in the same location as the pilot
      jobJDL = 'Executable     = "%s";\n' % os.path.basename( jobDict['GridExecutable'] )
      executable = os.path.join( os.path.dirname( self.pilot ), jobDict['GridExecutable'] )
    else:
      jobJDL = 'Executable     = "%s";\n' % os.path.basename( self.pilot )
      executable = self.pilot
    
    jobJDL += 'Arguments     = "%s";\n' % ' '.join( pilotOptions )

    jobJDL += 'TimeRef       = %s;\n' % jobDict['MaxCPUTime']

    jobJDL += 'TimePolicy    = ( %s );\n' % self.timePolicy

    requirements = self.requirements

    siteRequirements = '\n || '.join( [ 'other.GlueCEInfoHostName == "%s"' % s for s in ceMask ] ) 
    requirements.append( "( %s|n )" %  siteRequirements )
    
    if 'SoftwareTag' in jobDict:
      for tag in jobDict['SoftwareTag']:
        requirements.append('Member( "%s" , other.GlueHostApplicationSoftwareRunTimeEnvironment )' % tag)

    jobRequirements = '\n && '.join( requirements )

    jobJDL += 'jobRequirements  = %s;\n' % jobRequirements

    jobJDL += 'Rank          = %s;\n' % self.rank 
    jobJDL += 'FuzzyRank     = %s;\n' % self.fuzzyRank
    jobJDL += 'StdOutput     = "std.out";\n'
    jobJDL += 'StdError      = "std.err";\n'

    jobJDL += 'InputSandbox  = { "%s" };\n' % '", "'.join( [ self.install, executable ] )

    jobJDL += 'OutputSandbox = { "std.out", "std.err" };\n' 

    return (jobJDL,jobRequirements)

  def _gridCommand(self, proxy, cmd):
    """
     Execute cmd tuple after sourcing GridEnv
    """
    gridEnv = None
    if self.gridEnv:
      self.log.verbose( 'Sourcing GridEnv script:', self.gridEnv )
      ret = Source( 60, self.gridEnv )
      if not ret['OK']:
        self.log.error( 'Failed sourcing GridEnv:', ret['Message'] )
        return S_ERROR( 'Failed sourcing GridEnv' )
      if ret['stdout']: self.log.verbose( ret['stdout'] )
      if ret['stderr']: self.log.warn( ret['stderr'] )
      gridEnv = ret['outputEnv']

    ret = gProxyManager.dumpProxyToFile( proxy )
    if not ret['OK']:
      return ret
    gridEnv[ 'X509_USER_PROXY' ] = ret['Value']
    self.log.debug( 'Executing', ' '.join(cmd) )
    return systemCall( 60, cmd, env = gridEnv )
    

  def callBack(self, threadedJob, submitResult):
    return
  def exceptionCallBack(self, threadedJob, exceptionInfo ):
    return
  
  
  
  def __prepareJDL(self, jobDict, pilotOptions, ceMask ):
    """
      This method should be overridden in a subclass
    """
    self.log.error( '__prepareJDL() method should be implemented in a subclass' )
    sys.exit()
  
  def __resolveCECandidates( self, jobDict ):
    """
      Return a list of CE's 
    """
    # assume user knows what they're doing and avoid site mask e.g. sam jobs
    if 'GridRequirements' in jobDict:
      return jobDict['GridRequirements']

    # Get the mask
    ret = jobDB.getSiteMask()
    if not ret['OK']:
      self.log.error( 'Can not retrieve site Mask from DB:', ret['Message'] )
      return []

    siteMask = ret['Value']
    if not siteMask:
      self.log.error( 'Site mask is empty' )
      return []
    
    self.log.verbose( 'Site Mask: %s' % ', '.join(siteMask) )

    # remove banned sites from siteMask
    for site in jobDict['BannedSites']:
      if site in siteMask:
        siteMask.remove(site)
        self.log.verbose('Removing banned site %s from site Mask' % site )
    
    
    for site in siteMask:
      # remove from the mask if a Site is given
      if jobDict['Site'] and not site in jobDict['Site']:
        siteMask.remove(site)
        self.log.verbose('Removing site %s from the Mask' % site )

    if not siteMask:
      # job can not be submitted
      # FIXME: the best is to use the ApplicationStatus to report this, this will allow 
      # further iterations to consider the job as candidate without any further action
      jobDB.setJobStatus( jobDict['JobID'], application='No Candidate Sites in Mask' )      
      return []

    self.log.info( 'Candidates Sites for Job %s:' % jobDict['JobID'], ', '.join(siteMask) )

    # Get CE's associates to the given site Names
    ceMask = []

    section = '/Resources/Sites/%s' % self.flavour
    ret = gConfig.getSections(section)
    if not ret['OK']:
      # To avoid duplicating sites listed in LCG for gLite for example.  
      # This could be passed as a parameter from
      # the sub class to avoid below...
      section = '/Resources/Sites/LCG'
      ret = gConfig.getSections(section)

    if not ret['OK'] or not ret['Value']:
      self.log.error( 'Could not obtain CEs from CS', ret['Message'] )
      return []

    gridSites = sites['Value']

    for siteName in gridSites.items():
      if siteName in siteMask:
        ret = gConfig.getValue( '%s/%s/CE' % ( section, siteName), [] )
        if ret['OK']:
          ceMask.extend( ret['Value'])

    if not ceMask:
      self.log.error( 'No CE found for requested Sites:', ', '.join(siteMask) )    

    return ceMask

  def parseListMatchStdout(self, proxy, cmd, job):
    """
      Parse List Match stdout to return list of matched CE's
    """
    self.log.verbose( 'Executing List Match for job:', job )
    
    start = time.time()
    ret = self._gridCommand( proxy, cmd )
    
    if not ret['OK']:
      self.log.error( 'Failed to execute List Match', ret['Message'] )
      return False
    if ret['Value'][0] != 0:
      self.log.error( 'Error executing List Match:', '\n'.join( ret['Value'] ) )
      return False
    self.log.info( 'List Match Execution Time:', time.time()-start )

    stdout = ret['Value'][1]
    stderr = ret['Value'][2]
    availableCEs = []
    # Parse std.out
    for line in List.fromChar(stdout,'\n'):
      if re.match('jobmanager',line):
        # FIXME: the line has to be stripped from extra info
        availableCEs.append(line)
    
    if not availableCEs:
      self.log.info( 'List-Match failed to find CEs for Job:', job )
      self.log.info( stdout )
      self.log.info( stderr )
    else:
      self.log.debug( 'List-Match returns:', '\n'.join( ret['Value'] ) )
      self.log.info( 'List-Match found %s CEs for Job:' % len(availableCEs), job )
      self.log.verbose( ', '.join(availableCEs) )
    
    return availableCEs

  def parseJobSubmitStdout(self, proxy, cmd, job):
    """
      Parse Job Submit stdout to return job reference
    """
    start = time.time()
    self.log.verbose( 'Executing Job Submit for job:', job )
    
    ret = self._gridCommand( proxy, cmd )
    
    if not ret['OK']:
      self.log.error( 'Failed to execute Job Submit', ret['Message'] )
      return False
    if ret['Value'][0] != 0:
      self.log.error( 'Error executing Job Submit:', '\n'.join( ret['Value'] ) )
      return False
    self.log.info( 'Job Submit Execution Time:', time.time()-start )

    stdout = ret['Value'][1]
    stderr = ret['Value'][2]

    submittedPilot = None

    failed = 1
    for line in List.fromChar(stdout,'\n'):
      m = re.search("(https:\S+)",line)
      if (m):
        glite_id = m.group(1)
        submittedPilot = glite_id
        self.log.info( 'Reference %s for job %s' % ( glite_id, job ) )
        failed = 0
    if failed:
      self.log.error( 'Job Submit returns no Reference:', '\n'.join( ret['Value'] ) )

    return glite_id

  def __writeJDL(self, filename, jdlList):
    try:
      f = open(filename,'w')
      f.write( '\n'.join( jdlList) )
      f.close()
    except Exception, x:
      self.log.exception( x )
      return ''
    
    return filename

class gLitePilotDirector(PilotDirector):
  def __init__(self):
    self.flavour = 'gLite'
    PilotDirector.__init__(self)

  def configure(self, csSection, platform):
    """
     Here goes especific configuration for gLite PilotDirectors
    """
    PilotDirector.configure(self, csSection, platform )
    self.loggingServers = gConfig.getValue( csSection+'/LoggingServers'   , self.loggingServers )
    mySection = csSection+'/'+self.flavour
    self.loggingServers = gConfig.getValue( mySection+'/LoggingServers'   , self.loggingServers )
    mySection = csSection+'/'+platform
    self.loggingServers = gConfig.getValue( mySection+'/LoggingServers'   , self.loggingServers )
    if self.loggingServers:
      self.log.info( ' LoggingServers:', ', '.join(self.loggingServers) )
    self.log.info( '' )
    self.log.info( '===============================================' )

  def __prepareJDL(self, jobDict, pilotOptions, ceMask ):
    """
      Write JDL for Pilot Submission
    """
    RBs = []
    for RB in self.resourceBrokers:
      RBs.append( '"https://%s:7443/glite_wms_wmproxy_server"' % RB )

    LBs = []
    for LB in self.loggingServers:
      LBs.append = '"https://%s:9000"' % LB
    
    wmsClientJDL = """
WmsClient = [
requirements = jobRequirements && other.GlueCEStateStatus == "Production";
ErrorStorage = "%s/Error";
OutputStorage = "%s/jobOutput";
# ListenerPort = 44000;
ListenerStorage = "%s/Storage";
VirtualOrganisation = "lhcb";
RetryCount = 0;
ShallowRetryCount = 0;
WMProxyEndPoints = { %s };
LBEndPoints = { %s };
MyProxyServer = "myproxy.cern.ch";
];
""" % ( self.workDir, self.workDir, self.workDir, ', '.join(RBs), ', '.join(LBs) )


    (jobJDL , jobRequirements) = self._JobJDL( jobDict, pilotOptions, ceMask )

    jdl = os.path.join( self.workdir, '%s.jdl' % jobDict['JobID'] )
    jdl = self.__writeJDL( jdl, [jobJDL, wmsClientJDL] )

    return (jdl, jobRequirements)

  def __listMatch(self, proxy, job, jdl):
    """
     Check the number of available queues for the jobs to prevent submission
     if there are no matching resources.
    """
    cmd = [ 'glite-wms-job-list-match', '-a', '-c', '%s' % jdl, '%s' % jdl ]
    return self.parseListMatchStdout( proxy, cmd, job )
  
  def __submitPilot(self, proxy, job, jdl):
    """
     Submit pilot and get back the reference
    """
    cmd = [ 'glite-wms-job-sumit', '-a', '-c', '%s' % jdl, '%s' % jdl ]
    return self.parseJobSubmitStdout( proxy, cmd, job )

class LCGPilotDirector(PilotDirector):
  def __init__(self):
    self.flavour = 'LCG'
    PilotDirector.__init__(self)
  def configure(self, csSection, platform):
    """
     Here goes especific configuration for LCG PilotDirectors
    """
    PilotDirector.configure(self, csSection, platform )
    self.log.info( '' )
    self.log.info( '===============================================' )

  def __prepareJDL(self, jobDict, pilotOptions, ceMask ):
    """
      Write JDL for Pilot Submission
    """
    # RB = List.randomize( self.resourceBrokers )[0]
    LDs = []
    NSs = []
    LBs = []
    for RB in self.resourceBrokers:
      LDs.append( '"%s:9002"' % RB )
      NSs.append( '"%s:7772"' % RB )
      LBs.append( '"%s:9000"' % RB )

    LD = ', '.join(LDs)
    NS = ', '.join(NSs)
    LB = ', '.join(LBs)

    rbJDL = """
requirements = jobRequirements && other.GlueCEStateStatus == "Production";
RetryCount = 0;
ErrorStorage = "%s/Error";
OutputStorage = "%s/jobOutput";
# ListenerPort = 44000;
ListenerStorage = "%s/Storage";
VirtualOrganisation = "lhcb";
LoggingTimeout = 30;
LoggingSyncTimeout = 30;
LoggingDestination = { %s };
# Default NS logger level is set to 0 (null)
# max value is 6 (very ugly)
NSLoggerLevel = 0;
DefaultLogInfoLevel = 0;
DefaultStatusLevel = 0;
NSAddresses = { %s };
LBAddresses = { %s };
MyProxyServer = "myproxy.cern.ch";
""" % (self.workDir, self.workDir, self.workDir, LD, NS, LB)

    jobJDL,jobRequirements = self._JobJDL( jobDict, pilotOptions, ceMask )

    jdl = os.path.join( self.workdir, '%s.jdl' % jobDict['JobID'] )
    jdl = self.__writeJDL( jdl, [jobJDL, rbJDL] )

    return ( jdl, jobRequirements)

  def __listMatch(self, proxy, job, jdl):
    """
     Check the number of available queues for the jobs to prevent submission
     if there are no matching resources.
    """
    cmd = ['edg-job-list-match','-c','%s' % jdl , '--conf-vo', '%s' % jdl ,'%s' % jdl]
    return self.parseListMatchStdout( proxy, cmd, job )

  def __submitPilot(self, proxy, job, jdl):
    """
     Submit pilot and get back the reference
    """
    cmd = [ 'edg-job-sumit', '-c', '%s' % jdl, '%s' % jdl ]
    return self.parseJobSubmitStdout( proxy, cmd, job )
