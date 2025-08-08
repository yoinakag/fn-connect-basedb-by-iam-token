# OCI Function - Base Database を IAM トークンで接続

## 前提条件
- Base Databaseインスタンスを作成していること
- Base Databaseインスタンスがあるサブネットのセキュリティ・ルールもしくはNetwork Security Groupにてポート1522が開放されていること
- OCIファンクション用のVCNを作成していること
- OCIファンクションを利用するのポリシーを作成していること

## 1. Base Database側の設定
作成したBase Database(23ai)で設定する
```
#oracleユーザーで接続
#1. TLSのための暗号鍵とサーバー証明書を作成する。
$ mkdir /home/oracle/wallet
$ cd /home/oracle/wallet
$ orapki wallet create -wallet . -pwd WElcome##123456 -auto_login
$ orapki wallet add -wallet . -pwd WElcome##123456 -dn "CN=`hostname`" -keysize 2048 -self_signed -validity 3650
$ orapki wallet export -wallet . -pwd WElcome##123456 -dn "CN=`hostname`" -cert dbcert.crt
$ cat dbcert.crt

#2.PDBにTLS接続するようにtnsnamesに追記する
#2-1.PDBのサービス名を取得します
$ lsnrctl status
...
Service "db0801_pdb1.subnet07111020.vcn04201554.oraclevcn.com" has 1 instance(s).
  Instance "DB0801", status READY, has 1 handler(s) for this service...
The command completed successfully
...
#2-2.ホスト名を取得します
$ hostname
basedb23ai
#2-3.tnsnamesに追記
$ vi $ORACLE_HOME/network/admin/tnsnames.ora
接続文字列 = 
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCPS)(HOST = ホスト名)(PORT = 1522))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = PDBのサービス名)
    )
  )

#<設定例>
pdb01_tcps =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCPS)(HOST = basedb23ai)(PORT = 1522))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = db0801_pdb1.subnet07111020.vcn04201554.oraclevcn.com)
    )
  )
  
#3.sqlnet.oraでネットワーク暗号化に関するパラメータをコメントアウトし、TLSに関する3つのパラメータを追加。NAMES.DIRECTORY_PATHとENCRYPTION_WALLET_LOCATIONは残す。※ TLSは認証と暗号化を両方提供するため、ネットワークのネイティブ暗号とは併用できません。
$ vi $ORACLE_HOME/network/admin/sqlnet.ora  

#ココは残す
NAMES.DIRECTORY_PATH=(TNSNAMES,ONAMES,HOSTNAME)
ENCRYPTION_WALLET_LOCATION=(SOURCE=(METHOD=FILE)(METHOD_DATA=(DIRECTORY=/opt/oracle/dcs/commonstore/wallets/ora23ai_3nw_iad/tde)))

#コメントアウト
#SQLNET.ENCRYPTION_SERVER=REQUIRED
#SQLNET.CRYPTO_CHECKSUM_SERVER=REQUIRED
#SQLNET.ENCRYPTION_TYPES_SERVER=(AES256,AES192,AES128)
#SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER=(SHA256,SHA384,SHA512,SHA1)
#SQLNET.ENCRYPTION_CLIENT=REQUIRED
#SQLNET.CRYPTO_CHECKSUM_CLIENT=REQUIRED
#SQLNET.ENCRYPTION_TYPES_CLIENT=(AES256,AES192,AES128)
#SQLNET.CRYPTO_CHECKSUM_TYPES_CLIENT=(SHA256,SHA384,SHA512,SHA1)
#SQLNET.EXPIRE_TIME=10
#WALLET_LOCATION=(SOURCE=(METHOD=FILE)(METHOD_DATA=(DIRECTORY=/opt/oracle/dcs/commonstore/tcps_wallet)))
#SSL_CLIENT_AUTHENTICATION=FALSE

#以下3行追加
SSL_CLIENT_AUTHENTICATION=FALSE
SSL_VERSION=1.2
WALLET_LOCATION=(SOURCE=(METHOD=File)(METHOD_DATA=(DIRECTORY=/home/oracle/wallet)))

#4.opcユーザーにスイッチしてwalletファイルへのアクセス権をgridユーザーに付与
$ sudo setfacl -m u:oracle:rwx /home/oracle/
$ sudo setfacl -m u:oracle:rwx /home/oracle/wallet
$ sudo setfacl -m u:oracle:r /home/oracle/wallet/cwallet.sso
$ sudo setfacl -m u:oracle:r /home/oracle/wallet/dbcert.crt
$ sudo setfacl -m u:oracle:r /home/oracle/wallet/ewallet.p12

#5.oracleユーザーで接続
#listener.oraファイルの既存の設定をすべてコメントアウトして、新規に追記

$ vi $ORACLE_HOME/network/admin/listener.ora
# listener.oraファイルの既存の既存の設定をコメントアウト
#LISTENER=(DESCRIPTION_LIST=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=db23ai4iam.privatesubnetin.vcn0408035740.oraclevcn.com)(PORT=1521))(ADDRESS=(PROTOCOL=IPC)(KEY=EXTPROC1521))(ADDRESS=(PROTOCOL=TCPS)(HOST=db23ai4iam.privatesubnetin.vcn0408035740.oraclevcn.com)(PORT=2484))))
#WALLET_LOCATION=(SOURCE=(METHOD=FILE)(METHOD_DATA=(DIRECTORY=/opt/oracle/dcs/commonstore/tcps_wallet)))
#SSL_CLIENT_AUTHENTICATION=FALSE

#以下を追加
SSL_CLIENT_AUTHENTICATION=FALSE
SSL_VERSION=1.2
WALLET_LOCATION=(SOURCE=(METHOD=File)(METHOD_DATA=(DIRECTORY=/home/oracle/wallet)))

LISTENER =
  (DESCRIPTION_LIST =
    (DESCRIPTION =
      (ADDRESS = (PROTOCOL = TCPS)(HOST = ホスト名)(PORT = 1522))
      (ADDRESS = (PROTOCOL = IPC)(KEY = LISTENER))
      (ADDRESS = (PROTOCOL = TcP)(HOST = ホスト名)(PORT = 1521))
    )
  )

#<設定例>
#SSL_CLIENT_AUTHENTICATION=FALSE
#SSL_VERSION=1.2
#WALLET_LOCATION=(SOURCE=(METHOD=File)(METHOD_DATA=(DIRECTORY=/home/oracle/wallet)))
#
#LISTENER =
#  (DESCRIPTION_LIST =
#    (DESCRIPTION =
#      (ADDRESS = (PROTOCOL = TCPS)(HOST = basedb23ai)(PORT = 1522))
#      (ADDRESS = (PROTOCOL = IPC)(KEY = LISTENER))
#      (ADDRESS = (PROTOCOL = TcP)(HOST = basedb23ai)(PORT = 1521))
#    )
#  )
  
#6.リスナー再起動、walletファイルのアクセスエラーが出ていなければOK
$ lsnrctl stop
$ lsnrctl start

#7.リスナーがTCPS 1522でリスニングできていることを確認
[oracle@basedb23ai ~]$ lsnrctl status

LSNRCTL for Linux: Version 23.0.0.0.0 - for Oracle Cloud and Engineered Systems on 01-AUG-2025 08:34:24

Copyright (c) 1991, 2025, Oracle.  All rights reserved.

Connecting to (DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=basedb23ai)(PORT=1522)))
STATUS of the LISTENER
------------------------
Alias                     LISTENER
Version                   TNSLSNR for Linux: Version 23.0.0.0.0 - for Oracle Cloud and Engineered Systems
Start Date                01-AUG-2025 08:33:44
Uptime                    0 days 0 hr. 0 min. 40 sec
Trace Level               off
Security                  ON: Local OS Authentication
SNMP                      OFF
Listener Parameter File   /u01/app/oracle/product/23.0.0/dbhome_1/network/admin/listener.ora
Listener Log File         /u01/app/oracle/diag/tnslsnr/basedb23ai/listener/alert/log.xml
Listening Endpoints Summary...
  (DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=basedb23ai.subnet07111020.vcn04201554.oraclevcn.com)(PORT=1522)))
  (DESCRIPTION=(ADDRESS=(PROTOCOL=ipc)(KEY=LISTENER)))
  (DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=basedb23ai.subnet07111020.vcn04201554.oraclevcn.com)(PORT=1521)))
The listener supports no services
The command completed successfully


#8.opensslのコマンドで結果がサーバー証明書の結果が返ってくればOK。※CNは、トークン認証時のtnsnames.oraで指定するのホスト名と完全一致する必要あるのでメモしておく。
$ openssl s_client -connect ホスト名:1522
#<実行例>
#$ openssl s_client -connect basedb23ai:1522

CONNECTED(00000003)
Can't use SSL_get_servername
depth=0 CN = basedb23ai
verify error:num=18:self signed certificate
verify return:1
depth=0 CN = basedb23ai
verify return:1
---
Certificate chain
 0 s:CN = basedb23ai
   i:CN = basedb23ai
---
Server certificate
-----BEGIN CERTIFICATE-----
MIICrTCCAZUCEAhpvhl0DE5M+LEq5VQoV+cwDQYJKoZIhvcNAQELBQAwFTETMBEG
A1UEAxMKYmFzZWRiMjNhaTAeFw0yNTA4MDEwODI0NDVaFw0zNTA3MzAwODI0NDVa
MBUxEzARBgNVBAMTCmJhc2VkYjIzYWkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
ggEKAoIBAQCJu1GXaqdFcYyxIp5Yh+JtcsnGvv/9SNK/4RWYoukSlDYJsEiQEhxG
v5u+qtk9naT1YCfl+5PmZC/xy4DZhZs93qCbRIS1Im7umMvr8GXTTcYWSLWZxHu5
EgssZDnUOq7wqxWM51e7kr84+mwxUtjKm1pKrTqWoR690lo/J+8Mvb15QgIZCtNI
EGkKDNpbpU8F/FAGByUH7EP+dIQeMSTepzUVU5N4oQBnSOxwSK6TIT4nH7W+uRqJ
WuCQNev1603MXS9cHKlTPJ6zTrVudly9mwhaeCmDf2VpKeV5SvxPY7nLPCZuggTB
5vFel+7mabLy/WJQCPsuYeh3wDfiaG6ZAgMBAAEwDQYJKoZIhvcNAQELBQADggEB
ADVwosH66Pj8rPCBPkS7Wrg0I0vnOA6GaDW73b4enh7DwLK4bY5eWltPLdVxL71P
BIw1lTczXMa5pwUrb1+tPYaUaxs9JbPQPw0thRt6WP7T/ioxWqjkBMJQrlMC2vwd
3vEYY2+/2r8MYRj3v6K5g0NJVqYtLPNTGuD3+6WPFA5OkQ/NKW4F76+ykgAlmHSD
rQPDqHz8qmBT5qz4XDnQspykS8kgkPo0KKvU03cubUBgeQtWfGIUzgJNtEXBoJdM
ZIV3qV5E6N8ydrhyTkxgeGUZXOrnQDgXoIVJZu94QHfP0QjMlyx9AGKk26M08KM+
yNicdXy0KrAU0AU5BqZ9Sj8=
-----END CERTIFICATE-----

#9.Client側のWalletを作成する。
$ mkdir /home/oracle/client_wallet
$ cd /home/oracle/client_wallet
$ orapki wallet create -wallet . -pwd WElcome##123456 -auto_login
$ orapki wallet add -wallet ./ -pwd WElcome##123456 -trusted_cert -cert /home/oracle/wallet/dbcert.crt
$ ls -ll
total 8
-rw------- 1 oracle oinstall 1051 Aug  2 02:57 cwallet.sso
-rw------- 1 oracle oinstall    0 Aug  2 02:56 cwallet.sso.lck
-rw------- 1 oracle oinstall 1006 Aug  2 02:57 ewallet.p12
-rw------- 1 oracle oinstall    0 Aug  2 02:56 ewallet.p12.lck

# 以下のコマンドを実装して、Client側のWalletのBase64接続文字列を生成します。
[oracle@basedb23ai client_wallet]$ base64 cwallet.sso; echo "---SEPARATOR---"; base64 ewallet.p12;
ofhONgAAAAYAAAAhBo9hbHDDm7XiQj+zs96yB/pEge8rtkE7RA0BZKIaND0HMIID6gIBAzCCA7AG
CSqGSIb3DQEHAaCCA6EEggOdMIIDmTCCA5UGCSqGSIb3DQEHBqCCA4YwggOCAgEAMIIDewYJKoZI
hvcNAQcBMFoGCSqGSIb3DQEFDTBNMCwGCSqGSIb3DQEFDDAfBAhe0gn1zGyEFwICJxACASAwDAYI
KoZIhvcNAgkFADAdBglghkgBZQMEASoEEMg1vg3R6cmMR7HTGhaPDRGAggMQ2nZJJ8RFvZ6JeuQ2
zZwuotz6Zv0tXx8Dr+O1Tv/0EAgc8qqS0KppUiU4IAEvP4Y0uN6IxLdwkOYdfXd0/RkuLXi9tgZ1
T8RCj32gOhgNGfm0e4wgonZInFbIJTcmuX/fUWxcmCDvcWq5Zt3tmwyOMIvChzXK/FHPyTxAfWkO
/m+bN26g2y6k2TCyqtVAciZD6KlNTkTk0+4bNyAt4ytQVvaIQGCMNsI9ped0kJl7scqerCtdeZwf
1OtMgkXFiaL2PCkm8NBZqHb7oYzkl1oHOXwfBKyBup30fdeaQjr3GlfqVAhvwJUX5T6R54upPVZy
K+LtsSK7oDLLKPlyx2M/a/Ymw8B0C6uMolDzmPRwvLEaoPxfMODucppZobTbMZpGs6U5JeNVIIgp
GJ+x9kcvVGJvIdBZT73u6O5l/qG8l1KgDfznzbISqvtMngF8Vtol1YQhy56qbssYH9QgKQ3qK45E
qFJeQB/+PX4NV288wOM+T4ZIN8RkW+kx8DU8udo5hJXiFgB0a00S1kPKE2W575/JWVUA7yjYH6Mo
+fD3dreBOGWtxOjlIVs8VPXyNsDOfN9yZOk/xQeS52BmkOh1qw1fVANfGDe5n8lrhu4DchAARDp4
XrNz8sfHi0PCKZNqIayMiCCZ3RtJYm+zPhrrpxpP/JQB2SPj3sSx2U0FbdS1Vwx83MibN8jK/g8b
kKMrAkFcWMBfh7B62FjzOSQLHErx6ePnmN3mBk7kePecjWl26+vk8vcCbXeiw7OzIX39CTVOaDSU
/xtL39pVXy/M0XBZ8WqrNPbDbVEop42wOHoDoqyoqiZRnenCFvMIQfW0grxVqchwJysir3V9SjAr
AkUnucAypRMsQVmwhKL43MtmtrVEuLHzeK3rgjOoxLMP1TpCwhL1FwX3IVGwgx84PtLGxYXW8OT/
V1yaQcYU6aFSJEpZFSwxE6WkNAbwQjE0RZ9iGqq5vZx+ZVRp/qcA8VizxnI5WWn5UYSLe5YEjmxw
3UX5OqXqQagq8BaESlDcuO6CnRf7FXdm1XeYATkkajAxMCEwCQYFKw4DAhoFAAQU4W8yhI3S6jY8
TRws2QbsBR40+b4ECIKIQr5kaxCGAgInEA==
---SEPARATOR---
MIID6gIBAzCCA7AGCSqGSIb3DQEHAaCCA6EEggOdMIIDmTCCA5UGCSqGSIb3DQEHBqCCA4YwggOC
AgEAMIIDewYJKoZIhvcNAQcBMFoGCSqGSIb3DQEFDTBNMCwGCSqGSIb3DQEFDDAfBAgRXlQfueOY
1QICJxACASAwDAYIKoZIhvcNAgkFADAdBglghkgBZQMEASoEEB0BGNkhWa6XVp2gR/4ES5OAggMQ
ZYtp2SJAhuUVefkv0FRhhhWyKirvU96+v0UYumNIPeywEP/8+08L+9sD2y50a7V1MoBs+KWdjnUa
xcHDbEcE+VDzh8zQoF3RSFP3vOC+Bfw54sCR4bRm+jT3diDoLXqoGmZ12Kowu7CbnTV51KyaRlfy
KaTarA9CcYZzJ8825UFlQVIsfoVtMeyIlfP9B7l+OgQ9bdjJgeQyQUCeX+V+1vP8GfuREOH9PzS6
L16+Yyq0IgT89whUsNaZby3fPGBTPGmtq0HrwL6xEuEDJDrmdRewTnJneVD44PxbbGNX5fIc1NmQ
7uXL/mGaeXWFQfBoFSdF8v9zzFHGvh5z/AiDIY9AipD1FYk1EbKZlmtjCLd9Q1WVql4pvLqxhYow
rqX6cUFAKTqK0AIOjl2/lvMWVFBuJAO/A5Tv1GkWy7B39+kjETazcPWD+SBh0eLEjUPKCDUrEFL5
sylFIuHRueLd0Jb89vCL/GTAbK99pilVcHiTJVd5Ld0jam6+lUt7Gzhb2FID9tEI0J2t3tTk2VLE
jVOAzm58qhmrnKUJ9r3zjQUNRz7oxy3rdGuTCj9M8MPInTXAffDB5mtZCahPLjDtp0vUIgiROxCr
6kUNkoV539tuBr3Dzy2PcUhQ9CAC71GWZ+x5oSnFpjk9ms6XbhgEavkjvLV3DPw/bK6Yh3cW3FY7
3HwsdQzG8REfTbB2K7aDq5HA0MI8stCtpzUXTM/48+dtPkyHt94js61jXeqtVEHaH5kIwnlPS++Z
apbh+17a9JS+JAUumP04J2X1iNjSxKAY9XzTIA8kd4zqIR9TBdW3Yw8gfu7WdxpyPayWQtXtNAOV
mA9ZUpXzPPFOTzNIKqJhaZ+jsf6093YWFtbsmUsH4xQ8rPNPQ3qF5EdfTlf4voAAhBaCXYEvCEIW
mCltYcjOZ/7m+zl2yY8+cYYE06vym0mjTC4emYPLK7fNXJsKA5zgr9KnPJHUTWxcqRehdc/NMu9L
+Pv80/CwxZjvdZPZ4WxkoF/AwIW+lDvP9PaoWRxng7VLZWgrJkujinPm/DAxMCEwCQYFKw4DAhoF
AAQUc9F8uuVTTPyNSt7R0IitWpxrLrwECIKIQr5kaxCGAgInEA==
```

