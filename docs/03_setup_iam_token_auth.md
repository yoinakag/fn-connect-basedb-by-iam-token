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
CREATE USER func IDENTIFIED GLOBALLY AS 'IAM_PRINCIPAL_NAME=emp1'; -- DBスキーマ:emp1 = IAMユーザ:emp1
grant connect to func; -- connect権限を付与

CREATE USER dbusers IDENTIFIED GLOBALLY AS 'IAM_GROUP_NAME=dg_instance';
grant connect,resource to dbusers;