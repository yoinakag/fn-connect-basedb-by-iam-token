1. ssh to basedb node
ssh opc@193.122.140.64

2. change to oracle user
[opc@basedb23ai ~]$ sudo su - oracle
Last login: Fri Aug  1 06:34:03 UTC 2025

3. connect to basedb
[oracle@basedb23ai ~]$ sqlplus / as sysdba

SQL*Plus: Release 23.0.0.0.0 - for Oracle Cloud and Engineered Systems on Fri Aug 1 06:35:58 2025
Version 23.8.0.25.04

Copyright (c) 1982, 2025, Oracle.  All rights reserved.


Connected to:
Oracle Database 23ai EE High Perf Release 23.0.0.0.0 - for Oracle Cloud and Engineered Systems
Version 23.8.0.25.04

SQL>

4. create user pdbuser01

SQL> show pdbs;

    CON_ID CON_NAME                       OPEN MODE  RESTRICTED
---------- ------------------------------ ---------- ----------
         2 PDB$SEED                       READ ONLY  NO
         3 DB0801_PDB1                    READ WRITE NO
SQL> alter session set container=DB0801_PDB1;

Session altered.

SQL> create user pdbuser01 identified by WElcome##123456;

User created.

SQL> grant connect,resource to pdbuser01;

Grant succeeded.

SQL> exit
Disconnected from Oracle Database 23ai EE High Perf Release 23.0.0.0.0 - for Oracle Cloud and Engineered Systems
Version 23.8.0.25.04

5. Test pdbuser01 connection
    - $ORACLE_HOME/network/admin/listener.ora
    - $ORACLE_HOME/network/admin/sqlnet.ora
    - $ORACLE_HOME/network/admin/tnsnames.ora

5.1 on dbserver using sqlplus
[oracle@basedb23ai ~]$ lsnrctl status

LSNRCTL for Linux: Version 23.0.0.0.0 - for Oracle Cloud and Engineered Systems on 01-AUG-2025 06:40:25

Copyright (c) 1991, 2025, Oracle.  All rights reserved.

Connecting to (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=basedb23ai.subnet07111020.vcn04201554.oraclevcn.com)(PORT=1521)))
STATUS of the LISTENER
------------------------
Alias                     LISTENER
Version                   TNSLSNR for Linux: Version 23.0.0.0.0 - for Oracle Cloud and Engineered Systems
Start Date                01-AUG-2025 06:17:18
Uptime                    0 days 0 hr. 23 min. 6 sec
Trace Level               off
Security                  ON: Local OS Authentication
SNMP                      OFF
Listener Parameter File   /u01/app/oracle/product/23.0.0/dbhome_1/network/admin/listener.ora
Listener Log File         /u01/app/oracle/diag/tnslsnr/basedb23ai/listener/alert/log.xml
Listening Endpoints Summary...
  (DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=basedb23ai.subnet07111020.vcn04201554.oraclevcn.com)(PORT=1521)))
  (DESCRIPTION=(ADDRESS=(PROTOCOL=ipc)(KEY=EXTPROC1521)))
  (DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=basedb23ai.subnet07111020.vcn04201554.oraclevcn.com)(PORT=2484)))
Services Summary...
Service "330d3a56f99f26b6e0635c08f40af437.subnet07111020.vcn04201554.oraclevcn.com" has 1 instance(s).
  Instance "DB0801", status READY, has 1 handler(s) for this service...
Service "DB0801XDB.subnet07111020.vcn04201554.oraclevcn.com" has 1 instance(s).
  Instance "DB0801", status READY, has 1 handler(s) for this service...
Service "DB0801_DB0801_PDB1.paas.oracle.com" has 1 instance(s).
  Instance "DB0801", status READY, has 1 handler(s) for this service...
Service "DB0801_vh3_iad.subnet07111020.vcn04201554.oraclevcn.com" has 1 instance(s).
  Instance "DB0801", status READY, has 1 handler(s) for this service...
Service "db0801_pdb1.subnet07111020.vcn04201554.oraclevcn.com" has 1 instance(s).
  Instance "DB0801", status READY, has 1 handler(s) for this service...
The command completed successfully

add below content to tnsnames.ora
$ vi $ORACLE_HOME/network/admin/tnsnames.ora
pdb01 =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = basedb23ai.subnet07111020.vcn04201554.oraclevcn.com)(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = db0801_pdb1.subnet07111020.vcn04201554.oraclevcn.com)
    )
  )

$ lsnrctl stop
$ lsnrctl start
$ sqlplus pdbuser01/WElcome##123456@pdb01

5.2 connect by using sqldeveloper
 - Name: basedb23ai
 - Username: pdbuser01
 - Password: WElcome##123456
 - Host: 193.122.140.64
 - Port: 1521
 - Service Name: db0801_pdb1.subnet07111020.vcn04201554.oraclevcn.com

Test connection successfully !

