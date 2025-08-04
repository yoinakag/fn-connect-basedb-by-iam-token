# OCI IAMとBaseDBのトークン・ベースの認証設定
1. IDENTITY_PROVIDER_TYPEの設定
```
-- Alter System文でIdentity ProviderをIAMに設定
SQL> ALTER SYSTEM SET IDENTITY_PROVIDER_TYPE=OCI_IAM SCOPE=BOTH;
SQL> SELECT NAME, VALUE FROM V$PARAMETER WHERE NAME='identity_provider_type';
NAME                      VALUE
------------------------  -------------
identity_provider_type    OCI_IAM

```
2. IAMグループとポリシーの作成
IAMトークンを使用してデータベースに接続するためには、そもそもIAMユーザーがBaseDBサービスを使用するための権限をIAMポリシーとして許可されていなければならない。

ここでは、そのサービスを使用できるポリシーを持つdbtoken_grpというグループを作成し、emp1とmgr1というユーザーをそのグループに所属させる。

3. IAMユーザーとのDBスキーマのマッピング
-- 排他的マッピングユーザーの作成
CREATE USER dbusers IDENTIFIED GLOBALLY AS 'IAM_GROUP_NAME=dg_instance';
grant connect,resource to dbusers;

4. ユーザー表の作成
CREATE TABLE dbusers.users ( 
    "ID"  VARCHAR2(32 BYTE) DEFAULT ON NULL sys_guid(), 
    "FIRST_NAME"  VARCHAR2(50 BYTE) COLLATE "USING_NLS_COMP" NOT NULL ENABLE, 
    "LAST_NAME"  VARCHAR2(50 BYTE) COLLATE "USING_NLS_COMP" NOT NULL ENABLE, 
    "USERNAME"  VARCHAR2(50 BYTE) COLLATE "USING_NLS_COMP" NOT NULL ENABLE, 
    "CREATED_ON"  TIMESTAMP(6) DEFAULT ON NULL current_timestamp, 
    CONSTRAINT "USER_PK" PRIMARY KEY ( "ID" )
);
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('John', 'Doe', 'john.doe');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('Jane', 'Smith', 'jane.smith');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('Michael', 'Johnson', 'michael.j');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('Emily', 'Davis', 'emily.d');
INSERT INTO dbusers.users (FIRST_NAME, LAST_NAME, USERNAME) VALUES ('David', 'Wilson', 'david.wilson');
