import io
import os
import oci
import json
import oracledb
from fdk import response
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def _get_key_pair():
    """
    Generates a public-private key pair for proof of possession.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    if not oracledb.is_thin_mode():
        p_key = "".join(
            line.strip()
            for line in private_key_pem.splitlines()
            if not (
                line.startswith("-----BEGIN") or line.startswith("-----END")
            )
        )
        private_key_pem = p_key

    return {"private_key": private_key_pem, "public_key": public_key_pem}

def _generate_access_token(client, token_auth_config):
    """
    Token generation logic used by authentication methods.
    """
    key_pair = _get_key_pair()
    scope = token_auth_config.get("scope", "urn:oracle:db::id::*")

    details = oci.identity_data_plane.models.GenerateScopedAccessTokenDetails(
        scope=scope, public_key=key_pair["public_key"]
    )
    response = client.generate_scoped_access_token(
        generate_scoped_access_token_details=details
    )

    return (response.data.token, key_pair["private_key"])

def _generate_access_token(client, token_auth_config):
    """
    Token generation logic used by authentication methods.
    """
    key_pair = _get_key_pair()
    scope = token_auth_config.get("scope", "urn:oracle:db::id::*")

    details = oci.identity_data_plane.models.GenerateScopedAccessTokenDetails(
        scope=scope, public_key=key_pair["public_key"]
    )
    response = client.generate_scoped_access_token(
        generate_scoped_access_token_details=details
    )

    return (response.data.token, key_pair["private_key"])

print("init")
# Get connection parameters from enviroment
basedb_region = os.getenv("BASEDB_REGION")
basedb_compartment_ocid = os.getenv("BASEDB_COMPARTMENT_OCID")
basedb_ocid = os.getenv("BASEDB_OCID")
print("get parameter")

scope = "urn:oracle:db::id::{}::{}".format(basedb_region,basedb_compartment_ocid,basedb_ocid)
oracledb.init_oracle_client(lib_dir="/usr/lib/oracle/23/client64/lib",config_dir="/tmp/instant23ai")
print("init oracle client")

# signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
signer = oci.auth.signers.get_resource_principals_signer()
client = oci.identity_data_plane.DataplaneClient(config={}, signer=signer)
token_auth_config = {
    "scope":"urn:oracle:db::id::ocid1.compartment.oc1..aaaaaaaardb3dtrfgv5dde2rqisd44p3f6ihjtbd3gnbtwq64nq6lzngxotq::ocid1.dbsystem.oc1.iad.anuwcljsak7gbriafwglhghmau64pqtimdyzqhkoryf7shdzs5ehuzo6t6sa",
    "region":"us-ashburn-1"
}
print("get client")

# connection = oracledb.connect(
#     access_token=_generate_access_token(client, token_auth_config),
#     dsn="iam",
#     externalauth=True
# )
# print(connection)

#
# Function Handler: executed every time the function is invoked
#
def handler(ctx, data: io.BytesIO = None):
    print("handle")
    return read_all_users(ctx)

def read_all_users(ctx):
    try:
        sql_statement = """
            SELECT 1+1
            FROM dual
        """
        with oracledb.connect(
            access_token=_generate_access_token(client, token_auth_config),
            dsn="iam",
            externalauth=True
        ) as dbconnection:
            print(dbconnection)
            with dbconnection.cursor() as dbcursor:
                dbcursor.execute(sql_statement)
                dbcursor.rowfactory = lambda *args: dict(zip([d[0] for d in dbcursor.description], args))
                results = dbcursor.fetchall()

                return response.Response(
                    ctx,
                    response_data=json.dumps(results),
                    headers={"Content-Type": "application/json"}
                )

    except Exception as ex:
        print('ERROR: Failed to read all users', ex, flush=True)
        raise