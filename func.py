import io
import os
import oci
import json
import base64
import oracledb
from fdk import response
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

#
# Function Handler: executed every time the function is invoked
#
def handler(ctx, data: io.BytesIO = None):
    return read_all_users(ctx)

def read_all_users(ctx):
    try:
        sql_statement = """
            SELECT ID, FIRST_NAME, LAST_NAME, USERNAME, CREATED_ON
            FROM users
        """
        
        client = oci.identity_data_plane.DataplaneClient(config={}, signer=oci.auth.signers.get_resource_principals_signer())
        token_auth_config = {
            "scope": scope,
            "region": basedb_region
        }
        
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

def create_and_insert_users():
    """
    ユーザーテーブルの作成とデータ挿入を実行する関数
    
    引数:
        db_config (dict): データベース接続情報を含む辞書
            - user: ユーザー名
            - password: パスワード
            - dsn: 接続文字列 (例: "host:port/service_name")
    """
    # 処理対象のスキーマとテーブル名を定義
    schema = "dbusers"
    table_name = "users"
    
    try:
        client = oci.identity_data_plane.DataplaneClient(config={}, signer=oci.auth.signers.get_resource_principals_signer())
        token_auth_config = {
            "scope": scope,
            "region": basedb_region
        }
        
        with oracledb.connect(
            access_token=_generate_access_token(client, token_auth_config),
            dsn="iam",
            externalauth=True
        ) as  conn:
            print("データベース接続に成功しました")
            
            # テーブルの存在を確認
            def check_table_exists():
                """テーブルが存在するかどうかを確認する内部関数"""
                # Oracleではテーブル名とスキーマ名は通常大文字で格納されるため変換
                upper_schema = schema.upper()
                upper_table = table_name.upper()
                
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM all_tables 
                        WHERE owner = :owner AND table_name = :table_name
                    """, {"owner": upper_schema, "table_name": upper_table})
                    return cursor.fetchone()[0] > 0
            
            # テーブルが存在しない場合は作成
            if not check_table_exists():
                print(f"テーブル {schema}.{table_name} を作成します...")
                create_table_sql = """
                CREATE TABLE dbusers.users ( 
                    "ID"  VARCHAR2(32 BYTE) DEFAULT ON NULL sys_guid(), 
                    "FIRST_NAME"  VARCHAR2(50 BYTE) COLLATE "USING_NLS_COMP" NOT NULL ENABLE, 
                    "LAST_NAME"  VARCHAR2(50 BYTE) COLLATE "USING_NLS_COMP" NOT NULL ENABLE, 
                    "USERNAME"  VARCHAR2(50 BYTE) COLLATE "USING_NLS_COMP" NOT NULL ENABLE, 
                    "CREATED_ON"  TIMESTAMP(6) DEFAULT ON NULL current_timestamp, 
                    CONSTRAINT "USER_PK" PRIMARY KEY ( "ID" )
                )
                """
                with conn.cursor() as cursor:
                    cursor.execute(create_table_sql)
                print("テーブルの作成が完了しました")
                # 挿入するデータを定義
                user_data = [
                    ('John', 'Doe', 'john.doe'),
                    ('Jane', 'Smith', 'jane.smith'),
                    ('Michael', 'Johnson', 'michael.j'),
                    ('Emily', 'Davis', 'emily.d'),
                    ('David', 'Wilson', 'david.wilson')
                ]
                
                # データ挿入を実行
                print("データの挿入を開始します...")
                insert_sql = """
                INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) 
                VALUES (:1, :2, :3)
                """
                with conn.cursor() as cursor:
                    # 複数行を一括挿入（効率的な処理）
                    cursor.executemany(insert_sql, user_data)
                    # トランザクションをコミット（変更を確定）
                    conn.commit()
                print(f"{len(user_data)} 件のデータを挿入しました")
            else:
                print(f"テーブル {schema}.{table_name} は既に存在します")
    
    except oracledb.Error as e:
        # Oracle関連のエラー処理
        error, = e.args
        print(f"データベースエラーが発生しました: {error.message}")
        # エラー発生時はトランザクションをロールバック
        if 'conn' in locals():
            conn.rollback()
    except Exception as e:
        # その他の一般的なエラー処理
        print(f"予期しないエラーが発生しました: {str(e)}")

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
        
        # Base64文字列の抽出とクリーニング（前後の空白と改行を除去）
        base64_str1 = parts[0].strip()
        base64_str2 = parts[1].strip()
        
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

# Get connection parameters from enviroment
cn = os.getenv("CN")
host = os.getenv("HOST")
basedb_ocid = os.getenv("BASEDB_OCID")
service_name = os.getenv("SERVICE_NAME")
wallet_base64 = os.getenv("WALLET_BASE64")
basedb_region = os.getenv("BASEDB_REGION")
basedb_compartment_ocid = os.getenv("BASEDB_COMPARTMENT_OCID")

# Restore wallet file from wallet_base64 combined string
os.makedirs('/tmp/dbwallet', exist_ok=True)
restore_files_from_string(combined_str=wallet_base64)

# Setup tnsnames.ora and sqlnet.ora file
with open('/function/instant23ai/tnsnames.ora') as orig_tnsnamesora:
    newText=orig_tnsnamesora.read().replace('HOST_PLACEHOLDER', host).replace('SERVICE_NAME_PLACEHOLDER',service_name).replace('CN_PLACEHOLDER', cn)
with open('/tmp/dbwallet/tnsnames.ora', "w") as new_tnsnamesora:
    new_tnsnamesora.write(newText)
with open('/function/instant23ai/sqlnet.ora') as sqlnetora:
    sqlnetora_text=sqlnetora.read()
with open('/tmp/dbwallet/sqlnet.ora', "w") as new_sqlnetora:
    new_sqlnetora.write(sqlnetora_text)

# Generate scope for iam token auth
scope = "urn:oracle:db::id::{}::{}".format(basedb_region,basedb_compartment_ocid,basedb_ocid)
oracledb.init_oracle_client(lib_dir="/usr/lib/oracle/23/client64/lib", config_dir="/tmp/dbwallet")

# Create users table and insert essential data
create_and_insert_users()