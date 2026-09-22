# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC ## データベースオブジェクトの準備

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE CATALOG IF NOT EXISTS ontobricks;
# MAGIC CREATE SCHEMA IF NOT EXISTS ontobricks.family_tree_01;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 1. まずテーブル本体を作る
# MAGIC CREATE TABLE ontobricks.family_tree_01.person (
# MAGIC     person_id STRING NOT NULL,
# MAGIC     name STRING,
# MAGIC     gender STRING,
# MAGIC     father_id STRING,
# MAGIC     mother_id STRING
# MAGIC   );
# MAGIC
# MAGIC -- 2. 主キーを追加
# MAGIC ALTER TABLE
# MAGIC   ontobricks.family_tree_01.person
# MAGIC ADD
# MAGIC   CONSTRAINT person_pk PRIMARY KEY (person_id);
# MAGIC
# MAGIC -- 3. father_id の自己参照 FK
# MAGIC ALTER TABLE
# MAGIC   ontobricks.family_tree_01.person
# MAGIC ADD
# MAGIC   CONSTRAINT person_father_fk
# MAGIC     FOREIGN KEY (father_id) REFERENCES ontobricks.family_tree_01.person (person_id);
# MAGIC
# MAGIC -- 4. mother_id の自己参照 FK
# MAGIC ALTER TABLE
# MAGIC   ontobricks.family_tree_01.person
# MAGIC ADD
# MAGIC   CONSTRAINT person_mother_fk
# MAGIC     FOREIGN KEY (mother_id) REFERENCES ontobricks.family_tree_01.person (person_id);

# COMMAND ----------

# MAGIC %sql
# MAGIC INSERT INTO ontobricks.family_tree_01.person (
# MAGIC     person_id,
# MAGIC     name,
# MAGIC     gender,
# MAGIC     father_id,
# MAGIC     mother_id
# MAGIC )
# MAGIC VALUES
# MAGIC     ('p1', 'John Smith',    'M', NULL, NULL),
# MAGIC     ('p2', 'Mary Johnson',  'F', NULL, NULL),
# MAGIC     ('p3', 'Robert Smith',  'M', 'p1', 'p2'),
# MAGIC     ('p4', 'Emily Smith',   'F', 'p1', 'p2'),
# MAGIC     ('p5', 'Sarah Davis',    'F', NULL, NULL),
# MAGIC     ('p6', 'Michael Smith', 'M', 'p3', 'p5'),
# MAGIC     ('p7', 'Lisa Smith',    'F', 'p3', 'p5');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- OntoBricks App の Service Principal Application ID
# MAGIC DECLARE OR REPLACE VARIABLE ontobricks_app_principal STRING
# MAGIC DEFAULT 'cb683fcf-1151-4d99-92f8-5f6982d6093c';
# MAGIC
# MAGIC EXECUTE IMMEDIATE
# MAGIC   'GRANT USE CATALOG ON CATALOG ontobricks TO `' 
# MAGIC   || ontobricks_app_principal 
# MAGIC   || '`';
# MAGIC
# MAGIC EXECUTE IMMEDIATE
# MAGIC   'GRANT USE SCHEMA ON SCHEMA ontobricks.family_tree_01 TO `' 
# MAGIC   || ontobricks_app_principal 
# MAGIC   || '`';
# MAGIC
# MAGIC EXECUTE IMMEDIATE
# MAGIC   'GRANT SELECT ON SCHEMA ontobricks.family_tree_01 TO `' 
# MAGIC   || ontobricks_app_principal 
# MAGIC   || '`';

# COMMAND ----------

# MAGIC %md
# MAGIC ## mapping 時に設定するクエリ

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   person_id,
# MAGIC   name AS person_label,
# MAGIC   name,
# MAGIC   gender
# MAGIC FROM
# MAGIC   ontobricks.family_tree_01.person

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   person_id, -- source_id
# MAGIC   father_id  -- target_id
# MAGIC FROM ontobricks.family_tree_01.person
# MAGIC WHERE father_id IS NOT NULL

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   person_id, -- source_id
# MAGIC   mother_id  -- target_id
# MAGIC FROM ontobricks.family_tree_01.person
# MAGIC WHERE mother_id IS NOT NULL

# COMMAND ----------

# MAGIC %md
# MAGIC ## SPARQL

# COMMAND ----------

APP_NAME = "ontobricks-08x"
TARGET_DOMAIN = "FamilyTree"
DOMAIN_VERSION = "1"

# COMMAND ----------

import requests
import pandas as pd
from databricks.sdk import WorkspaceClient

# 認証
w = WorkspaceClient()
app = w.apps.get(APP_NAME)
app_url = app.url.rstrip("/")

notebook_token = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
)

r = requests.post(
    f"{w.config.host.rstrip('/')}/oidc/v1/token",
    data={
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": notebook_token,
        "subject_token_type": "urn:databricks:params:oauth:token-type:personal-access-token",
        "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "scope": "all-apis",
        "audience": app.oauth2_app_client_id,
    },
    timeout=30,
)
r.raise_for_status()

session = requests.Session()
session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


