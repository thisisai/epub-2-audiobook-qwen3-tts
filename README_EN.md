[**中文版 README**](./README.md)

# Qwen3-TTS for Mac — Local Text-to-Speech on Apple Silicon

Run **Qwen3-TTS** text-to-speech models locally on Apple Silicon Macs (M1/M2/M3/M4). Fully offline, no cloud API required.

> Based on [kapi2800/qwen3-tts-apple-silicon](https://github.com/kapi2800/qwen3-tts-apple-silicon), with a Chinese-localized UI and bug fixes.

---

## Features

- **Custom Voice** — 14 built-in voices (Chinese/English/Japanese/Korean) with emotion and speed control
- **Voice Design** — Describe your desired voice style in natural language (e.g. "young female, soft and gentle tone")
- **Voice Cloning** — Clone any voice with just a 5-second audio sample
- **Auto-Chunking** — Automatically splits long text, generates segments, and merges them, bypassing the ~1.5 min single-pass limit
- **Batch Conversion** — Convert an entire folder of `.txt` files to `.mp3` in one go
- **MP3 Output** — All audio saved as 192kbps MP3
- **Fully Offline** — No internet needed, all inference runs locally
- **Apple Silicon Optimized** — Uses the MLX framework for low memory usage and low temperatures

---

## System Requirements

| Item | Requirement |
|------|-------------|
| OS | macOS (Apple Silicon M1/M2/M3/M4) |
| Python | 3.13+ (uses `audioop-lts` package) |
| RAM | Lite model ~3GB / Pro model ~6GB |
| Disk Space | ~2.9GB per model |
| Other | FFmpeg, Homebrew |

### MLX vs PyTorch Performance

| Metric | PyTorch Model | MLX Model |
|--------|--------------|-----------|
| Memory Usage | 10+ GB | 2-3 GB |
| CPU Temp | 80-90°C | 40-50°C |

---

## Installation

### Option 1: One-Click Install (Recommended)

```bash
bash setup.sh
```

This automatically: installs Python 3.13, FFmpeg, creates a virtual environment, installs dependencies, patches warnings, downloads models, and updates Skill paths.

### Option 2: Manual Install

#### 1. Clone the Project

```bash
git clone https://github.com/kapi2800/qwen3-tts-apple-silicon.git
cd qwen3-tts-apple-silicon
```

#### 2. Install Python 3.13

```bash
brew install python@3.13
```

#### 3. Create Virtual Environment and Install Dependencies

```bash
/opt/homebrew/bin/python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Install FFmpeg

```bash
brew install ffmpeg
```

#### 5. Download Models

> **Important: Use `huggingface-cli` or `hf` to download, NOT `git clone`.**
> Using `git clone` will corrupt safetensors files ([Issue #1](https://github.com/kapi2800/qwen3-tts-apple-silicon/issues/1)).

Create models directory:

```bash
mkdir -p models
```

**Pro Models (1.7B — Best quality, recommended 6GB+ RAM):**

```bash
# Custom Voice (required)
hf download --local-dir models/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit

# Voice Design
hf download --local-dir models/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit \
  mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit

# Voice Cloning
hf download --local-dir models/Qwen3-TTS-12Hz-1.7B-Base-8bit \
  mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit
```

**Lite Models (0.6B — Faster, for machines with less RAM):**

```bash
hf download --local-dir models/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit \
  mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit

hf download --local-dir models/Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit \
  mlx-community/Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit

hf download --local-dir models/Qwen3-TTS-12Hz-0.6B-Base-8bit \
  mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit
```

#### 6. Launch

```bash
source venv/bin/activate
python main.py
```

---

## Usage

### Mode 1: Custom Voice

Choose from built-in voice characters with emotion and speed control.

**Available Voices:**

| Language | Voices |
|----------|--------|
| Chinese | Vivian, Serena, Uncle_Fu, Dylan, Eric |
| English | Ryan, Aiden, Ethan, Chelsie, Serena, Vivian |
| Japanese | Ono_Anna |
| Korean | Sohee |

**Emotion Examples:**
- Sad and crying, slow pace
- Excited and happy, fast pace
- Angry, shouting loudly
- Whispering softly
- Gentle and calm, moderate pace
- Professional news anchor tone

### Mode 2: Voice Design

Describe your desired voice style in natural language:
- "Young female, soft and sweet tone"
- "Middle-aged male, deep and magnetic voice"
- "Elderly male, slow pace, raspy voice"

### Mode 3: Voice Cloning

Provide a 5-10 second reference audio to clone a voice. Supports:
- **Quick Clone** — Drag in an audio file directly
- **Register Voice** — Save a voice for repeated use
- Supports WAV, MP3 formats (non-WAV auto-converted via FFmpeg)

### Mode 7: Batch Conversion

Convert an entire folder of `.txt` files to `.mp3`:

1. Select `7`, then drag in a folder (or enter the path)
2. Choose model, voice, emotion, speed (press Enter for defaults)
3. Confirm and auto-convert

**Output Rules:**
- Each `.txt` becomes a same-named `.mp3` (e.g. `chapter1.txt` → `chapter1.mp3`)
- Output location: `outputs/CustomVoice/` (or the corresponding subfolder)
- Long text auto-chunked and merged, no 1.5 min limit

### EPUB to Audiobook Workflow

`epub_to_chapters.py` reads an EPUB ebook, automatically splits it into individual chapter `.txt` files, then pairs with batch conversion to produce an audiobook:

```bash
# Step 1: EPUB to chapters (requires venv, depends on beautifulsoup4)
source venv/bin/activate
python epub_to_chapters.py my_book.epub --output-dir chapters

# Step 2: Batch convert to MP3
# Launch main.py → select 7 → drag in the chapters/ folder
python main.py
```

**Options:**

| Flag | Description |
|------|-------------|
| `--output-dir DIR` | Output directory (default: `chapters`) |
| `--keep-all` | No filtering, export all chapters (including cover, copyright, etc.) |
| `--no-skip-end` | Don't truncate at acknowledgements/appendix, continue exporting |

**Auto-filter Rules:**
- Cover, copyright page, table of contents, title page → skipped
- Pages with fewer than 50 characters → skipped
- `Acknowledgements`, `Afterword`, `Appendix` → truncated (disable with `--no-skip-end`)
- Output filename format: `01_Chapter_Title.txt`, `02_Chapter_Title.txt`... sorted and compatible with batch mode

> **Note:** DRM-encrypted EPUB files cannot be parsed. Use DRM-free EPUBs only.

---

## Tips

- Drag in a `.txt` file to read long text aloud — the program auto-chunks it
- Type `q`, `exit`, or `quit` to return to the previous menu at any time
- Cleaner reference audio for voice cloning yields better results (avoid background noise)
- Generated audio is saved in the `outputs/` folder as MP3 (192kbps)

---

## Directory Structure

```
epub-2-audiobook-qwen3-tts/
├── main.py              # Main program (interactive menu)
├── tts-cli.py           # CLI tool (for scripts/Skill integration)
├── epub_to_chapters.py  # EPUB to chapters tool (epub → chapter txt files)
├── setup.sh             # One-click install script
├── requirements.txt     # Python dependencies
├── models/              # Model files (download separately)
├── voices/              # Saved voice cloning files
├── outputs/             # Generated audio output (MP3)
│   ├── CustomVoice/
│   ├── VoiceDesign/
│   └── Clones/
├── chapters/            # epub_to_chapters.py default output directory
├── .claude/skills/      # Claude Code Skill definitions
└── venv/                # Python virtual environment
```

---

## FAQ

### `audioop-lts` install fails

This package requires **Python 3.13+**. Verify your version:

```bash
python --version  # Should show 3.13.x
```

### `Invalid json header length` error

Model was downloaded incorrectly. **Do NOT use `git clone`**, use `hf download`:

```bash
hf download --local-dir models/MODEL_NAME mlx-community/MODEL_NAME
```

### `mlx_audio not found`

Activate the virtual environment first:

```bash
source venv/bin/activate
```

### Long text only produces 1-2 minutes of audio

The model has a single-pass limit of ~1200 tokens (~1500 Chinese characters or ~1.5 minutes). `main.py` has built-in auto-chunking that splits text into ~1000-character segments, generates each one, then merges them with FFmpeg into a single MP3. There is theoretically no length limit.

### Tokenizer regex warning

If you see `incorrect regex pattern` warnings, find the `post_load_hook` method in `venv/lib/python3.13/site-packages/mlx_audio/tts/models/qwen3_tts/qwen3_tts.py` and wrap `AutoTokenizer.from_pretrained()` in `warnings.catch_warnings()` to suppress it. This warning does not affect functionality.

---

## Sharing with Friends

Copy the entire project folder (including `models/` ~8.7GB) to a friend. They just need to run:

```bash
cd qwen3-tts
bash setup.sh
```

The setup script will automatically:
- Install Python 3.13 and FFmpeg (via Homebrew)
- Create virtual environment and install dependencies
- Patch tokenizer warnings
- Detect existing models (skip download)
- Update Claude Code Skill paths

> **Note**: The `venv/` folder does not need to be copied — the script rebuilds it. If you don't want to copy 8.7GB of models, your friend can download them separately (the script will prompt).

---

## Related Projects

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — Alibaba's original Qwen3-TTS model
- [MLX Audio](https://github.com/Blaizzy/mlx-audio) — Apple MLX audio framework
- [MLX Community](https://huggingface.co/mlx-community) — MLX-converted models on HuggingFace

---

## License

This project is based on [kapi2800/qwen3-tts-apple-silicon](https://github.com/kapi2800/qwen3-tts-apple-silicon) and follows the original project's license terms.
