# EPIC 6 — Infrastructure Hardening

- **Issue**: noema-agent #9
- **DoD**: Docker reproducible / Build documented / Minimal runtime footprint
- **Date**: 2026-05-15

---

## 構成概要

```
noema-agent/
├── Dockerfile             # Multi-stage build (builder / prod / dev)
├── docker-compose.yml     # Service definitions (agent / agent-dev)
├── requirements.txt       # Prod deps only (fastapi, uvicorn, pydantic)
├── requirements-dev.txt   # Dev/test deps (pytest, httpx, requests)
└── docs/
    └── EPIC6_Infrastructure.md
```

---

## Docker ビルド

### Production

```bash
# イメージビルド
docker build --target prod -t noema-agent:prod .

# 起動
docker run -p 8000:8000 noema-agent:prod

# または compose で
docker compose up agent
```

### Dev / テスト

```bash
# Dev イメージビルド
docker build --target dev -t noema-agent:dev .

# hot-reload 付き起動 (port 8001)
docker compose up agent-dev

# テスト実行
docker compose run --rm agent-dev pytest tests/ -v
```

---

## Multi-stage 設計

| Stage | ベース | 内容 | 用途 |
|---|---|---|---|
| `builder` | python:3.11-slim | venv 作成、prod deps インストール | 中間 |
| `prod` | python:3.11-slim | venv + app のみ。非 root ユーザー | 本番 |
| `dev` | prod (継承) | + dev deps + tests mount | 開発/CI |

**prod イメージに含まれないもの:** pytest / httpx / requests / build tools / pip

---

## 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `MAX_PAYLOAD_BYTES` | `65536` (64KB) | constraint_engine の payload size 上限 |

---

## ヘルスチェック

```bash
curl http://localhost:8000/health
# {"status": "healthy", "executor": "ready", "supported_tasks": ["echo"]}

curl http://localhost:8000/
# {"service": "noema-agent", "version": "3.0.0", ...}
```

---

## セキュリティ方針

- 非 root ユーザー (`noema`) で実行
- prod イメージにテストコード・テスト依存物なし
- `python:3.11-slim` ベース (不要なシステムパッケージを排除)
- `--no-access-log` で prod ログに request path を残さない (privacy)

---

## EPIC 2 との接続

`MAX_PAYLOAD_BYTES` 環境変数は `app/constraint_engine.py` が読み取る:

```python
_MAX_PAYLOAD_BYTES = int(os.environ.get("MAX_PAYLOAD_BYTES", 65_536))
```

Docker 経由で constraint limit を外部から制御可能。

---

## 既知の制限 (EPIC 6 スコープ外)

- `_NETWORK_DEPENDENT_TASK_TYPES` が現状空集合。実用的なタスクタイプが追加されたタイミングで埋めること (EPIC 2 チェック時の指摘)
- TLS / reverse proxy 設定は本 EPIC のスコープ外
- CI パイプラインへの組み込みは別途
