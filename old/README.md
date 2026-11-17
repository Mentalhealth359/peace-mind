# old/

今のアプリでは使っていないファイルの置き場です。どこからも読み込まれていません。
不要と確定したら、このフォルダごと削除してかまいません。

| ファイル | 元の場所 | 使わなくなった理由 |
|---|---|---|
| `requirements.txt` | `peace-mind/requirements.txt` | 古い一覧（Flask・pandas など未使用のものが入っている）。正しい一覧は `peace/requirements.txt` |
| `jinkou.py` | `peace/jinkou.py` | 空のファイル |
| `db.sqlite3.bak-before-0007` | `peace/db.sqlite3.bak-before-0007` | マイグレーション 0007 適用前の DB バックアップ（Git には入れていない。手元にだけある） |
| `migrations-photo/` | `peace/mentalhealth/migrations/photo/` | どこからも参照されていない画像。表示に使っているのは `peace/mentalhealth/static/mentalhealth/photo/` |
