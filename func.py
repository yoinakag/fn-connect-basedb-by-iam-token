import io
import os
import oci
import json
import oracledb
from fdk import response
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Get connection parameters from enviroment
basedb_region = os.getenv("BASEDB_REGION")
basedb_compartment_ocid = os.getenv("BASEDB_COMPARTMENT_OCID")
basedb_ocid = os.getenv("BASEDB_OCID")

scope = "urn:oracle:db::id::{}::{}".format(basedb_region,basedb_compartment_ocid,basedb_ocid)
oracledb.init_oracle_client(lib_dir="/usr/lib/oracle/23/client64/lib", config_dir="/tmp/instant23ai")

#
# Function Handler: executed every time the function is invoked
#
def handler(ctx, data: io.BytesIO = None):
    return read_all_users(ctx)

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

def print_directory_files(directory_path):
    """打印指定目录下的文件列表及其内容"""
    try:
        if not os.path.exists(directory_path):
            print(f"错误: 目录 '{directory_path}' 不存在")
            return
        
        if not os.path.isdir(directory_path):
            print(f"错误: '{directory_path}' 不是一个目录")
            return
        
        files = os.listdir(directory_path)
        
        if not files:
            print(f"目录 '{directory_path}' 为空")
            return
        
        print(f"目录 '{directory_path}' 下的文件列表:")
        for filename in files:
            file_path = os.path.join(directory_path, filename)
            
            if os.path.isfile(file_path):
                print(f"\n=== 文件: {filename} ===")
                
                try:
                    with open(file_path, 'r') as file:
                        content = file.read()
                        if content.strip():  
                            print(content)
                        else:
                            print("文件内容为空")
                except Exception as e:
                    print(f"无法读取文件内容: {str(e)}")
            else:
                print(f"- {filename} (目录，跳过)")
                
    except Exception as e:
        print(f"发生错误: {str(e)}")

def read_all_users(ctx):
    try:
        sql_statement = """
            SELECT 1+1
            FROM dual
        """
        
        client = oci.identity_data_plane.DataplaneClient(config={}, signer=oci.auth.signers.get_resource_principals_signer())
        token_auth_config = {
            "scope":"urn:oracle:db::id::ocid1.compartment.oc1..aaaaaaaardb3dtrfgv5dde2rqisd44p3f6ihjtbd3gnbtwq64nq6lzngxotq::ocid1.dbsystem.oc1.iad.anuwcljsak7gbriafwglhghmau64pqtimdyzqhkoryf7shdzs5ehuzo6t6sa",
            "region":"us-ashburn-1"
        }
        
        print_directory_files("/tmp/instant23ai")
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