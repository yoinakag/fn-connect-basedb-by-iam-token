import io
import os
import json
import oracledb
from fdk import response

# Get connection parameters from enviroment
basedb_region = os.getenv("BASEDB_REGION")
basedb_compartment_ocid = os.getenv("BASEDB_COMPARTMENT_OCID")
basedb_ocid = os.getenv("BASEDB_OCID")

class TokenHandlerIAM:

    def __init__(self,
                 dir_name="/tmp/.oci/db-token/",
                 command="oci iam db-token get --auth instance_principal --region {} --scope urn:oracle:db::id::{}::{}".format(basedb_region,basedb_compartment_ocid,basedb_ocid)):
        self.dir_name = dir_name
        self.command = command
        self.token = None
        self.private_key = None

    def __call__(self, refresh):
        if refresh:
            if os.system(self.command) != 0:
                raise Exception("token command failed!")
        if self.token is None or refresh:
            self.read_token_info()
        return (self.token, self.private_key)

    def read_token_info(self):
        token_file_name = os.path.join(self.dir_name, "token")
        pkey_file_name = os.path.join(self.dir_name, "oci_db_key.pem")
        with open(token_file_name) as f:
            self.token = f.read().strip()
        with open(pkey_file_name) as f:
            if oracledb.is_thin_mode():
                self.private_key = f.read().strip()
            else:
                lines = [s for s in f.read().strip().split("\n")
                         if s not in ('-----BEGIN PRIVATE KEY-----',
                                      '-----END PRIVATE KEY-----')]
                self.private_key = "".join(lines)


oracledb.init_oracle_client(lib_dir="/usr/lib/oracle/23/client64/lib",config_dir="/tmp/instant23ai")

#
# Function Handler: executed every time the function is invoked
#
def handler(ctx, data: io.BytesIO = None):
    return read_all_users(ctx)

def read_all_users(ctx):
    try:
        sql_statement = """
            SELECT 1+1
            FROM dual
        """
        with oracledb.connect(
            access_token=TokenHandlerIAM(),
            dsn="iam",
            externalauth=True
        ) as dbconnection:
            with dbconnection.cursor() as dbcursor:
                dbcursor.execute(sql_statement)
                dbcursor.rowfactory = lambda *args: dict(zip([d[0] for d in dbcursor.description], args))
                results = dbcursor.fetchall()

                for result in results:
                    if result.get("CREATED_ON"):
                        result["CREATED_ON"] = result["CREATED_ON"].isoformat()

                return response.Response(
                    ctx,
                    response_data=json.dumps(results),
                    headers={"Content-Type": "application/json"}
                )

    except Exception as ex:
        print('ERROR: Failed to read all users', ex, flush=True)
        raise