#!/usr/bin/env python
########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/FrameworkSystem/scripts/dirac-proxy-info.py,v 1.4 2008/10/21 10:43:12 acasajus Exp $
# File :   dirac-proxy-init.py
# Author : Adrian Casajus
########################################################################
__RCSID__   = "$Id: dirac-proxy-info.py,v 1.4 2008/10/21 10:43:12 acasajus Exp $"
__VERSION__ = "$Revision: 1.4 $"

import sys
import os.path
from DIRACEnvironment import DIRAC
from DIRAC.Core.Base import Script


class Params:

  proxyLoc = False
  checkExists = False
  vomsEnabled = True
  csEnabled = True
  steps = False

  def showVersion( self, arg ):
    print "Version:"
    print " ", __RCSID__
    print " ", __VERSION__
    sys.exit(0)
    return DIRAC.S_OK()

  def setProxyLocation( self, arg ):
    self.proxyLoc = arg
    return DIRAC.S_OK()

  def checkExists( self, arg ):
    self.checkExists = True
    return DIRAC.S_OK()

  def disableVOMS( self, arg ):
    self.vomsEnabled = False
    return DIRAC.S_OK()

  def disableCS( self, arg ):
    self.csEnabled = False
    return DIRAC.S_OK()

  def showSteps( self, arg ):
    self.steps = True
    return DIRAC.S_OK()

params = Params()

Script.registerSwitch( "f:", "file=", "File to use as user key", params.setProxyLocation )
Script.registerSwitch( "i", "version", "Print version", params.showVersion )
Script.registerSwitch( "n", "novoms", "Disable VOMS", params.disableVOMS )
Script.registerSwitch( "x", "nocs", "Disable CS", params.disableCS )
Script.registerSwitch( "e", "steps", "Show steps info", params.showSteps )

Script.disableCS()
Script.parseCommandLine()

if params.csEnabled:
  retVal = Script.enableCS()
  if not retVal[ 'OK' ]:
    print "Cannot contact CS to get user list"

from DIRAC.Core.Security.Misc import *

result = getProxyInfo( params.proxyLoc, not params.vomsEnabled )
if not result[ 'OK' ]:
  print "Error: %s" % result[ 'Message' ]
infoDict = result[ 'Value' ]
print formatProxyInfoAsString( infoDict )

if params.steps:
  print "== Steps extended info =="
  chain = infoDict[ 'chain' ]
  stepInfo = getProxyStepsInfo( chain )[ 'Value' ]
  print formatProxyStepsInfoAsString( stepInfo )

sys.exit(0)