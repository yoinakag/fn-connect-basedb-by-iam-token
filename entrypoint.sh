#!/bin/bash
set -e

# echo "${BASEDB_IP} ${BASEDB_CONNECTION_URL} basedb" >> /etc/hosts

sed -i "s/basedb_service_name/${BASEDB_SERVICE_NAME}/g" /tmp/instant23ai/tnsnames.ora

# openssl s_client -connect basedb:1522 </dev/null 2>/dev/null \
#   | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /etc/pki/ca-trust/source/anchors/dbcert.crt

# update-ca-trust

exec /usr/local/bin/fdk /function/func.py handler
