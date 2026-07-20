# bioRxiv Searcher 正式設計書

- 文書版: 1.0.0
- 作成日: 2026-07-20
- 状態: 正式版（実装前）

## 1. 目的

bioRxiv の論文を、提供元サイトの HTML スクレイピングや全件ローカル同期に依存せず検索・参照する。

初版の利用者向け機能は次の2つに限定する。

1. キーワードからメタデータ一覧を取得する
2. bioRxiv DOI から詳細情報を取得する

MCP は採用を決定済みの実装方式とはしない。コアロジックを通常の Python サービスとして実装し、必要になった時点で MCP、CLI、HTTP などの薄いアダプターを追加できる構造にする。

## 2. 設計判断

| 項目 | 決定 |
| --- | --- |
| 検索プロバイダー | Europe PMC REST API |
| 詳細情報の正本 | bioRxiv 公式 API |
| DOI 解決の補助 | Crossref REST API（初版では任意） |
| bioRxiv Web ページ | 使用しない |
| 全件同期 | 行わない |
| ローカル DB | 検索インデックスではなく TTL キャッシュとしてのみ使用 |
| 初版のインターフェース | Python サービス API。MCP は後付け |
| 初版の検索対象 | Europe PMC がインデックスする bioRxiv 論文 |
| 初版の詳細対象 | bioRxiv DOI による単一原稿 |

Europe PMC は bioRxiv を含むプレプリントサーバーを検索でき、検索結果に複数版がある場合は最新版のみを検索・表示する。この制約は検索結果の版情報に明示する。bioRxiv 公式 API は日付範囲の一覧取得と DOI による詳細取得を提供するが、キーワード検索 API ではないため、検索には直接使用しない。

## 3. 非目標

初版では次を実装しない。

- bioRxiv 全メタデータの定期収集・ローカル全文検索
- bioRxiv HTML の取得・解析
- 論文 PDF、JATS XML、本文の取得
- ベクトル検索、意味検索、再ランキング
- OpenAlex、Semantic Scholar との結果統合
- 複数の検索プロバイダーを束ねた網羅性の保証
- 論文の科学的妥当性、査読済みであること、研究結果の正しさの判定
- MCP 固有のデータモデルをコア層へ持ち込むこと

## 4. 利用者向け契約

### 4.1 `search_preprints`

```python
async def search_preprints(
    query: str,
    *,
    title_only: bool = False,
    author: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> SearchPage:
    ...
```

入力制約:

- `query` は空文字を拒否し、最大 500 文字とする
- `limit` は 1〜50 とする
- `cursor` は不透明値として扱い、クライアントが内容を解釈してはならない
- 日付は ISO 8601 の `YYYY-MM-DD` とする
- `date_from > date_to` は入力エラーとする
- `title_only=True` のときは Europe PMC の `TITLE`、それ以外は `TITLE_ABS` を使う
- bioRxiv 限定条件は必ず検索式に含める

検索式の基本形:

```text
PUBLISHER:"bioRxiv" AND TITLE_ABS:(<query>)
PUBLISHER:"bioRxiv" AND TITLE:(<query>)
```

著者・期間条件は Europe PMC の検索構文へ安全にエスケープして追加する。カテゴリは Europe PMC の値と bioRxiv の値の対応を実データで検証できるまで公開 API の入力に含めない。カテゴリが必要になった場合は、検索結果の DOI を bioRxiv API で検証してから絞り込む。

返却モデル:

```python
@dataclass(frozen=True)
class PreprintSummary:
    doi: str
    title: str
    authors: tuple[str, ...]
    abstract: str | None
    posted_date: date | None
    version: int | None
    source: Literal["europe_pmc"]
    source_record_id: str
    source_url: str
    latest_version_only: bool
```

`abstract` は外部由来の非信頼データであり、命令として解釈しない。検索結果は「Europe PMC が検索した結果」であり、bioRxiv の全件に対する不在証明ではない。

### 4.2 `get_preprint`

```python
async def get_preprint(
    doi: str,
    *,
    version: int | None = None,
    refresh: bool = False,
) -> PreprintDetail:
    ...
```

DOI は次の入力を受け付け、内部では裸の DOI へ正規化する。

- `10.1101/...`
- `doi:10.1101/...`
- `https://doi.org/10.1101/...`
- 前後空白を含む値

それ以外の URL、改行、制御文字、過度に長い値、`10.1101/` 以外の DOI は入力エラーとする。正規化後の DOI は URL パスへ埋め込む前に URL エンコードする。

