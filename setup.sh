#!/bin/bash
#
# Qwen3-TTS 一鍵安裝腳本
# 適用於 Apple Silicon Mac (M1/M2/M3/M4)
#
set -e

echo "========================================="
echo " Qwen3-TTS 安裝腳本"
echo "========================================="
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ── 1. 檢查系統 ──────────────────────────
echo "【1/5】檢查系統環境..."

# 檢查 Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "錯誤：此專案僅支援 Apple Silicon (M1/M2/M3/M4)"
    exit 1
fi
echo "  ✓ Apple Silicon"

# 檢查 Homebrew
if ! command -v brew &>/dev/null; then
    echo "錯誤：請先安裝 Homebrew → https://brew.sh"
    exit 1
fi
echo "  ✓ Homebrew"

# ── 2. 安裝系統依賴 ──────────────────────
echo ""
echo "【2/5】安裝系統依賴..."

# Python 3.13
if ! command -v python3.13 &>/dev/null; then
    echo "  安裝 Python 3.13..."
    brew install python@3.13
else
    echo "  ✓ Python 3.13 已安裝"
fi

# FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "  安裝 FFmpeg..."
    brew install ffmpeg
else
    echo "  ✓ FFmpeg 已安裝"
fi

# ── 3. 建立虛擬環境 ──────────────────────
echo ""
echo "【3/5】建立 Python 虛擬環境..."

if [ -d "venv" ]; then
    # 檢查 venv 的 Python 版本
    VENV_PY_VER=$("$PROJECT_DIR/venv/bin/python" --version 2>/dev/null || echo "unknown")
    if [[ "$VENV_PY_VER" == *"3.13"* ]]; then
        echo "  ✓ 虛擬環境已存在 ($VENV_PY_VER)"
    else
        echo "  虛擬環境 Python 版本不符，重建中..."
        rm -rf venv
        python3.13 -m venv venv
        echo "  ✓ 虛擬環境已重建"
    fi
else
    python3.13 -m venv venv
    echo "  ✓ 虛擬環境已建立"
fi

# ── 4. 安裝 Python 依賴 ──────────────────
echo ""
echo "【4/5】安裝 Python 套件（可能需要幾分鐘）..."

"$PROJECT_DIR/venv/bin/pip" install --upgrade pip --quiet
"$PROJECT_DIR/venv/bin/pip" install -r requirements.txt --quiet
echo "  ✓ 所有套件已安裝"

# ── 5. 修復 Tokenizer 警告 ───────────────
echo ""
echo "【5/5】套用 Tokenizer 警告修復..."

# 找到 qwen3_tts.py 的位置
QWEN3_TTS_PY=$(find "$PROJECT_DIR/venv" -path "*/mlx_audio/tts/models/qwen3_tts/qwen3_tts.py" 2>/dev/null | head -1)

if [ -n "$QWEN3_TTS_PY" ]; then
    # 檢查是否已經修復過
    if grep -q "catch_warnings" "$QWEN3_TTS_PY" 2>/dev/null; then
        echo "  ✓ 已修復過，跳過"
    else
        # 備份原檔
        cp "$QWEN3_TTS_PY" "${QWEN3_TTS_PY}.bak"

        # 使用 Python 進行精確替換
        "$PROJECT_DIR/venv/bin/python" -c "
import re

with open('$QWEN3_TTS_PY', 'r') as f:
    content = f.read()

# 找到 post_load_hook 中的 tokenizer 載入段落並替換
old_pattern = r'(def post_load_hook\(cls, model.*?\"\"\".*?\n)(.*?)(model\.tokenizer\s*=\s*AutoTokenizer\.from_pretrained\(str\(model_path\)\))'
new_code = '''        try:
            import warnings
            from transformers import AutoTokenizer

            with warnings.catch_warnings():
                warnings.filterwarnings(\"ignore\", message=\".*incorrect regex pattern.*\")
                model.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        except Exception as e:
            print(f\"Warning: Could not load tokenizer: {e}\")'''

# 簡單替換：找到 AutoTokenizer 那行並替換整個 try block
if 'from transformers import AutoTokenizer' in content and 'catch_warnings' not in content:
    # 替換原始的 try block
    content = content.replace(
        '''        try:
            from transformers import AutoTokenizer

            model.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        except Exception as e:
            print(f\"Warning: Could not load tokenizer: {e}\")''',
        '''        try:
            import warnings
            from transformers import AutoTokenizer

            with warnings.catch_warnings():
                warnings.filterwarnings(\"ignore\", message=\".*incorrect regex pattern.*\")
                model.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        except Exception as e:
            print(f\"Warning: Could not load tokenizer: {e}\")'''
    )

    with open('$QWEN3_TTS_PY', 'w') as f:
        f.write(content)
    print('  ✓ Tokenizer 警告已修復')
else:
    print('  ✓ 無需修復或已修復')
"
    fi
else
    echo "  ⚠ 找不到 qwen3_tts.py，請確認 mlx_audio 已安裝"
fi

# ── 6. 下載模型 ──────────────────────────
echo ""
echo "【下載模型】檢查模型..."

mkdir -p models

HF_CMD="$PROJECT_DIR/venv/bin/hf"
if [ ! -f "$HF_CMD" ]; then
    HF_CMD="$PROJECT_DIR/venv/bin/huggingface-cli"
fi

download_model() {
    local folder="$1"
    local repo="$2"
    local target="$PROJECT_DIR/models/$folder"

    if [ -d "$target" ] && [ "$(ls -A "$target" 2>/dev/null)" ]; then
        echo "  ✓ $folder 已存在"
    else
        echo "  下載 $folder..."
        echo "    （約 2.9GB，請耐心等待）"
        "$HF_CMD" download --local-dir "$target" "$repo"
        echo "  ✓ $folder 下載完成"
    fi
}

echo ""
echo "將下載 Pro 模型（1.7B）— 共約 8.7GB"
echo "如需 Lite 模型，下載完成後可手動執行相關指令（見 README）"
echo ""
read -p "開始下載？(Y/n) " DOWNLOAD_CONFIRM
DOWNLOAD_CONFIRM=${DOWNLOAD_CONFIRM:-Y}

if [[ "$DOWNLOAD_CONFIRM" =~ ^[Yy]$ ]]; then
    download_model "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit" "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"
    download_model "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit" "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit"
    download_model "Qwen3-TTS-12Hz-1.7B-Base-8bit" "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
else
    echo "  跳過模型下載（稍後可重新執行此腳本）"
fi

# ── 完成 ─────────────────────────────────
echo ""
echo "========================================="
echo " 安裝完成！"
echo "========================================="
echo ""
echo "使用方式："
echo ""
echo "  互動模式："
echo "    source venv/bin/activate"
echo "    python main.py"
echo ""
echo "  CLI 模式："
echo "    $PROJECT_DIR/venv/bin/python $PROJECT_DIR/tts-cli.py \"你好世界\""
echo ""

# 快速驗證
echo "驗證安裝..."
"$PROJECT_DIR/venv/bin/python" -c "
import mlx.core as mx
print(f'  ✓ MLX 後端: {mx.default_device()}')
" 2>/dev/null || echo "  ⚠ MLX 驗證失敗"

echo ""
echo "完成！"
