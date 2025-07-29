FROM oraclelinux:9-slim

WORKDIR /function

RUN groupadd --gid 1000 fn && adduser --uid 1000 --gid fn fn

RUN microdnf -y install python3 python3-pip && \
    microdnf clean all

RUN microdnf install oracle-instantclient-release-23ai-el9
RUN microdnf install oracle-instantclient-basic

RUN microdnf -y install openssl ca-certificates && \
    microdnf clean all

RUN mkdir /tmp/.oci && chown -R fn:fn /tmp/.oci

RUN echo "132.145.147.69 basedb.subnet07111020.vcn04201554.oraclevcn.com basedb" >> /etc/hosts

RUN  openssl s_client -connect 132.145.147.69:1522 </dev/null 2>/dev/null \
    | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /etc/pki/ca-trust/source/anchors/dbcert.crt
RUN update-ca-trust

ENV LD_LIBRARY_PATH=/usr/lib/oracle/23/client64/lib
ENV OCI_RESOURCE_PRINCIPAL_VERSION=2.2
ENV PATH=/usr/lib/oracle/23/client64/bin:$PATH
ENV TNS_ADMIN=/tmp/instant23ai
ENV PYTHONPATH=/function

ADD . /function/

RUN mkdir -p /tmp/instant23ai && chown -R fn:fn /tmp/instant23ai
COPY instant23ai/. /tmp/instant23ai/
RUN chown -R fn:fn /tmp/instant23ai

RUN sed -i "s/basedb_service_name/pdb01.subnet07111020.vcn04201554.oraclevcn.com/g" /tmp/instant23ai/tnsnames.ora

RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r /function/requirements.txt && \
    rm -f /function/requirements.txt /function/README.md /function/Dockerfile /function/func.yaml

ENV PYTHONPATH=/python

RUN ls -la /tmp && ls -la /tmp/instant23ai
ENTRYPOINT ["/usr/local/bin/fdk", "/function/func.py", "handler"]