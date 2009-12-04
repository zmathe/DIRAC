-- $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/Core/Transformation/TransformationDB.sql,v 1.15 2009/08/26 07:17:46 rgracian Exp $
-- -------------------------------------------------------------------------------
--  Schema definition for the TransformationDB database a generic
--  engine to define input data streams and support dynamic data 
--  grouping per unit of execution.

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS Transformations;
CREATE TABLE Transformations (
    TransformationID INTEGER NOT NULL AUTO_INCREMENT,
    TransformationName VARCHAR(255) NOT NULL,
    Description VARCHAR(255),
    LongDescription  BLOB,
    CreationDate DATETIME,
    AuthorDN VARCHAR(255) NOT NULL,
    AuthorGroup VARCHAR(255) NOT NULL,
    Type CHAR(16) DEFAULT 'Simulation',
    Plugin CHAR(16) DEFAULT 'None',
    AgentType CHAR(16) DEFAULT 'Manual',
    Status  CHAR(16) DEFAULT 'New',
    FileMask VARCHAR(255),
    TransformationGroup varchar(64) NOT NULL default 'General',
    GroupSize INT NOT NULL DEFAULT 1,
    InheritedFrom INTEGER DEFAULT 0,
    Body BLOB,
    MaxNumberOfJobs INT NOT NULL DEFAULT 0,
    EventsPerJob INT NOT NULL DEFAULT 0,
    PRIMARY KEY(TransformationID),
    INDEX(TransformationName)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS AdditionalParameters;
CREATE TABLE AdditionalParameters (
    TransformationID INTEGER NOT NULL,
    ParameterName VARCHAR(32) NOT NULL,
    ParameterValue BLOB NOT NULL,
    PRIMARY KEY(TransformationID,ParameterName)
);

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS TransformationLog;
CREATE TABLE TransformationLog (
    TransformationID INTEGER NOT NULL,
    Message VARCHAR(255) NOT NULL,
    Author VARCHAR(255) NOT NULL DEFAULT "Unknown",
    MessageDate DATETIME NOT NULL,
    INDEX (TransformationID),
    INDEX (MessageDate)
);

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS Jobs;
CREATE TABLE Jobs (
JobID INTEGER NOT NULL AUTO_INCREMENT,
TransformationID INTEGER NOT NULL,
WmsStatus char(16) DEFAULT 'Created',
JobWmsID char(16) DEFAULT '',
TargetSE char(32) DEFAULT 'Unknown',
CreationTime DATETIME NOT NULL,
LastUpdateTime DATETIME NOT NULL,
PRIMARY KEY(TransformationID,JobID),
INDEX(WmsStatus)
);

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS JobInputs;
CREATE TABLE JobInputs (
TransformationID INTEGER NOT NULL,
JobID INTEGER NOT NULL,
InputVector BLOB,
PRIMARY KEY(TransformationID,JobID)
);

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS DataFiles;
CREATE TABLE DataFiles (
   FileID INTEGER NOT NULL AUTO_INCREMENT,
   LFN VARCHAR(255) UNIQUE,
   Status varchar(32) DEFAULT 'AprioriGood',
   INDEX (Status),
   PRIMARY KEY (FileID, LFN)
);

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS Replicas;
CREATE TABLE Replicas (
  FileID INTEGER NOT NULL,
  PFN VARCHAR(255),
  SE VARCHAR(32),
  Status VARCHAR(32) DEFAULT 'AprioriGood',
  INDEX (Status),
  PRIMARY KEY (FileID, SE)
);

-- -------------------------------------------------------------------------------
DROP TABLE IF EXISTS FileTransformations;
CREATE TABLE FileTransformations(
   FileID INTEGER NOT NULL,
   TransformationID INTEGER NOT NULL,
   TransformationType VARCHAR(32),
   PRIMARY KEY (FileID, TransformationID)
);
