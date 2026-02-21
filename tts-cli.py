#!/usr/bin/env python3
"""
Qwen3-TTS CLI — Non-interactive wrapper for skill/agent integration.

Usage:
    python tts-cli.py "要說的文字"
    python tts-cli.py "Hello world" --voice Ryan --speed 1.3
    python tts-cli.py "描述語音風格" --mode design --emotion "年輕女性，語調溫柔甜美"
"""

import os
import sys
import argparse
import shutil
import time
import re
import subprocess
import warnings
import gc
import json
from datetime import datetime
from pathlib import Path

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*incorrect regex pattern.*")
warnings.filterwarnings("ignore", message=".*model of type qwen3_tts.*")

BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
VOICES_DIR = BASE_DIR / "voices"
OUTPUT_DIR = BASE_DIR / "outputs"
SAMPLE_RATE = 24000

MODELS = {
    "pro-custom":  {"folder": "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",  "mode": "custom",  "subfolder": "CustomVoice"},
    "pro-design":  {"folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",  "mode": "design",  "subfolder": "VoiceDesign"},
    "pro-clone":   {"folder": "Qwen3-TTS-12Hz-1.7B-Base-8bit",         "mode": "clone",   "subfolder": "Clones"},
    "lite-custom": {"folder": "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",  "mode": "custom",  "subfolder": "CustomVoice"},
    "lite-design": {"folder": "Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit",  "mode": "design",  "subfolder": "VoiceDesign"},
    "lite-clone":  {"folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit",         "mode": "clone",   "subfolder": "Clones"},
}

ALL_VOICES = {
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"],
}


def get_model_path(folder_name):
    full_path = MODELS_DIR / folder_name
    if not full_path.exists():
        return None
    snapshots_dir = full_path / "snapshots"
    if snapshots_dir.exists():
        subs = [f for f in snapshots_dir.iterdir() if not f.name.startswith(".")]
        if subs:
            return subs[0]
    return full_path


def generate(text, voice, model_key, emotion, speed, no_play, ref_audio=None, ref_text=None):
    try:
        from mlx_audio.tts.utils import load_model
        from mlx_audio.tts.generate import generate_audio
    except ImportError:
        return {"error": "mlx_audio not found. Run: source venv/bin/activate"}

    info = MODELS.get(model_key)
    if not info:
        return {"error": f"Unknown model: {model_key}. Valid: {', '.join(MODELS.keys())}"}

    model_path = get_model_path(info["folder"])
    if not model_path:
        return {"error": f"Model not found: {info['folder']}. Run hf download first."}

    # Load model
    try:
        model = load_model(str(model_path))
    except Exception as e:
        return {"error": f"Failed to load model: {e}"}

    # Generate audio
    temp_dir = BASE_DIR / f"temp_{int(time.time())}_{os.getpid()}"
    temp_dir.mkdir(exist_ok=True)

    try:
        if info["mode"] == "custom":
            generate_audio(
                model=model, text=text, voice=voice,
                instruct=emotion, speed=speed,
                output_path=str(temp_dir),
            )
        elif info["mode"] == "design":
            generate_audio(
                model=model, text=text,
                instruct=emotion,
                output_path=str(temp_dir),
            )
        elif info["mode"] == "clone":
            if not ref_audio:
                return {"error": "Clone mode requires --ref-audio"}
            generate_audio(
                model=model, text=text,
                ref_audio=ref_audio, ref_text=ref_text or ".",
                output_path=str(temp_dir),
            )

        source = temp_dir / "audio_000.wav"
        if not source.exists():
            return {"error": "Audio generation produced no output"}

        # Save to outputs
        out_dir = OUTPUT_DIR / info["subfolder"]
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%H-%M-%S")
        clean = re.sub(r"[^\w\s-]", "", text)[:20].strip().replace(" ", "_") or "audio"
        filename = f"{ts}_{clean}.wav"
        final_path = out_dir / filename

        shutil.move(str(source), str(final_path))

        # Play audio
        if not no_play:
            try:
                subprocess.run(
                    ["afplay", str(final_path)],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                pass

        return {
            "status": "success",
            "file": str(final_path),
            "text": text,
            "voice": voice,
            "model": model_key,
            "emotion": emotion,
            "speed": speed,
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        gc.collect()


def main():
    parser = argparse.ArgumentParser(
        description="Qwen3-TTS CLI - Generate speech audio from text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Models:
  pro-custom   Pro Custom Voice (1.7B, default)
  pro-design   Pro Voice Design (1.7B)
  pro-clone    Pro Voice Clone (1.7B)
  lite-custom  Lite Custom Voice (0.6B)
  lite-design  Lite Voice Design (0.6B)
  lite-clone   Lite Voice Clone (0.6B)

Voices:
  Chinese:  Vivian, Serena, Uncle_Fu, Dylan, Eric
  English:  Ryan, Aiden, Ethan, Chelsie, Serena, Vivian
  Japanese: Ono_Anna
  Korean:   Sohee

Examples:
  python tts-cli.py "你好世界"
  python tts-cli.py "Hello" --voice Ryan --speed 1.3
  python tts-cli.py "描述" --model pro-design --emotion "年輕女性，語調甜美"
  python tts-cli.py "複製語音" --model pro-clone --ref-audio voice.wav
""",
    )

    parser.add_argument("text", help="Text to convert to speech")
    parser.add_argument("--voice", default="Vivian", help="Speaker voice (default: Vivian)")
    parser.add_argument("--model", default="pro-custom", choices=MODELS.keys(), help="Model (default: pro-custom)")
    parser.add_argument("--emotion", default="", help="Emotion/style instruction")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (default: 1.0)")
    parser.add_argument("--ref-audio", default=None, help="Reference audio for clone mode")
    parser.add_argument("--ref-text", default=None, help="Transcript of reference audio")
    parser.add_argument("--no-play", action="store_true", help="Don't auto-play audio")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--list-voices", action="store_true", help="List all available voices")

    args = parser.parse_args()

    if args.list_voices:
        for lang, voices in ALL_VOICES.items():
            print(f"{lang}: {', '.join(voices)}")
        return

    # Validate voice for custom mode
    if args.model.endswith("-custom"):
        valid = [v for voices in ALL_VOICES.values() for v in voices]
        if args.voice not in valid:
            err = f"Unknown voice '{args.voice}'. Valid: {', '.join(valid)}"
            if args.json:
                print(json.dumps({"error": err}))
            else:
                print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)

    # Default emotion
    if not args.emotion:
        if args.model.endswith("-design"):
            args.emotion = args.text  # In design mode, emotion IS the voice description
        else:
            args.emotion = "Normal tone"

    result = generate(
        text=args.text,
        voice=args.voice,
        model_key=args.model,
        emotion=args.emotion,
        speed=args.speed,
        no_play=args.no_play,
        ref_audio=args.ref_audio,
        ref_text=args.ref_text,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Generated: {result['file']}")

    sys.exit(0 if "error" not in result else 1)


if __name__ == "__main__":
    main()
