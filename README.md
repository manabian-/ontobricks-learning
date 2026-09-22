# OntoBricks 学習用レポジトリ

OntoBricks を学習・技術検証するための、manabian 個人の学習用リポジトリです。

OntoBricks を利用しながら、Ontology、Knowledge Graph、RDF、SPARQL、GraphQL、Reasoning、SWRL、Action、MCP などの関連技術について、実際に動作確認したコードや設定ファイル、サンプルデータ、メモを整理していきます。

> [!NOTE]
> 本リポジトリは manabian 個人による学習・検証用のリポジトリです。
> OntoBricks および Databricks の公式リポジトリ、公式ドキュメントではありません。

## Purpose

本リポジトリの主な目的は次のとおりです。

* OntoBricks の基本機能を理解する
* Ontology と Knowledge Graph の構築方法を検証する
* OWL / RDF / R2RML などの Semantic Web 技術を学習する
* SPARQL / GraphQL によるグラフ探索を検証する
* Reasoning / Inference の動作を確認する
* SWRL による Business Rule の実装方法を検証する
* Ontology に紐づく Action や Virtual Attribute を検証する
* MCP などの外部ツールとの連携方法を検討する
* OntoBricks の機能や制約について再現可能な形で記録する

## OntoBricks とは

[OntoBricks](https://ontobricks.org/) は、Databricks 上のデータから **Ontology（オントロジー）と Knowledge Graph（ナレッジグラフ）を構築・活用するための Databricks Labs プロジェクト**です。

Unity Catalog で管理されているテーブルに対して、OWL を用いて業務上の概念や関係性を定義し、R2RML により Ontology と実データをマッピングすることで、RDF Triple をベースとした Knowledge Graph を構築できます。


