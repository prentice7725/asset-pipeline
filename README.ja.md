# Asset Pipeline

[한국어](README.md) | 日本語

プロンプト、参照画像、プロジェクトの企画書をもとに、ゲーム用の画像や効果音の候補を作成するPython CLIツールです。ComfyUIによる生成、後処理・検証、Asepriteへの書き出しを連携します。

**生成結果は自動承認しません。** ピクセルキャラクターは検証を通過した候補のみをレビューしたうえでStatic Masterとして承認し、SFXも基本検証の後に人が実際に聴いて確認する必要があります。失敗した段階では処理を中断し、記録を保存します。

## 特徴

- **ワークフロー駆動**：ワークフローレジストリで出力種別・機能・状態を管理し、ルーターが最適なワークフローを自動選択
- **品質ゲート**：Pixel Gateで検証に失敗した候補は中断し、書き出しをブロック
- **承認記録の改ざん検知**：承認記録を検証manifest・候補・書き出し画像のハッシュに紐付け、根拠が変われば承認を無効化
- **完全な実行記録**：失敗を含むすべての試行について、ワークフロー・モデル・seed・プロンプト・パラメータ・QA結果を保存
- **AIエージェント連携**：ローカルMCPサーバーとしてCodex等から利用可能

## 対応機能と現在の状況

| 出力種別 | 動作 |
|---|---|
| `PIXEL_STATIC` | ピクセル候補の生成 → 分析 → 安全なアルファ処理 → Pixel Gate → 解像度レビュー → Aseprite書き出し → 明示的な承認 |
| `PIXEL_ANIMATION` | 承認済みのStatic Masterとレビュー済みの既存モーションを用いた8フレームの歩行アニメーション制作、パレット・Pixel Gate検証、Aseprite書き出し |
| `NONPIXEL_IMAGE` | ComfyUIによる画像生成と基本QA。最終的な目視レビューが必要 |
| `NONPIXEL_ANIMATION` | 実験的な契約のみ提供。実際の生産実行は未対応 |
| `SFX` | Stable Audio 3 Mediumによる効果音生成、元のFLAC・PCM WAVを保存、基本的なオーディオQA。試聴レビュー必須 |

現在、ローカル環境で**82件のテスト**が通過しています。初期移行では、実際のAseprite往復検証と、既存アニメーション8フレームのRGBA完全一致を確認しました。その後、Krea2による生成とSFXの実際のCLI・MCP経由の生成も検証しました。

検証の根拠：[初期検証](docs/bootstrap_status.json)、[プロンプト検証](docs/prompt_spec_verification.json)、[SFX検証](docs/sfx_verification.json)、[プラグインの状況](docs/plugin/STATUS.json)
外部プログラム、モデルの重み、ローカルのベンチマーク資料はリポジトリに含めていません。

## インストール

必要な環境：

- Python 3.11以上
- 設定したアドレスで起動しているComfyUI（デフォルトは`http://127.0.0.1:8188`）
- 選択したワークフローに必要なモデルとノード
- ピクセルマスターの制作・書き出し用のAseprite
- アニメーションのデコードとSFXのWAV変換用のFFmpeg（`PATH`から実行可能であること）

Windows PowerShellでのインストール：

```powershell
git clone https://github.com/prentice7725/asset-pipeline.git
cd asset-pipeline
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,motion,mcp]"
assetpipe --help
```

仮想環境を有効化しない場合は、`.venv\Scripts\python.exe`と`.venv\Scripts\assetpipe.exe`を直接使用してください。外部連携はWindowsで検証しており、他のOSはまだ検証していません。

[config/pipeline.yaml](config/pipeline.yaml)でComfyUIのアドレスとタイムアウトを設定します。Asepriteは`aseprite.executable`または`ASEPRITE_PATH`で指定でき、`PATH`と一般的なインストール先も探索します。ワークフローのグラフはPythonコードと分離し、[config/workflows](config/workflows)に配置します。

## Codexでの利用

現在はローカルMCP接続で利用できます。リポジトリが`C:\workspace\asset-pipeline`にある場合：

```powershell
Copy-Item config\mcp_adapter.example.yaml config\mcp_adapter.local.yaml
codex mcp add asset-pipeline -- "C:\workspace\asset-pipeline\.venv\Scripts\assetpipe-mcp.exe" --config "C:\workspace\asset-pipeline\config\mcp_adapter.local.yaml"
```

ローカル設定がすでにある場合はコピーしないでください。設定ファイルの`source_roots`に、作業対象のプロジェクト・アセットのフォルダを追加します。複数のフォルダはYAMLのリストで指定します。

```yaml
core_root: ..
source_roots:
  - C:/workspace/game-a
  - C:/workspace/game-b
  - ../examples
output_root: ../workspace/plugin_runs
```

相対パスは設定ファイルのあるフォルダを基準に解釈します。ソースフォルダは事前に存在している必要があります。設定後にCodexを再起動し、次のように依頼します。