# 共通のAPI呼び出し
def api(method, path, **kwargs):
    headers = {}
    if method == "POST":
        csrf = session.cookies.get("csrf_token")
        if not csrf:
            raise RuntimeError("CSRFトークンを取得できませんでした")
        headers["X-CSRF-Token"] = csrf
    response = session.request(
        method,
        f"{app_url}{path}",
        headers=headers,
        timeout=120,
        **kwargs,
    )
    if not response.ok:
        raise RuntimeError(f"{path}: HTTP {response.status_code}\n{response.text}")
    data = response.json()
    if data.get("success") is False:
        raise RuntimeError(f"{path}: {data}")
    return data


# ドメイン名の解決とセッション初期化
domains = api("GET", "/domain/list-projects").get("domains", [])
domain_name = next(
    (name for name in domains if name.casefold() == TARGET_DOMAIN.casefold()),
    None,
)

if domain_name is None:
    raise ValueError(f"{TARGET_DOMAIN}が見つかりません。候補: {domains}")

api(
    "POST",
    "/domain/load-from-uc",
    json={
        "domain": domain_name,
        "version": DOMAIN_VERSION,
    },
)

print(f"対象: {domain_name} / V{DOMAIN_VERSION}")

# COMMAND ----------

def execute_sparql(query):
    result = api(
        "POST",
        "/dtwin/execute",
        json={
            "query": query,
            "limit": 100,
        },
    )

    rows = result.get("results", [])
    print(f"取得件数: {len(rows)}")

    if rows:
        display(pd.DataFrame(rows))
    else:
        print("結果は0行です")

# COMMAND ----------

# 1. すべての人物：期待値7人
execute_sparql("""
PREFIX family: <https://databricks-ontology.com/FamilyTree/>

SELECT ?person ?name ?gender
WHERE {
  ?person a family:Person .
  ?person family:name ?name .
  ?person family:gender ?gender .
}
ORDER BY ?name
""")

# COMMAND ----------

# 2. Johnの子：期待値Emily、Robert
execute_sparql("""
PREFIX family: <https://databricks-ontology.com/FamilyTree/>

SELECT ?child ?name
WHERE {
  ?father a family:Person .
  ?father family:name "John Smith" .

  ?child a family:Person .
  ?child family:hasFather ?father .
  ?child family:name ?name .
}
ORDER BY ?name
""")

# COMMAND ----------

