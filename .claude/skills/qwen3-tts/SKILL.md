---
name: qwen3-tts
description: Generate speech audio from text using local Qwen3-TTS model. Use when you need text-to-speech, generate voice audio, create narration, or produce spoken content. Supports Chinese, English, Japanese, Korean voices with emotion and speed control.
argument-hint: "text" [--voice NAME] [--emotion STYLE] [--speed N]
allowed-tools: Bash(/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py *)
user-invocable: true
---

# Qwen3-TTS Local Speech Generation

Generate speech audio from text using a locally running Qwen3-TTS model on Apple Silicon. All processing is done on-device.

> **Note**: If paths in this file don't match your system, run `bash setup.sh` from the project root to auto-fix them.

## Command

```bash
/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py "TEXT" [OPTIONS]
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--voice NAME` | Vivian | Speaker voice |
| `--model MODEL` | pro-custom | Model to use |
| `--emotion TEXT` | Normal tone | Emotion/style instruction |
| `--speed N` | 1.0 | Speed multiplier (0.5-2.0) |
| `--ref-audio PATH` | - | Reference audio for clone mode |
| `--ref-text TEXT` | - | Transcript of reference audio |
| `--no-play` | false | Skip auto-playback |
| `--json` | false | Output as JSON |

## Available Voices

| Language | Voices |
|----------|--------|
| Chinese | Vivian, Serena, Uncle_Fu, Dylan, Eric |
| English | Ryan, Aiden, Ethan, Chelsie, Serena, Vivian |
| Japanese | Ono_Anna |
| Korean | Sohee |

## Models

| Model Key | Description |
|-----------|-------------|
| `pro-custom` | Pro 1.7B - Preset voices with emotion (default) |
| `pro-design` | Pro 1.7B - Create voice from text description |
| `pro-clone` | Pro 1.7B - Clone voice from audio sample |
| `lite-custom` | Lite 0.6B - Faster, less RAM |
| `lite-design` | Lite 0.6B - Faster voice design |
| `lite-clone` | Lite 0.6B - Faster voice clone |

## Emotion/Style Examples

For `--emotion`:
- Chinese: "溫柔平靜，語速適中", "興奮開心，語速很快", "播報新聞的專業語調"
- English: "Calm and gentle", "Excited and energetic", "Professional news anchor"

For `--model pro-design` (voice design mode), `--emotion` describes the voice itself:
- "年輕女性，語調溫柔甜美"
- "中年男性，聲音低沉有磁性"

## Task

Generate audio for: $ARGUMENTS

Steps:
1. Parse the user's request to determine text, voice, emotion, and speed
2. Choose the appropriate model (pro-custom for preset voices, pro-design for custom voice styles)
3. Run the command with `--json` flag to get structured output
4. Report the output file path to the user
5. If the user didn't specify a voice, default to Vivian (Chinese) for Chinese text, or Ryan for English text

## Examples

Basic Chinese:
```bash
/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py "你好，歡迎使用語音合成" --json
```

English with specific voice:
```bash
/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py "Hello world" --voice Ryan --json
```

With emotion:
```bash
/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py "今天天氣真好" --voice Vivian --emotion "興奮開心" --json
```

Voice design mode:
```bash
/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py "你好世界" --model pro-design --emotion "年輕女性，語調溫柔甜美" --json
```

Fast speed:
```bash
/Users/thisisai/Documents/qwen3-tts/venv/bin/python /Users/thisisai/Documents/qwen3-tts/tts-cli.py "快速播報" --speed 1.3 --json
```