> asset-pipelineのasset_capabilitiesで準備状況を確認して。
>
> game-aプロジェクトに、剣がぶつかる効果音を3秒で作って。音楽と声はなしで。

MCPは既存のコアを呼び出す6つのツールを提供します：`asset_capabilities`、`asset_build_brief`、`asset_route`、`asset_generate`、`asset_continue_animation`、`asset_inspect_run`
サーバーはCodexが起動し、画像・オーディオの生成時にはComfyUIが起動している必要があります。

[ローカルインストール案内](docs/plugin/LOCAL_SETUP.md)と[ツール契約](docs/plugin/MCP_TOOL_CONTRACT.md)を参照してください。プラグインパッケージは作成済みですが、公式Plugin Creatorでの検証と、実際のプラグインホストへのインストールはまだ完了していません。ローカルMCP SDKでの検証とは区別しており、公開プラグインの配布やリモートサービスは含みません。

## プロジェクト別の保存

Briefに`project_id`を指定するか、CLIで`--project game-a`を使用します。省略した場合は`default`を使用し、ソースのパスからプロジェクトを推測することはありません。

```text
MCP: output_root/プロジェクトID/runs/アセットID/実行ID/
CLI: workspace/プロジェクトID/runs/アセットID/実行ID/
```

MCPのリクエスト記録は`output_root/プロジェクトID/requests/`に保存します。続けて作成するアニメーションも元のプロジェクトを維持します。CLIで明示的に`--output`を指定した場合は、そのパスをそのまま使用します。
プロジェクトIDは英数字で始まり、英数字・ハイフン・アンダースコアのみ使用でき、最大64文字です。

## 画像と効果音の生成

一般的な画像の候補：

```powershell
assetpipe create --type nonpixel-image --project game-a --asset-id scout --workflow anima_base --preset smoke --seed 101 --prompt "fantasy scout, short brown hair, blue cloak, light armor, dagger"
```

効果音の候補：

```powershell
assetpipe create --type sfx --project game-a --asset-id sword_hit --duration 3 --prompt "A single metallic sword impact, sharp clang with a short ringing decay, dry close recording, no music, no speech."
```

SFXの長さは1〜30秒で、デフォルトは5秒です。現在、`audio_stable_audio_3_medium`はテキストを直接入力する経路で接続しており、オプションのQwen拡張段階は除外しています。元のFLACと16-bit PCM WAV、および長さ・無音・ピーク・RMSなどのQA記録を保存します。QAを通過した後も試聴レビューが必要です。[SFXの利用案内](docs/SFX.md)

すべての生成コマンドは実行manifestのパスを出力します。リポジトリ外から実行する場合は、サブコマンドの前に`assetpipe --root <リポジトリのパス>`を指定してください。

## Asset Briefと共通プロンプト

入力は[Asset Briefスキーマ](schemas/asset_brief.schema.json)による検証を通過します。プロジェクト・アセットのID、目的、出典、キャラクターの正本となる特徴、制約、アニメーションの要件、ワークフローの希望、禁止要素、未確定事項を記録します。

ドキュメントの根拠は、`EXPLICIT`（明示）、`DERIVED`（根拠のある解釈）、`UNSPECIFIED`（未確定）に区別します。未確定の内容を正本として自動的に確定することはなく、正本はあくまでプロジェクトのドキュメントです。

```powershell
assetpipe brief from-docs tests/fixtures/character_test.md --prepared examples/character_test_brief.yaml --output workspace/document_brief.json
assetpipe route --brief workspace/document_brief.json --output workspace/document_route.json
```

Codexまたは人がドキュメントを読んでBriefを準備します。`from-docs`は準備されたBriefと出典のパスを検証するもので、ドキュメントの内容を自動解釈するものではありません。

プロンプトは、**共通PromptSpec → モデル別アダプター → ComfyUIワークフロー**の順に連携します。Anima・Krea2のアダプターは特徴と制約を保持し、モデル固有の接頭辞をプロファイルで管理します。Tomohiのトリガーワードは`tomohi`です。

```powershell
assetpipe compile-prompt --brief examples/prompt_spec_courier.yaml --output workspace/compiled.json
assetpipe create --brief examples/prompt_spec_courier.yaml --project game-a
```

Kreaのスタイル指定には、選択した説明と出典URLを記録できます。詳細は[PromptSpec案内（韓国語）](docs/PROMPT_SPEC.md)を参照してください。Qwen・Flux・SDXLのアダプターはまだ接続していません。

## ワークフローの選択

[ワークフローレジストリ](config/workflow_registry.yaml)に、出力種別、機能、タグ、優先度、状態、ファイル、モデルを登録します。ルーターは出力種別と機能を確認し、タグ・状態・優先度で選択します。互換性のあるワークフローが明示的に指定された場合はそれを優先します。

