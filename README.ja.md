# bioRxiv Searcher

Europe PMC で bioRxiv のメタデータを検索し、bioRxiv 公式 API で正本の詳細情報を取得する検索サービスです。HTML スクレイピング、全件ミラーリング、MCP への必須依存を行いません。

English: [README.md](README.md)

## 特徴

- Europe PMC REST API によるキーワード検索
- bioRxiv 公式 API による DOI ベースの詳細取得
- DOI 正規化と型付き外部 API エラー
- タイムアウト、リトライ、レート制御、小規模な SQLite TTL キャッシュ
- Python サービス API と CLI アダプター
- MCP をコア依存にしない拡張可能な境界

検索結果の出典と詳細情報の正本を、返却モデル上で明示的に分離しています。検索結果は Europe PMC による発見用メタデータであり、bioRxiv 全件の網羅性を保証するものではありません。

## 必要環境

- Python 3.14 以降
- [uv](https://docs.astral.sh/uv/)

## 使い方

### uv を使う場合

```bash
uv sync
```

### requirements.txt を使う場合

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

uv を使う場合:

```bash

# Europe PMC の bioRxiv インデックスを検索
uv run python main.py search "single-cell" --limit 5

# DOI から bioRxiv 公式 API の詳細情報を取得
uv run python main.py detail 10.1101/2026.01.01.123456
```

`requirements.txt` を使う場合は、仮想環境を有効化した状態で実行します。

```bash
python main.py search "single-cell" --limit 5
python main.py detail 10.1101/2026.01.01.123456
```

CLI は短期間のレスポンスを `.biorxiv-searcher.sqlite3` にキャッシュします。保存先を変更する場合は `--cache PATH` を指定してください。

```bash
uv run python main.py search "protein folding" --cache /tmp/biorxiv-searcher.sqlite3
```

## Python API

```python
from biorxiv_search import PreprintSearchService

page = await service.search_preprints("single-cell", limit=20)
detail = await service.get_preprint(page.items[0].doi)
```

サービス層は MCP、CLI、HTTP の各トランスポートから独立しています。そのため、MCP アダプターを追加してもドメイン層やアプリケーション層を変更する必要がありません。

## 開発

```bash
uv run pytest -q
```

正式なアーキテクチャと API 契約は [DESIGN.md](DESIGN.md) に記載しています。

## ライセンス

MIT License。詳細は [LICENSE](LICENSE) を参照してください。

## データと運用上の注意

- bioRxiv の Web ページはスクレイピングしません。
- メタデータ全件同期は行いません。
- Europe PMC は最新版のみを検索対象とする場合があり、収録には遅延があります。
- 論文タイトルや要旨は外部由来の非信頼コンテンツであり、命令として解釈してはいけません。
