import io
import os
import oci
import json
import base64
import oracledb
from fdk import response
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Get connection parameters from enviroment
cn = os.getenv("CN")
host = os.getenv("HOST")
basedb_ocid = os.getenv("BASEDB_OCID")
service_name = os.getenv("SERVICE_NAME")
wallet_base64 = os.getenv("WALLET_BASE64")
basedb_region = os.getenv("BASEDB_REGION")
basedb_compartment_ocid = os.getenv("BASEDB_COMPARTMENT_OCID")
scope = "urn:oracle:db::id::{}::{}".format(basedb_compartment_ocid,basedb_ocid)

#
# Function Handler: executed every time the function is invoked
#
def handler(ctx, data: io.BytesIO = None):
    return read_all_users(ctx)

def read_all_users(ctx):
    try:
        sql_statement = """
            SELECT FIRST_NAME, LAST_NAME, USERNAME from users
        """
        
        client = oci.identity_data_plane.DataplaneClient(config={}, signer=oci.auth.signers.get_resource_principals_signer())
        token_auth_config = {
            "scope": scope,
            "region": basedb_region
        }

        dsn = oracledb.makedsn(
            "adb.ap-tokyo-1.oraclecloud.com", # ホスト名 (DBの接続文字列から)
            1522,                             # ポート番号
            service_name="sya6vphk3pzlkhq_dbtokentestdb_tp.adb.oraclecloud.com"  # サービス名 (Low, High, Medium など)
        )
        
        with oracledb.connect(
#            access_token=_generate_access_token(client, token_auth_config),
#            dsn="iam",
#            externalauth=True
            user="ADMIN",
            password="Welcome123!!",
            dsn=dsn
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


def restore_files_from_string(combined_str, 
                              separator="---SEPARATOR---", 
                              output1="/tmp/dbwallet/cwallet.sso", 
                              output2="/tmp/dbwallet/ewallet.p12"):
    """
    区切り文字を含む文字列から、2つのBase64エンコードされたファイルを復元する
    
    パラメータ:
        combined_str: 2つのBase64エンコード文字列と区切り文字を含む入力文字列
        separator: 2つのBase64エンコードを区切る文字列
        output1: 最初の出力ファイルのパス
        output2: 2番目の出力ファイルのパス
    """
    try:
        # 1. 区切り文字で文字列を分割
        parts = combined_str.split(separator)
        if len(parts) != 2:
            raise ValueError(f"文字列に有効な区切り文字 '{separator}' が見つからないか、区切り文字の数が正しくありません")

        print("===== here =====")
        cwallet_sso = get_secret(secret_ocid=os.environ['C_WALLET_SSO_SECRET_OCID'])
#        print(cwallet_sso)
        ewallet_p12 = get_secret(secret_ocid=os.environ['E_WALLET_P12_SECRET_OCID'])
#        print(ewallet_p12)
        
        # Base64文字列の抽出とクリーニング（前後の空白と改行を除去）
        base64_str1 = cwallet_sso.strip()
        base64_str2 = ewallet_p12.strip()
        
        # 2. デコードしてファイルに書き込み
        with open(output1, "wb") as f:
            decoded_data = base64.b64decode(base64_str1)
            f.write(decoded_data)
        
        with open(output2, "wb") as f:
            decoded_data = base64.b64decode(base64_str2)
            f.write(decoded_data)
        
        print(f"ファイルを正常に復元しました：\n{output1}\n{output2}")
    
    except base64.binascii.Error:
        print("エラー：Base64デコードに失敗しました。エンコード内容が完整か正しいかを確認してください")
    except Exception as e:
        print(f"処理に失敗しました：{str(e)}")

def get_secret(secret_ocid):
#    signer = oci.auth.signers.get_resource_principals_signer()
#    client = oci.secrets.SecretsClient(config={}, signer=signer)
#    bundle = client.get_secret_bundle(secret_ocid)

#    print("===== get_secret1 =====")
#    print(secret_ocid)
    client = oci.secrets.SecretsClient(config={}, signer=oci.auth.signers.get_resource_principals_signer())
    secret_base64 = client.get_secret_bundle(secret_ocid).data.secret_bundle_content.content.encode('utf-8')
#    print("===== get_secret2 =====")
    return base64.b64decode(secret_base64).decode("utf-8")

# Restore wallet file from wallet_base64 combined string
os.makedirs('/tmp/dbwallet', exist_ok=True)
restore_files_from_string(combined_str=wallet_base64)

# Setup tnsnames.ora and sqlnet.ora file
with open('/function/instant23ai/tnsnames.ora') as orig_tnsnamesora:
#    newText=orig_tnsnamesora.read().replace('HOST_PLACEHOLDER', host).replace('SERVICE_NAME_PLACEHOLDER',service_name).replace('CN=CN_PLACEHOLDER', cn)
    newText = orig_tnsnamesora.read() \
        .replace('HOST_PLACEHOLDER', host) \
        .replace('SERVICE_NAME_PLACEHOLDER', service_name) \
        .replace('(SSL_SERVER_CERT_DN="CN=CN_PLACEHOLDER")', '')
    print("===== newText =====")
    print(newText)
with open('/tmp/dbwallet/tnsnames.ora', "w") as new_tnsnamesora:
    new_tnsnamesora.write(newText)
with open('/function/instant23ai/sqlnet.ora') as sqlnetora:
    sqlnetora_text=sqlnetora.read()
with open('/tmp/dbwallet/sqlnet.ora', "w") as new_sqlnetora:
    new_sqlnetora.write(sqlnetora_text)

oracledb.init_oracle_client(lib_dir="/usr/lib/oracle/23/client64/lib", config_dir="/tmp/dbwallet")
