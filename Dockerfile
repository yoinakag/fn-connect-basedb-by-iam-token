FROM oraclelinux:9-slim

WORKDIR /function

RUN groupadd --gid 1000 fn && adduser --uid 1000 --gid fn fn

RUN microdnf -y install python3 python3-pip && \
    microdnf clean all

RUN microdnf install oracle-instantclient-release-23ai-el9
RUN microdnf install oracle-instantclient-basic

ENV LD_LIBRARY_PATH=/usr/lib/oracle/23/client64/lib
ENV OCI_RESOURCE_PRINCIPAL_VERSION=2.2
ENV PATH=/usr/lib/oracle/23/client64/bin:$PATH
ENV PYTHONPATH=/function

ADD . /function/

RUN chown -R fn:fn /function

RUN mkdir /tmp/dbwallet
RUN chown -R fn:fn /tmp/dbwallet

ENV TNS_ADMIN=/tmp/dbwallet

RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r /function/requirements.txt && \
    rm -f /function/requirements.txt /function/README.md /function/Dockerfile /function/func.yaml

ENV PYTHONPATH=/python

ENTRYPOINT ["/usr/local/bin/fdk", "/function/func.py", "handler"]