# 3. John Smith の孫：期待値Lisa、Michael
execute_sparql("""
PREFIX family: <https://databricks-ontology.com/FamilyTree/>

SELECT DISTINCT ?grandchild ?name
WHERE {
  ?grandchild a family:Person .
  ?grandchild family:name ?name .
  ?grandchild family:hasFather ?child .

  ?child a family:Person .
  ?child family:hasFather ?john .

  ?john a family:Person .
  ?john family:name "John Smith" .
}
ORDER BY ?name
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Graph Chatの質問

# COMMAND ----------

# MAGIC %md
# MAGIC 1. すべての人を抽出して
# MAGIC 2. 父親が John Smith の人
# MAGIC 3. John Smith の子のうち、その人物が父親になっている子供、つまり John Smith の孫を教えて。hasFather の関係を2段階たどってください。

# COMMAND ----------

# MAGIC %md
# MAGIC # GraphQL

# COMMAND ----------

import json
import requests

from databricks.sdk import WorkspaceClient


# ============================================================
# 1. 設定
# ============================================================

APP_NAME = "ontobricks-08x"
DOMAIN_FOLDER = "familytree"
DOMAIN_VERSION = "1"


# ============================================================
# 2. Workspace / App 情報
# ============================================================

w = WorkspaceClient()

app = w.apps.get(APP_NAME)

app_url = app.url.rstrip("/")
app_client_id = app.oauth2_app_client_id
workspace_host = w.config.host.rstrip("/")

print("Workspace           :", workspace_host)
print("App URL             :", app_url)
print("App Name            :", APP_NAME)
print("App OAuth Client ID :", app_client_id)
print("Domain              :", DOMAIN_FOLDER)
print("Version             :", DOMAIN_VERSION)

if not app_client_id:
    raise RuntimeError(
        "oauth2_app_client_id が取得できませんでした。"
    )


# ============================================================
# 3. Notebook token
# ============================================================

notebook_token = (
    dbutils.notebook.entry_point
    .getDbutils()
    .notebook()
    .getContext()
    .apiToken()
    .get()
)

print("Notebook token acquired")


# ============================================================
# 4. Notebook token → App audience token
#
# 重要:
# subject_token_type は
# urn:databricks:params:oauth:token-type:personal-access-token
# ============================================================

token_response = requests.post(
    f"{workspace_host}/oidc/v1/token",
    data={
        "grant_type":
            "urn:ietf:params:oauth:grant-type:token-exchange",

        "subject_token":
            notebook_token,

        "subject_token_type":
            "urn:databricks:params:oauth:token-type:personal-access-token",

        "requested_token_type":
            "urn:ietf:params:oauth:token-type:access_token",

        "scope":
            "all-apis",

        "audience":
            app_client_id,
    },
    timeout=30,
)

print(
    "Token exchange HTTP:",
    token_response.status_code
)

if not token_response.ok:
    print(token_response.text)
    token_response.raise_for_status()

token_result = token_response.json()

app_token = token_result["access_token"]

print("App audience token acquired")


# ============================================================
# 5. HTTP Session
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "Authorization": f"Bearer {app_token}",
        "Accept": "application/json",
    }
)


# ============================================================
# 6. App にアクセス
#    Session Cookie / CSRF Cookie の取得
# ============================================================

r = session.get(
    f"{app_url}/domain/list-projects",
    timeout=30,
)

print("list-projects HTTP:", r.status_code)

try:
    print(
        json.dumps(
            r.json(),
            indent=2,
            ensure_ascii=False,
        )
    )
except Exception:
    print(r.text)

r.raise_for_status()


# ============================================================
# 7. CSRF Token
# ============================================================

csrf_token = session.cookies.get("csrf_token")

print(
    "CSRF token acquired:",
    bool(csrf_token)
)

print(
    "Cookies:",
    session.cookies.get_dict()
)

if not csrf_token:
    raise RuntimeError(
        "csrf_token cookie が取得できませんでした。"
    )


# ============================================================
# 8. FamilyTree v1 を Session にロード
# ============================================================

r = session.post(
    f"{app_url}/domain/load-from-uc",
    headers={
        "X-CSRF-Token": csrf_token,
    },
    json={
        "domain": DOMAIN_FOLDER,
        "version": DOMAIN_VERSION,
    },
    timeout=60,
)

print("load-from-uc HTTP:", r.status_code)

try:
    load_result = r.json()

    print(
        json.dumps(
            load_result,
            indent=2,
            ensure_ascii=False,
        )
    )

except Exception:
    print(r.text)
    raise

r.raise_for_status()

if not load_result.get("success"):
    raise RuntimeError(
        f"Domain load failed: {load_result}"
    )


# ============================================================
# 9. Domain 状態確認
# ============================================================

r = session.get(
    f"{app_url}/domain/info",
    timeout=30,
)

print("domain/info HTTP:", r.status_code)

domain_info = r.json()

print(
    json.dumps(
        domain_info,
        indent=2,
        ensure_ascii=False,
    )
)

r.raise_for_status()


# ============================================================
# 10. GraphQL Schema 確認
# ============================================================

r = session.get(
    f"{app_url}/dtwin/graphql/schema",
    timeout=30,
)

print("GraphQL schema HTTP:", r.status_code)

try:
    print(
        json.dumps(
            r.json(),
            indent=2,
            ensure_ascii=False,
        )
    )
except Exception:
    print(r.text)

r.raise_for_status()

# COMMAND ----------

GRAPHQL = """
query CheckNames {
  persons(limit: 100) {
    id
    label
    name
    gender
  }
}
"""

r = session.post(
    f"{app_url}/graphql/familytree",
    json={
        "query": GRAPHQL,
        "depth": 1,
    },
    timeout=120,
)

print("HTTP:", r.status_code)
print(
    json.dumps(
        r.json(),
        indent=2,
        ensure_ascii=False,
    )
)

# COMMAND ----------

# 親から子を探す方法を確立できず、子を起点に親を取得
GRAPHQL = """
# 親から子を探す方法を確立できず、子を起点に親を取得
query GetParentsOfRobertAndEmily {
  robert: persons(
    limit: 10
    search: "Robert Smith"
  ) {
    id
    label
    father: hasFather {
      id
      label
    }
    mother: hasMother {
      id
      label
    }
  }

  emily: persons(
    limit: 10
    search: "Emily Smith"
  ) {
    id
    label
    father: hasFather {
      id
      label
    }
    mother: hasMother {
      id
      label
    }
  }
}

"""

r = session.post(
    f"{app_url}/graphql/familytree",
    json={
        "query": GRAPHQL,
        "depth": 1,
    },
    timeout=120,
)

print("HTTP:", r.status_code)
print(
    json.dumps(
        r.json(),
        indent=2,
        ensure_ascii=False,
    )
)

# COMMAND ----------

# 祖父から孫を探す方法を確立できず、孫を起点に親を取得
GRAPHQL = """
# 祖父から孫を探す方法を確立できず、孫を起点に親を取得
query GetGrandfathersOfLisaAndMichael {
  lisa: persons(
    limit: 10
    search: "Lisa Smith"
  ) {
    id
    label
    father: hasFather {
      id
      label
      grandfather: hasFather {
        id
        label
      }
    }
  }

  michael: persons(
    limit: 10
    search: "Michael Smith"
  ) {
    id
    label
    father: hasFather {
      id
      label
      grandfather: hasFather {
        id
        label
      }
    }
  }
}
"""

r = session.post(
    f"{app_url}/graphql/familytree",
    json={
        "query": GRAPHQL,
        "depth": 1,
    },
    timeout=120,
)

print("HTTP:", r.status_code)
print(
    json.dumps(
        r.json(),
        indent=2,
        ensure_ascii=False,
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC EOF