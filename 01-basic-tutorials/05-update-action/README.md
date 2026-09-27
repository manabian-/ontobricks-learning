# 05 - データ更新が伴う Action の実装編

OntoBricks 入門シリーズのデータ更新が伴う Action の実装編です。シンプルな Action の実装編として、ドキュメントにて`Class Actions (Unity Catalog functions)`として紹介されている機能を実装します。

- [OntoBricks User Guide — OntoBricks docs](https://ontobricks.org/documentation/user-guide.html#class-actions-unity-catalog-functions)

詳細な手順は下記の記事にて紹介しています。

- [Databricks 上でオントロジーとナレッジグラフを構築・活用するための OntoBricks 入門シリーズ 5. データ更新を伴う Action の実装編 #rdf - Qiita](https://qiita.com/manabian/items/1343185d47b7226a01b9)

## Assets


| # | 種別 | ファイル名 | 役割 |
| --- | --- | --- | --- |
| 1 | Notebook | action_demo_02 | Customer Journey 実装用ノートブック |
| 2 | File | action_demo_02_ontology.ttl | オントロジー定義（Turtle 形式） |
| 3 | File | action_demo_02_r2rml_mapping.ttl | R2RML マッピング定義 |