## 2. OCI IAM と BaseDB のトークン・ベースの認証設定（Function 用）

### 2-1. IDENTITY_PROVIDER_TYPE の設定
BaseDB 側で IAM 認証を有効化します。  
以下の SQL を実行して `IDENTITY_PROVIDER_TYPE` を `OCI_IAM` に設定します。

```sql
-- Identity Provider を IAM に設定
ALTER SYSTEM SET IDENTITY_PROVIDER_TYPE=OCI_IAM SCOPE=BOTH;

-- 設定確認
SELECT NAME, VALUE 
FROM V$PARAMETER 
WHERE NAME='identity_provider_type';

-- 実行結果例
NAME                      VALUE
------------------------  -------------
identity_provider_type    OCI_IAM
```

---

### 2-2. Dynamic Group とポリシーの作成
OCI Function から IAM トークン経由で BaseDB にアクセスするため、  
Function が実行される **アプリケーション** を Dynamic Group に登録し、そのグループに適切なポリシーを付与します。

1. **Dynamic Group の作成**  
   - OCI コンソール → **「アイデンティティとセキュリティ」→「Dynamic Groups」** → 「作成」
   - 名前: `dg-function-basedb`
   - ルール例（`app-connect-basedb-by-iam-token` が Function アプリケーション名）  
     ```
     ALL {resource.type = 'fnfunc', resource.compartment.id = '<アプリケーションのコンパートメントOCID>'}
     ```
     またはアプリケーション単位で指定する場合:  
     ```
     ANY {resource.id = '<FunctionのOCID>'}
     ```

