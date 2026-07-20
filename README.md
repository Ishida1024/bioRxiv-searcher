 # bioRxiv Searcher

Europe PMC で bioRxiv のメタデータを検索し、bioRxiv 公式 API で DOI の詳細情報を取得する Python サービスです。bioRxiv の Web ページはスクレイピングせず、検索結果と詳細情報の出典を分離します。

## 実行

```bash
uv sync
uv run python main.py search "single-cell" --limit 5
uv run python main.py detail 10.1101/2026.01.01.123456
```

検索結果は Europe PMC、詳細情報は bioRxiv API のレスポンスです。CLI はカレントディレクトリの `.biorxiv-searcher.sqlite3` に短期 TTL キャッシュを保存します。別の場所を使う場合は各サブコマンドに `--cache PATH` を指定してください。

## 開発

```bash
uv run pytest -q
```

設計の正式版は [DESIGN.md](DESIGN.md) を参照してください。