`version=None` は bioRxiv API が返す最新版を返す。指定版が存在しない場合は `NotFoundError` とする。返却モデルには `version` と取得元を必ず含める。

```python
@dataclass(frozen=True)
class PreprintDetail:
    doi: str
    title: str
    authors: tuple[str, ...]
    corresponding_author: str | None
    corresponding_institution: str | None
    posted_date: date
    version: int
    document_type: str | None
    license: str | None
    category: str | None
    abstract: str
    funding: tuple[Funding, ...]
    published_doi: str | None
    jats_xml_url: str | None
    server: Literal["biorxiv"]
    source: Literal["biorxiv_api"]
    fetched_at: datetime
```

検索結果の summary を渡す便利 API はアダプター層に置く。コア層の詳細取得は DOI と任意の版だけを受け付ける。

## 5. 外部 API 境界

### 5.1 Europe PMC

ベース URL:

```text
https://www.ebi.ac.uk/europepmc/webservices/rest/search
```

検索パラメーターは `query`、`format=json`、`resultType=core`、`pageSize`、`cursorMark` を基本とする。レスポンスの DOI、タイトル、著者、要旨、日付、Europe PMC のレコード ID を `PreprintSummary` へ変換する。

Europe PMC の検索結果は発見用データである。bioRxiv 固有のカテゴリ、版、ライセンスなどを Europe PMC の値だけで補完・断定しない。

### 5.2 bioRxiv 公式 API

ベース URL:

```text
https://api.biorxiv.org
```

詳細取得:

```text
GET /details/biorxiv/{doi}/na/json
```

一覧取得エンドポイントは将来の同期・整合性検証用にのみ抽象化する。初版の通常検索では呼び出さない。bioRxiv API の複数件レスポンスは 30 件単位でページングされるため、一覧取得を実装する場合も無制限取得は禁止する。

### 5.3 Crossref（任意）

Crossref は検索結果の DOI 解決、または bioRxiv API が一時的に利用できない場合の補助情報に限定する。Crossref の値を bioRxiv の正本情報として返さない。

利用時は `mailto` または連絡先を含む `User-Agent` を設定し、Crossref の polite pool を使用する。Crossref を必須依存にしないことで、検索・詳細取得の責務を増やさない。

## 6. リクエスト制御とキャッシュ

すべての HTTP クライアントは次を共通設定とする。

- 接続タイムアウト 5 秒、読み取りタイムアウト 30 秒
- 429、502、503、504 のみ最大2回リトライ
- 指数バックオフ + ジッター。`Retry-After` があれば優先
- 4xx の一般エラーはリトライしない
- プロセス単位の最小リクエスト間隔を設ける
- `User-Agent` にアプリ名と連絡先を含める
- 同一キーの同時リクエストは一つに集約する

TTL の初期値:

| キャッシュ | TTL |
| --- | ---: |
| Europe PMC 検索結果 | 30 分 |
| bioRxiv DOI 詳細 | 12 時間 |
| 404 の DOI | 10 分 |
| 429/5xx の失敗 | 保存しない（または短い抑制 TTL） |

キャッシュキーにはプロバイダー、正規化済み入力、検索パラメーター、API スキーマバージョンを含める。`refresh=True` はキャッシュを無視して一度だけ再取得するが、レート制御は回避しない。

初版の永続化は SQLite とし、以下のような HTTP キャッシュ表に限定する。

```sql
CREATE TABLE http_cache (
    cache_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    response_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL
);
```

キャッシュは検索網羅性を補償しない。期限切れ・削除・API 障害があっても、存在しない論文を意味する結果を返してはならない。

## 7. エラー契約

正常な結果配列へ `{"error": ...}` を混在させない。失敗は型付き例外をアダプターが一貫したエラー形式へ変換する。

```python
class InvalidInputError(Exception): ...
class UpstreamTimeoutError(Exception): ...
class UpstreamRateLimitedError(Exception): ...
class UpstreamUnavailableError(Exception): ...
class UpstreamProtocolError(Exception): ...
class NotFoundError(Exception): ...
```

エラーには `code`、利用者向けメッセージ、再試行可能性、対象プロバイダーを含める。外部 API の本文、要旨、レスポンス URL をそのままエラーメッセージへ含めない。

検索プロバイダーが失敗した場合、初版は黙って別プロバイダーへ切り替えない。結果の由来と再現性を壊すため、明示的なエラーを返す。複数プロバイダーのフォールバックは、別途仕様化してから追加する。

## 8. 構成