2. **ポリシーの作成**  
   - OCI コンソール → **「ポリシー」** → 「作成」
   - 作成するポリシー例（同じコンパートメントにある BaseDB にアクセスさせる場合）:
     ```
     Allow dynamic-group dg-function-basedb to use database-connections in compartment <compartment_name>
     Allow dynamic-group dg-function-basedb to use database-family in compartment <compartment_name>
     ```

> 💡 **ポイント**  
> - Function は IAM トークンを使って DB に接続するため、`use database-family` 権限が必須です。  
> - Dynamic Group のルールは対象 Function アプリケーションまたは Function に限定するのがセキュリティ的に安全です。

---

### 2-3. Dynamic Group と DB スキーマのマッピング
Dynamic Group 名を IAM_GROUP_NAME のようにスキーマとマッピングします。

```sql
-- マッピング用スキーマ作成
CREATE USER dbusers IDENTIFIED GLOBALLY AS 'IAM_GROUP_NAME=dg-function-basedb';
GRANT connect, resource TO dbusers;
GRANT unlimited tablespace TO dbusers;
```

---

### 2-4. ユーザー表の作成とデータ投入
以下のスクリプトを `dbusers` スキーマで実行します。

```sql
CREATE TABLE dbusers.users ( 
    "ID"  VARCHAR2(32 BYTE) DEFAULT ON NULL sys_guid(), 
    "FIRST_NAME"  VARCHAR2(50 BYTE) NOT NULL ENABLE,  
    "LAST_NAME"  VARCHAR2(50 BYTE) NOT NULL ENABLE,  
    "USERNAME"  VARCHAR2(50 BYTE) NOT NULL ENABLE,  
    "CREATED_ON"  TIMESTAMP(6) DEFAULT ON NULL current_timestamp, 
    CONSTRAINT "USER_PK" PRIMARY KEY ( "ID" )
);
/  

INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('John', 'Doe', 'john.doe');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('Jane', 'Smith', 'jane.smith');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('Michael', 'Johnson', 'michael.j');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('Emily', 'Davis', 'emily.d');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('David', 'Wilson', 'david.wilson');

COMMIT; 
/
```

