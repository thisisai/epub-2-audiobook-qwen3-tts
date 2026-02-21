[**English README**](./README_EN.md)

# Qwen3-TTS for Mac — Apple Silicon 本機語音合成

在 Apple Silicon Mac（M1/M2/M3/M4）上本機運行 **Qwen3-TTS** 文字轉語音模型。完全離線、不需要雲端 API。

> 基於 [kapi2800/qwen3-tts-apple-silicon](https://github.com/kapi2800/qwen3-tts-apple-silicon)，已中文化介面並修復已知問題。

---

## 功能特色

- **自訂語音** — 14 種內建語音（中/英/日/韓），支援情緒與語速控制
- **語音設計** — 用文字描述想要的語音風格（例如「年輕女性，語調溫柔甜美」）
- **語音複製** — 提供 5 秒音檔即可複製任何人的聲音
- **長文自動分段** — 自動切分長文、逐段生成後合併，突破單次 ~1.5 分鐘限制
- **批次轉換** — 整個資料夾的 `.txt` 一鍵轉成 `.mp3`，輸出以原檔名命名
- **輸出 MP3** — 所有音檔直接轉為 192kbps MP3 歸檔，不自動播放
- **完全離線** — 不需要網路，所有推論都在本機完成
- **Apple Silicon 優化** — 使用 MLX 框架，低記憶體、低溫度

---

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | macOS（Apple Silicon M1/M2/M3/M4） |
| Python | 3.13+（使用 `audioop-lts` 套件） |
| 記憶體 | Lite 模型 ~3GB / Pro 模型 ~6GB |
| 磁碟空間 | 每個模型約 2.9GB |
| 其他 | FFmpeg、Homebrew |

### MLX vs PyTorch 效能比較

| 指標 | PyTorch 模型 | MLX 模型 |
|------|-------------|----------|
| 記憶體用量 | 10+ GB | 2-3 GB |
| CPU 溫度 | 80-90°C | 40-50°C |

---

## 安裝步驟

### 方式一：一鍵安裝（推薦）

```bash
bash setup.sh
```

會自動完成：安裝 Python 3.13、FFmpeg、建立虛擬環境、安裝依賴、修復警告、下載模型、更新 Skill 路徑。

### 方式二：手動安裝

#### 1. Clone 專案

```bash
git clone https://github.com/kapi2800/qwen3-tts-apple-silicon.git
cd qwen3-tts-apple-silicon
```

#### 2. 安裝 Python 3.13（如尚未安裝）

```bash
brew install python@3.13
```

#### 3. 建立虛擬環境並安裝依賴

```bash
/opt/homebrew/bin/python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 安裝 FFmpeg（如尚未安裝）

```bash
brew install ffmpeg
```

#### 5. 下載模型

> **重要：請使用 `huggingface-cli` 或 `hf` 指令下載，不要用 `git clone`。**
> 用 `git clone` 會導致 safetensors 檔案損壞（[Issue #1](https://github.com/kapi2800/qwen3-tts-apple-silicon/issues/1)）。

先建立 models 資料夾：

```bash
mkdir -p models
```

**Pro 模型（1.7B — 最佳品質，建議 RAM 6GB+）：**

```bash
# 自訂語音（必裝）
hf download --local-dir models/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit

# 語音設計
hf download --local-dir models/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit \
  mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit

# 語音複製
hf download --local-dir models/Qwen3-TTS-12Hz-1.7B-Base-8bit \
  mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit
```

**Lite 模型（0.6B — 較快速，適合 RAM 較少的機器）：**

```bash
hf download --local-dir models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit \
  mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit

hf download --local-dir models/Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit \
  mlx-community/Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit

hf download --local-dir models/Qwen3-TTS-12Hz-0.6B-Base-8bit \
  mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit
```

下載完成後目錄結構如下：

```
models/
├── Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit/
│   ├── config.json
│   ├── model.safetensors
│   ├── tokenizer_config.json
│   └── ...
├── Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit/
└── Qwen3-TTS-12Hz-1.7B-Base-8bit/
```

#### 6. 啟動

```bash
source venv/bin/activate
python main.py
```

---

## 使用說明

啟動後會看到主選單：

```
========================================
 Qwen3-TTS 語音合成管理器
========================================

  Pro 模型（1.7B - 最佳品質）
  ---------------------------------
  1. 自訂語音
  2. 語音設計
  3. 語音複製

  Lite 模型（0.6B - 較快速）
  ---------------------------
  4. 自訂語音
  5. 語音設計
  6. 語音複製

  7. 批次轉換（整個資料夾 .txt → .mp3）

  q. 離開
```

### 模式一：自訂語音

選擇內建語音角色，搭配情緒指令和語速控制。

**可用語音：**

| 語言 | 語音角色 |
|------|---------|
| 中文 | Vivian、Serena、Uncle_Fu、Dylan、Eric |
| 英文 | Ryan、Aiden、Ethan、Chelsie、Serena、Vivian |
| 日文 | Ono_Anna |
| 韓文 | Sohee |

**情緒指令範例：**

- 悲傷哭泣，語速緩慢
- 興奮開心，語速很快
- 憤怒大聲喊叫
- 輕聲細語耳語
- 溫柔平靜，語速適中
- 播報新聞的專業語調

### 模式二：語音設計

用自然語言描述你想要的語音風格：

- 「年輕女性，語調溫柔甜美」
- 「中年男性，聲音低沉有磁性」
- 「老年男性，語速緩慢，聲音沙啞」

### 模式三：語音複製

提供一段 5-10 秒的參考音檔，即可複製該語音。支援：

- **快速複製** — 直接拖入音檔使用
- **登錄語音** — 儲存語音供反覆使用
- 支援 WAV、MP3 等格式（非 WAV 會自動透過 FFmpeg 轉換）

### 模式七：批次轉換

將整個資料夾的 `.txt` 檔案一次全部轉成 `.mp3`：

1. 選 `7` 後拖入資料夾（或輸入路徑）
2. 選擇模型、語音、情緒、語速（可全部 Enter 用預設）
3. 確認後自動逐檔轉換

**輸出規則：**
- 每個 `.txt` 對應一個同名 `.mp3`（例如 `第一章.txt` → `第一章.mp3`）
- 輸出位置：`outputs/CustomVoice/`（或對應模式的子資料夾）
- 長文自動分段合併，不受 1.5 分鐘限制

### 書籍有聲書製作流程

`epub_to_chapters.py` 可以讀取 EPUB 電子書，自動按章節分割成獨立 `.txt` 檔，再搭配批次轉換一鍵產出有聲書：

```bash
# 第一步：EPUB 轉章節（需要 venv，依賴 beautifulsoup4）
source venv/bin/activate
python epub_to_chapters.py 我的書.epub --output-dir chapters

# 第二步：批次轉成 MP3
# 開啟 main.py → 選 7 → 拖入 chapters/ 資料夾
python main.py
```

**選項：**

| 參數 | 說明 |
|------|------|
| `--output-dir DIR` | 指定輸出目錄（預設：`chapters`） |
| `--keep-all` | 不過濾，匯出所有章節（包含封面、版權、致謝等） |
| `--no-skip-end` | 不在致謝/附錄處截斷，繼續匯出後續章節 |

**自動過濾規則：**
- 封面、版權頁、目錄、書名頁等非正文頁面 → 自動跳過
- 內容少於 50 字的空白頁 → 自動跳過
- 遇到 `致謝`、`後記`、`附錄` → 截斷，後續不納入（可用 `--no-skip-end` 關閉）
- 輸出檔名格式：`01_章節標題.txt`、`02_章節標題.txt`...，排序與批次模式相容

> **注意：** 加密（DRM）的 EPUB 檔案無法解析，請使用無 DRM 保護的 EPUB。

---

## 使用技巧

- 拖入 `.txt` 檔案可直接朗讀長篇文字，程式會自動分段處理
- 輸入 `q`、`exit` 或 `quit` 可隨時返回上一層
- 語音複製的音檔品質越乾淨，效果越好（避免背景噪音）
- 生成的音檔自動儲存在 `outputs/` 資料夾，格式為 MP3（192kbps）

---

## 目錄結構

```
epub-2-audiobook-qwen3-tts/
├── main.py              # 主程式（互動選單）
├── tts-cli.py           # CLI 工具（供腳本/Skill 呼叫）
├── epub_to_chapters.py  # EPUB 轉章節工具（epub → 多個章節 txt）
├── setup.sh             # 一鍵安裝腳本
├── requirements.txt     # Python 依賴
├── models/              # 模型檔案（需自行下載）
├── voices/              # 已儲存的語音複製檔案
├── outputs/             # 生成的音檔輸出（MP3）
│   ├── CustomVoice/
│   ├── VoiceDesign/
│   └── Clones/
├── chapters/            # epub_to_chapters.py 預設輸出目錄
├── .claude/skills/      # Claude Code Skill 定義
└── venv/                # Python 虛擬環境
```

---

## 常見問題

### `audioop-lts` 安裝失敗

此套件需要 **Python 3.13+**。請確認使用正確版本：

```bash
python --version  # 應顯示 3.13.x
```

### `Invalid json header length` 錯誤

模型下載方式不正確。**不要用 `git clone`**，改用 `hf download`：

```bash
hf download --local-dir models/模型名稱 mlx-community/模型名稱
```

### `mlx_audio not found`

請先啟動虛擬環境：

```bash
source venv/bin/activate
```

### 長文只有 1~2 分鐘音訊

模型單次生成上限約 1200 tokens（對應約 1500 中文字或 1.5 分鐘）。`main.py` 已內建自動分段合併功能，會將長文切成每段 ~1000 字，逐段生成後用 FFmpeg 合併成一個完整 MP3，理論上沒有長度上限。

### tokenizer regex 警告

如果看到 `incorrect regex pattern` 的警告，可在 `venv/lib/python3.13/site-packages/mlx_audio/tts/models/qwen3_tts/qwen3_tts.py` 中找到 `post_load_hook` 方法，將 `AutoTokenizer.from_pretrained()` 包在 `warnings.catch_warnings()` 中靜默處理。此警告不影響功能。

---

## 分享給朋友

可以將整個專案資料夾複製給朋友（包括 `models/` 約 8.7GB）。朋友收到後只需執行：

```bash
cd qwen3-tts
bash setup.sh
```

安裝腳本會自動：
- 安裝 Python 3.13 和 FFmpeg（透過 Homebrew）
- 建立虛擬環境並安裝所有依賴
- 修復 tokenizer 警告
- 偵測已存在的模型（跳過下載）
- 更新 Claude Code Skill 路徑

> **注意**：`venv/` 資料夾不需要複製，腳本會自動重建。如果不想複製 8.7GB 的模型，朋友也可以自行下載（腳本會提示）。

---

## 相關專案

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — 阿里巴巴原始 Qwen3-TTS 模型
- [MLX Audio](https://github.com/Blaizzy/mlx-audio) — Apple MLX 音訊框架
- [MLX Community](https://huggingface.co/mlx-community) — HuggingFace 上的 MLX 轉換模型

---

## 授權

本專案基於 [kapi2800/qwen3-tts-apple-silicon](https://github.com/kapi2800/qwen3-tts-apple-silicon) 修改，遵循原專案授權條款。