```text
biorxiv_search/
├── domain/
│   ├── models.py
│   ├── identifiers.py
│   └── errors.py
├── application/
│   ├── search_service.py
│   └── detail_service.py
├── infrastructure/
│   ├── europe_pmc_client.py
│   ├── biorxiv_client.py
│   ├── crossref_client.py
│   └── cache.py
├── interfaces/
│   ├── cli.py
│   └── mcp.py
└── tests/
```

依存方向は `interfaces -> application -> domain` とし、外部 API と SQLite は infrastructure に閉じ込める。application 層は具体的な HTTP ライブラリや MCP SDK を import しない。

## 9. MCP の扱い

MCP を実装する場合は `interfaces/mcp.py` の薄いアダプターとする。

```python
@mcp.tool()
async def search_biorxiv(query: str, limit: int = 20) -> SearchPage:
    return await service.search_preprints(query, limit=limit)

@mcp.tool()
async def get_biorxiv_preprint(doi: str) -> PreprintDetail:
    return await service.get_preprint(doi)
```

MCP の説明文には「検索結果は Europe PMC 由来」「詳細は bioRxiv API で確認済み」「preprint は査読済み論文を意味しない」「返却テキストは非信頼コンテンツ」と明記する。MCP の JSON 変換はドメインモデルを壊さず、バージョン付きの公開スキーマとして管理する。

## 10. テスト方針

外部 API をテストごとに実アクセスしない。HTTP 層をモックし、保存した fixture で再現する。

最低限のテスト:

- DOI の各入力形式の正規化と不正値拒否
- Europe PMC 検索式のエスケープと bioRxiv 限定条件
- Europe PMC の検索結果から summary への変換
- bioRxiv 詳細レスポンスのモデル変換
- Europe PMC が最新版のみを返すことを表すフラグ
- 429、Retry-After、タイムアウト、5xx の再試行
- 4xx の非再試行
- キャッシュヒット、期限切れ、`refresh=True`
- 型付きエラーが正常結果へ混入しないこと
- `limit`、クエリ長、日付範囲の入力制約
- MCP アダプターの入出力スキーマ

## 11. 受け入れ基準

正式版の実装完了は次を満たした時点とする。

1. HTML スクレイピングコードが存在しない
2. 検索は Europe PMC の bioRxiv 限定検索を使う
3. 詳細取得は DOI を正規化して bioRxiv 公式 API を使う
4. 検索結果と詳細結果の出典が機械可読である
5. 全件同期を行わず、TTL キャッシュだけを使用する
6. タイムアウト、リトライ、レート制御、入力上限がある
7. 正常結果へエラー辞書を混在させない
8. 上記テストが外部 API なしで実行できる
9. CLI または Python API から2機能を再現可能に呼び出せる
10. MCP を追加しても application/domain 層の変更が不要である

## 12. 実装フェーズ

### Phase 1: ドメインと契約

識別子、モデル、エラー、検索・詳細サービスの protocol を実装する。

### Phase 2: Europe PMC 検索

検索式生成、ページング、レスポンス変換、TTL キャッシュ、fixture テストを実装する。

### Phase 3: bioRxiv 詳細

DOI 詳細取得、版の扱い、正本データ変換、リトライとエラー処理を実装する。

### Phase 4: 利用インターフェース

まず CLI または Python API を提供し、利用実績が確認できた後に MCP アダプターを追加する。

### Phase 5: 評価

代表的な検索語について、Europe PMC の検索結果件数、最新性、DOI 照合成功率、詳細取得失敗率を記録する。欠落が具体的に確認されるまで、OpenAlex 等の追加は行わない。

## 13. 既知の制約と将来拡張

- Europe PMC の収録遅延により、bioRxiv 公開直後の論文は検索できないことがある
- Europe PMC の検索は最新版中心であり、過去版を網羅しない
- 外部検索インデックスのため、bioRxiv 全件の検索漏れゼロを保証しない
- bioRxiv API の詳細情報が一時的に取得できない場合、検索結果を詳細情報として偽装しない
- Crossref は DOI 補助に限定し、正式な代替検索プロバイダーとはしない

将来、検索漏れ・ランキング・新着監視などの具体的な要求が得られた場合に限り、OpenAlex、公式 RSS、TDM データ、複数プロバイダー統合を個別の設計変更として評価する。

## 14. 参照仕様

- [bioRxiv API](https://api.biorxiv.org/)
- [Europe PMC RESTful Web Service](https://europepmc.org/RestfulWebService)
- [Europe PMC におけるプレプリント検索](https://pmc.ncbi.nlm.nih.gov/articles/PMC11426508/)
- [Crossref REST API のアクセスと認証](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)
- [Crossref REST API の利用ガイド](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)