> 💡 **補足**  
> - `dbusers` スキーマは Dynamic Group とマッピングしているため、Function 実行時に IAM トークンで接続できます。  
> - Dynamic Group 名は OCI 設定と DB マッピングで完全一致させる必要があります。

## 3. ファンクションのデプロイメント

### 3-1. アプリケーションの作成
このステップでは、OCI Function をデプロイするための **アプリケーション** を作成します。  
アプリケーションは、関数の実行環境（VCN・サブネット・シェイプなど）を定義するコンテナのような役割を持っています。

1. OCI コンソールにログインし、左上のメニューから **「開発者サービス」→「アプリケーション」** を選択します。  
2. **「アプリケーションの作成」** をクリックします。  
3. 以下のパラメータを入力します。  

   - **名前**: `app-connect-basedb-by-iam-token`  
     （後続の `fn deploy` コマンドで使用するので覚えておきます）
   - **VCN**: 事前に作成した VCN を選択  
   - **サブネットコンパートメント**: VCN サブネットが所属しているコンパートメントを選択  
   - **サブネット**: 事前に作成した VCN 内のサブネットを選択（Public または Private サブネット、DB 接続要件に応じて選択）  
   - **シェイプ**: `GENERIC_X86` を選択（汎用的な x86 ベースの実行環境）  