| 状態 | 選択ルール |
|---|---|
| `ACTIVE` | 自動選択可能 |
| `VALIDATED` | 明示的に指定すれば使用可能 |
| `EXPERIMENTAL` | ワークフローIDと`allow_experimental: true`が必要 |
| `REJECTED` | 実行禁止 |

対応していない参照画像・negative prompt・画像内の文字の要求は、黙って捨てずにブロックします。選択の根拠と代替候補は`route_decision.json`に記録します。

## ピクセル検証とStatic Masterの承認

```text
Brief → ルーター → 生成候補 → 分析 → 安全なアルファ処理
      → Pixel Gate → 解像度レビュー → Aseprite書き出し → 明示的な承認
```

```powershell
assetpipe create --type pixel-static --project game-a --asset-id warrior --prompt "sword wielding fantasy warrior"
```

自動での変更はバイナリアルファ処理に限定しています。キャラクターのアイデンティティ・衣装・装備・シルエットの意味を自動で再デザインすることはありません。Pixel Gateで失敗した場合は処理を中断し、書き出しをブロックします。レビュー待ちの候補も自動では先に進めません。

`RESOLUTION_REVIEW_REQUIRED`の状態では、`assetpipe.pixel.resolution.record_resolution_review`で、通過した候補の解像度・レビュー担当者・理由を記録します。その後：

```powershell
assetpipe export-static --run <実行フォルダ> --resolution-review <レビュー記録.json>
assetpipe approve-static --run <実行フォルダ> --aseprite-reviewed --reviewed-by "<レビュー担当者>" --reason "<Asepriteでのレビュー結果>"
```

`approve-static`は、検証を通過した静止画の書き出しと、明示的なAsepriteでのレビューがある場合に限り`approval_record.json`を作成します。承認記録は、検証manifest、解像度レポート・レビュー記録、候補、Asepriteマスター、書き出した画像のハッシュに紐付けられます。根拠が変われば承認は無効となり、状態と画像のハッシュだけが記載された旧形式の承認記録では不十分です。

## ピクセルアニメーション

```text
承認済みのStatic Master + レビュー済みの既存モーション
  → 意味に基づくフレーム選択 → CHARACTER_LOCAL_DIRECT → マスターパレット
  → Pixel Gate → Aseprite → スプライトシート
```

Briefの`production`に、`static_master`、`approval_record`、`motion_reference`、`selection`、`direct_profile`を指定します。開始時に承認の根拠を再検証し、新しいモーションの生成は自動では実行しません。

現在検証済みの`blue_tunic_white_matte_v1`は、青いチュニックのキャラクターと白い参照背景による、レビュー済みの8フレーム歩行のみに対応しています。汎用的なキャラクター・動作の復元アルゴリズムではありません。既存のピクセル演算とFFmpegの色変換を保持しています。

[移行のサンプル](examples/pixel_animation_smoke.yaml)は、隣接する既存の`pixel-pipeline`の資料を参照します。その資料は配布しておらず、強化された承認ルールを適用するには、レビュー済みの静止画の書き出しから新たに承認記録を作成する必要があります。

AsepriteではRGBAの往復一致、フレーム数・時間・タグ・メタデータを検証します。アニメーションの結果も最終レビューが必要で、`game_ready: false`のままとなります。Pixel Art Fixerはオプションの復旧ポリシーとしてのみ維持しています。

## 実行記録と開発

失敗を含むすべての生成試行について`run_manifest.json`を記録します。ワークフローのハッシュ・バージョン、モデル・LoRA、seed、実際のプロンプト・パラメータ、ComfyUIの実行ID、段階ごとの状態、QA、出力、時刻を保存します。中間ファイルを削除したり、既存の実行フォルダを上書きしたりすることはありません。
生成物とローカル設定はGitの追跡対象から除外しています。

```powershell
python -m pytest
assetpipe --help
```

Asepriteがない場合は実際のAsepriteテストをスキップし、ローカルのベンチマークがない場合は該当するアニメーションの回帰検証をスキップします。単体テストには起動中のComfyUIは不要です。

```text
src/assetpipe/
  brief/ router/ registry/     # 入力の契約とワークフローの選択
  prompts/                    # 共通プロンプトとモデル別のコンパイル
  providers/ pipelines/       # 外部ツールとの連携と生産経路
  pixel/ motion/              # ピクセル・モーションのインターフェース
  manifests/ cli/             # 実行記録とCLI
  _ported/                    # 移植した検証の実装
integrations/mcp/             # ローカルMCPアダプター
plugin/                      # プラグインの指針と参照資料
config/ schemas/ examples/ tests/ docs/
```

[移行一覧](docs/migration_inventory.json)には、元のハッシュと変更内容を記録しています。bootstrapスクリプトは既存のリポジトリとローカルのベンチマークを必要とする移行ツールであり、通常のインストール手順ではありません。
GUI・Web UI・クラウドへのデプロイ・DB・汎用的なアニメーション復元は、現在の範囲に含めていません。