> 💡 **注意:**  
> - BaseDB に接続する場合、サブネットから DB へのネットワーク到達性が必要です。  
> - Private サブネットを選ぶ場合は NAT Gateway や Service Gateway の設定を事前に行っておきます。  

---

### 3-2. アプリケーション構成の設定
アプリケーションを作成したら、関数が実行時に利用する **環境変数（Configuration）** を設定します。  
これにより、ソースコードを修正せずに接続情報を切り替えたり、機密情報を安全に保持できます。

1. 作成したアプリケーションを選択し、**「アプリケーション構成」** タブを開きます。  
2. **「構成の追加」** をクリックし、以下のキーと値を設定します。  

   - `SERVICE_NAME`: PDB のサービス名  
     例: `db0801_pdb1.subnet07111020.vcn04201554.oraclevcn.com`
   - `WALLET_BASE64`: Client 側 Wallet の Base64 エンコード文字列  
   - `BASEDB_COMPARTMENT_OCID`: BaseDB が存在するコンパートメントの OCID  
   - `HOST`: BaseDB のパブリック IP アドレス  
   - `BASEDB_OCID`: BaseDB の OCID  
   - `CN`: BaseDB のホスト名  
     例: `basedb23ai`
   - `BASEDB_REGION`: BaseDB が存在するリージョンコード  
     例: `us-ashburn-1`

---

### 3-3. ファンクションのデプロイメント

以下の手順では、OCI Cloud Shell を利用して Function をデプロイします。  
OCI CLI や Docker Registry の設定も含まれているため、初回は全手順を実行してください。

```bash
# ステップ1: リージョンのコンテキストを設定
fn list context
fn use context us-chicago-1

# ステップ2: ファンクションのコンパートメントを設定
fn update context oracle.compartment-id ocid1.compartment.oc1..aaaa...（自分のコンパートメントOCID）

# ステップ3: リポジトリの設定（自分のOCIRリポジトリ）
fn update context registry ord.ocir.io/sehubiapacprod/[repo-name-prefix]

# ステップ4: 認証トークンの生成（OCIコンソールで作成）
# 作成方法: ユーザ設定 → 認証トークン → トークンの生成
# 生成されたトークンは Docker ログインに使用
# 例: docker login -u 'tenancy_namespace/username@company.com' ord.ocir.io
docker login -u 'sehubiapacprod/linfeng.yan@oracle.com' ord.ocir.io

# ステップ5: コンパートメント内のアプリ一覧を確認
fn list apps

# ステップ6: ソースコード取得（GitHubからクローン）
git clone https://github.com/yan-linfeng/fn-connect-basedb-by-iam-token
cd fn-connect-basedb-by-iam-token

# ステップ7: 関数をアプリケーションにデプロイ
fn deploy --app app-connect-basedb-by-iam-token

# ステップ9: 関数を呼び出して動作確認
fn invoke app-connect-basedb-by-iam-token access-basedb-func


