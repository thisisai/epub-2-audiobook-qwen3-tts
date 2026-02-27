import os
import sys
import shutil
import time
import wave
import gc
import re
import subprocess
import warnings
from datetime import datetime

# Suppress harmless library warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
except ImportError:
    print("Error: 'mlx_audio' library not found.")
    print("Run: source .venv/bin/activate")
    sys.exit(1)

# Configuration
BASE_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
MODELS_DIR = os.path.join(os.getcwd(), "models")
VOICES_DIR = os.path.join(os.getcwd(), "voices")

# Settings
SAMPLE_RATE = 24000
FILENAME_MAX_LEN = 20

# Model Definitions
MODELS = {
    # Pro (1.7B)
    "1": {"name": "Custom Voice", "folder": "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "mode": "custom", "output_subfolder": "CustomVoice"},
    "2": {"name": "Voice Design", "folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit", "mode": "design", "output_subfolder": "VoiceDesign"},
    "3": {"name": "Voice Cloning", "folder": "Qwen3-TTS-12Hz-1.7B-Base-8bit", "mode": "clone_manager", "output_subfolder": "Clones"},
    # Lite (0.6B)
    "4": {"name": "Custom Voice", "folder": "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit", "mode": "custom", "output_subfolder": "CustomVoice"},
    "5": {"name": "Voice Design", "folder": "Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit", "mode": "design", "output_subfolder": "VoiceDesign"},
    "6": {"name": "Voice Cloning", "folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit", "mode": "clone_manager", "output_subfolder": "Clones"},
}

SPEAKER_MAP = {
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"]
}

EMOTION_EXAMPLES = [
    "悲傷哭泣，語速緩慢",
    "興奮開心，語速很快",
    "憤怒大聲喊叫",
    "輕聲細語耳語",
    "溫柔平靜，語速適中",
    "播報新聞的專業語調"
]


def ask_speed():
    """互動選擇語速，支援預設選項或直接輸入數字"""
    print("\n語速：")
    print("  1. 正常 (1.0x)")
    print("  2. 快速 (1.3x)")
    print("  3. 慢速 (0.8x)")
    print("  或直接輸入數字，例如：1.5、0.7（範圍 0.5～2.0）")
    sp = input("選擇：").strip() or "1"
    presets = {"1": 1.0, "2": 1.3, "3": 0.8}
    if sp in presets:
        return presets[sp]
    try:
        val = float(sp)
        if 0.5 <= val <= 2.0:
            return val
        print(f"超出範圍（0.5～2.0），使用預設 1.0x")
    except ValueError:
        print("輸入無效，使用預設 1.0x")
    return 1.0


def flush_input():
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    except (ImportError, OSError):
        pass


def clean_memory():
    gc.collect()


def make_temp_dir():
    return f"temp_{int(time.time())}"


def get_smart_path(folder_name):
    full_path = os.path.join(MODELS_DIR, folder_name)
    if not os.path.exists(full_path):
        return None

    snapshots_dir = os.path.join(full_path, "snapshots")
    if os.path.exists(snapshots_dir):
        subfolders = [f for f in os.listdir(snapshots_dir) if not f.startswith('.')]
        if subfolders:
            return os.path.join(snapshots_dir, subfolders[0])

    return full_path


def wav_to_mp3(wav_path, mp3_path, bitrate="192k"):
    """用 FFmpeg 將 WAV 轉為 MP3"""
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", wav_path,
           "-codec:a", "libmp3lame", "-b:a", bitrate, mp3_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def concat_wavs(wav_list, output_path):
    """用 FFmpeg 合併多個 WAV 檔案"""
    if len(wav_list) == 1:
        shutil.move(wav_list[0], output_path)
        return True

    # 建立 FFmpeg concat 清單
    list_file = output_path + ".list.txt"
    try:
        with open(list_file, "w") as f:
            for w in wav_list:
                f.write(f"file '{w}'\n")

        # 用 filter_complex 合併，重新編碼統一 sample rate，避免各段不一致導致合併失敗
        inputs = []
        for w in wav_list:
            inputs += ["-i", w]
        filter_str = "".join(f"[{i}:a]" for i in range(len(wav_list)))
        filter_str += f"concat=n={len(wav_list)}:v=0:a=1[out]"
        cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-ar", "24000", "-ac", "1",
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)


def split_text(text, max_chars=1000):
    """將長文切成適合 TTS 的段落（每段約 max_chars 字）

    策略：先把所有句子提取出來，再依序合併到接近 max_chars 為止。
    不管原文是一句一行還是整篇一段，都能正確處理。
    """
    # 1. 把整篇文字的句子都提取出來（按標點切分）
    #    先把多餘的空行/換行清掉，合成一串文字
    merged = " ".join(p.strip() for p in text.split("\n") if p.strip())

    # 2. 按句尾標點切成句子
    sentences = re.split(r'(?<=[。！？；.!?;])\s*', merged)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 3. 把短句子合併，直到接近 max_chars
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) <= max_chars:
            current += s
        else:
            if current:
                chunks.append(current)
            # 單句本身就超過 max_chars，按逗號再切
            if len(s) > max_chars:
                sub_parts = re.split(r'(?<=[，,、])\s*', s)
                sub_current = ""
                for sp in sub_parts:
                    sp = sp.strip()
                    if not sp:
                        continue
                    if len(sub_current) + len(sp) <= max_chars:
                        sub_current += sp
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = sp
                current = sub_current
            else:
                current = s
    if current:
        chunks.append(current)

    return chunks if chunks else [text]


def generate_long_audio(model, text, subfolder, text_label, gen_kwargs):
    """處理長文本：自動分段生成 → 合併 → 存成 MP3"""
    chunks = split_text(text)
    total_chunks = len(chunks)

    if total_chunks > 1:
        print(f"  文字較長，自動分為 {total_chunks} 段生成...")

    wav_parts = []
    temp_dirs = []

    try:
        for ci, chunk in enumerate(chunks):
            if total_chunks > 1:
                print(f"    段 {ci+1}/{total_chunks}（{len(chunk)} 字）...", end="", flush=True)

            temp_dir = make_temp_dir() + f"_{ci}"
            temp_dirs.append(temp_dir)

            generate_audio(model=model, text=chunk, output_path=temp_dir, **gen_kwargs)

            part_wav = os.path.join(temp_dir, "audio_000.wav")
            if os.path.exists(part_wav):
                wav_parts.append(part_wav)
                if total_chunks > 1:
                    print(" ✓")
            else:
                if total_chunks > 1:
                    print(" ✗（無輸出）")

        if not wav_parts:
            print("  錯誤：未產生任何音訊")
            return None

        # 合併 WAV
        save_path = os.path.join(BASE_OUTPUT_DIR, subfolder)
        os.makedirs(save_path, exist_ok=True)

        timestamp = datetime.now().strftime("%H-%M-%S")
        clean_text = re.sub(r'[^\w\s-]', '', text_label)[:FILENAME_MAX_LEN].strip().replace(' ', '_') or "audio"

        combined_wav = os.path.join(save_path, f"{timestamp}_{clean_text}_tmp.wav")

        if len(wav_parts) > 1:
            if not concat_wavs(wav_parts, combined_wav):
                # 合併失敗，只用第一段
                shutil.move(wav_parts[0], combined_wav)
        else:
            shutil.move(wav_parts[0], combined_wav)

        # WAV → MP3
        mp3_name = f"{timestamp}_{clean_text}.mp3"
        mp3_path = os.path.join(save_path, mp3_name)

        if wav_to_mp3(combined_wav, mp3_path):
            print(f"已儲存：outputs/{subfolder}/{mp3_name}")
        else:
            wav_name = f"{timestamp}_{clean_text}.wav"
            final_wav = os.path.join(save_path, wav_name)
            os.rename(combined_wav, final_wav)
            print(f"已儲存：outputs/{subfolder}/{wav_name}（MP3 轉換失敗）")
            return final_wav

        # 清理臨時 WAV
        if os.path.exists(combined_wav):
            os.remove(combined_wav)

        return mp3_path

    finally:
        for td in temp_dirs:
            if os.path.exists(td):
                shutil.rmtree(td, ignore_errors=True)


def save_audio_file(temp_folder, subfolder, text_snippet):
    save_path = os.path.join(BASE_OUTPUT_DIR, subfolder)
    os.makedirs(save_path, exist_ok=True)

    timestamp = datetime.now().strftime("%H-%M-%S")
    clean_text = re.sub(r'[^\w\s-]', '', text_snippet)[:FILENAME_MAX_LEN].strip().replace(' ', '_') or "audio"

    source_file = os.path.join(temp_folder, "audio_000.wav")

    if os.path.exists(source_file):
        mp3_name = f"{timestamp}_{clean_text}.mp3"
        mp3_path = os.path.join(save_path, mp3_name)

        if wav_to_mp3(source_file, mp3_path):
            print(f"已儲存：outputs/{subfolder}/{mp3_name}")
        else:
            # FFmpeg 失敗，保留 WAV
            wav_name = f"{timestamp}_{clean_text}.wav"
            wav_path = os.path.join(save_path, wav_name)
            shutil.move(source_file, wav_path)
            print(f"已儲存：outputs/{subfolder}/{wav_name}（MP3 轉換失敗）")

    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder, ignore_errors=True)


def clean_path(user_input):
    path = user_input.strip()
    if len(path) > 1 and path[0] in ["'", '"'] and path[-1] == path[0]:
        path = path[1:-1]
    return path.replace("\\ ", " ")


def get_safe_input(prompt="\n輸入文字（或拖入 .txt 檔案）："):
    try:
        raw_input = input(prompt).strip()
        if raw_input.lower() in ['exit', 'quit', 'q']:
            return None

        clean_p = clean_path(raw_input)
        if os.path.exists(clean_p) and clean_p.endswith(".txt"):
            print(f"讀取檔案：{os.path.basename(clean_p)}")
            try:
                with open(clean_p, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except IOError as e:
                print(f"讀取檔案錯誤：{e}")
                return None

        return raw_input
    except KeyboardInterrupt:
        flush_input()
        return None


def convert_audio_if_needed(input_path):
    if not os.path.exists(input_path):
        return None

    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".wav":
        try:
            with wave.open(input_path, 'rb') as f:
                if f.getnchannels() > 0:
                    return input_path
        except wave.Error:
            pass

    temp_wav = os.path.join(os.getcwd(), f"temp_convert_{int(time.time())}.wav")
    print(f"轉換 '{ext}' 為 WAV 格式中...")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", input_path, 
           "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", temp_wav]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return temp_wav
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("錯誤：無法轉換音檔，請確認 ffmpeg 已安裝。")
        return None


def get_saved_voices():
    if not os.path.exists(VOICES_DIR):
        return []
    voices = [f.replace(".wav", "") for f in os.listdir(VOICES_DIR) if f.endswith(".wav")]
    return sorted(voices)


def enroll_new_voice():
    print("\n--- 登錄新語音 ---")
    flush_input()

    name = input("1. 語音名稱（例如：老闆、媽媽）：").strip()
    if not name:
        return

    safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

    ref_input = input("2. 拖入參考音檔：").strip()
    raw_path = clean_path(ref_input)

    if len(raw_path) > 300 or "\n" in raw_path:
        print("錯誤：輸入過長。")
        flush_input()
        return

    clean_wav_path = convert_audio_if_needed(raw_path)
    if not clean_wav_path:
        return

    print("3. 逐字稿（影響品質，請務必填寫）：")
    ref_text = input("   請輸入音檔中說的完整內容：").strip()

    if not os.path.exists(VOICES_DIR):
        os.makedirs(VOICES_DIR)

    target_wav = os.path.join(VOICES_DIR, f"{safe_name}.wav")
    target_txt = os.path.join(VOICES_DIR, f"{safe_name}.txt")

    shutil.copy(clean_wav_path, target_wav)
    with open(target_txt, "w", encoding='utf-8') as f:
        f.write(ref_text)

    if clean_wav_path != raw_path and os.path.exists(clean_wav_path):
        os.remove(clean_wav_path)

    print(f"語音已儲存為 '{safe_name}'")


def run_custom_session(model_key):
    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("錯誤：找不到模型。")
        return

    print(f"\n載入 {info['name']} 中...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"載入失敗：{e}")
        return

    print(f"\n--- {info['name']} ---")
    speaker = "Vivian"

    print("\n可用語音：")
    idx = 1
    speaker_list = []
    for lang, names in SPEAKER_MAP.items():
        lang_zh = {"Chinese": "中文", "English": "英文", "Japanese": "日文", "Korean": "韓文"}.get(lang, lang)
        for n in names:
            print(f"  {idx}. {n}（{lang_zh}）")
            speaker_list.append(n)
            idx += 1

    user_choice = input("\n選擇語音（輸入編號或名稱）：").strip()
    if user_choice.isdigit():
        num = int(user_choice) - 1
        if 0 <= num < len(speaker_list):
            speaker = speaker_list[num]
    else:
        for lang, names in SPEAKER_MAP.items():
            if user_choice in names:
                speaker = user_choice
                break
    print(f"使用語音：{speaker}")

    print("\n情緒範例：")
    for ex in EMOTION_EXAMPLES:
        print(f"  - {ex}")
    base_instruct = input("情緒指令（直接按 Enter 為預設）：").strip() or "溫柔平靜，語速適中"

    speed = ask_speed()

    while True:
        text = get_safe_input()
        if text is None:
            break
        print("生成中...")
        try:
            generate_long_audio(
                model=model, text=text,
                subfolder=info["output_subfolder"], text_label=text,
                gen_kwargs={"voice": speaker, "instruct": base_instruct, "speed": speed, "lang_code": "chinese"},
            )
        except Exception as e:
            print(f"錯誤：{e}")
    clean_memory()


def run_design_session(model_key):
    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("錯誤：找不到模型。")
        return

    print(f"\n載入 {info['name']} 中...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"載入失敗：{e}")
        return

    print(f"\n--- {info['name']} ---")
    print("描述你想要的語音風格，例如：")
    print("  - 年輕女性，語調溫柔甜美")
    print("  - 中年男性，聲音低沉有磁性")
    print("  - 老年男性，語速緩慢，聲音沙啞")
    instruct = input("\n語音描述：").strip()
    if not instruct:
        return

    while True:
        text = get_safe_input()
        if text is None:
            break
        print("生成中...")
        try:
            generate_long_audio(
                model=model, text=text,
                subfolder=info["output_subfolder"], text_label=text,
                gen_kwargs={"instruct": instruct, "lang_code": "chinese"},
            )
        except Exception as e:
            print(f"錯誤：{e}")
    clean_memory()


def run_clone_manager(model_key):
    print("\n--- 語音複製管理 ---")
    print("  1. 選擇已儲存的語音")
    print("  2. 登錄新語音")
    print("  3. 快速複製")
    print("  4. 返回")

    sub_choice = input("\n選擇：").strip()
    if sub_choice == "2":
        enroll_new_voice()
        return
    if sub_choice == "4":
        return

    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("錯誤：找不到模型。")
        return

    print("\n載入基礎模型中...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"載入失敗：{e}")
        return

    ref_audio, ref_text = None, None

    if sub_choice == "1":
        saved = get_saved_voices()
        if not saved:
            print("尚無已儲存的語音。")
            return
        print("\n已儲存的語音：")
        for i, v in enumerate(saved):
            print(f"  {i+1}. {v}")
        try:
            idx = int(input("\n選擇編號：")) - 1
            if idx < 0 or idx >= len(saved):
                print("選擇無效。")
                return
            name = saved[idx]
            ref_audio = os.path.join(VOICES_DIR, f"{name}.wav")
            txt_path = os.path.join(VOICES_DIR, f"{name}.txt")
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    ref_text = f.read().strip()
            print(f"已載入：{name}")
        except (ValueError, IndexError):
            print("選擇無效。")
            return

    elif sub_choice == "3":
        ref_input = input("\n拖入參考音檔：").strip()
        raw_path = clean_path(ref_input)
        ref_audio = convert_audio_if_needed(raw_path)
        if not ref_audio:
            return
        ref_text = input("   音檔逐字稿（可選）：").strip() or "."

    else:
        return

    speed = ask_speed()

    while True:
        text = get_safe_input(f"\n輸入要用 '{os.path.basename(str(ref_audio))}' 語音說的文字（輸入 exit 離開）：")
        if text is None:
            break
        print("複製語音中...")
        try:
            generate_long_audio(
                model=model, text=text,
                subfolder=info["output_subfolder"], text_label=text,
                gen_kwargs={"ref_audio": ref_audio, "ref_text": ref_text, "speed": speed, "lang_code": "chinese"},
            )
        except Exception as e:
            print(f"錯誤：{e}")
    clean_memory()


def run_batch_session():
    """批次轉換：整個資料夾的 .txt 一鍵轉成 .mp3 語音"""
    print("\n" + "=" * 40)
    print(" 批次轉換模式（.txt → .mp3）")
    print("=" * 40)

    # 1. 選資料夾
    folder_input = input("\n拖入資料夾（或輸入路徑）：").strip()
    folder_path = clean_path(folder_input)

    if not os.path.isdir(folder_path):
        print(f"錯誤：找不到資料夾 '{folder_path}'")
        return

    txt_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".txt")])
    if not txt_files:
        print("資料夾中沒有 .txt 檔案。")
        return

    print(f"\n找到 {len(txt_files)} 個 .txt 檔案：")
    for i, f in enumerate(txt_files, 1):
        print(f"  {i}. {f}")

    # 2. 選模型
    print("\n選擇模型：")
    print("  1. Pro 自訂語音（1.7B，預設）")
    print("  2. Pro 語音設計（1.7B）")
    print("  3. Pro 語音複製（1.7B，使用自製聲音）")
    print("  4. Lite 自訂語音（0.6B，較快）")
    print("  5. Lite 語音設計（0.6B，較快）")
    print("  6. Lite 語音複製（0.6B，使用自製聲音）")
    model_choice = input("選擇（直接 Enter = 1）：").strip() or "1"

    if model_choice not in MODELS:
        print("選擇無效，使用 Pro 自訂語音。")
        model_choice = "1"

    info = MODELS[model_choice]
    is_custom = info["mode"] == "custom"
    is_clone = info["mode"] == "clone_manager"

    # 3. 選語音
    speaker = "Vivian"
    ref_audio = None
    ref_text = None

    if is_clone:
        saved = get_saved_voices()
        if not saved:
            print("尚無已儲存的自製語音。請先到主選單的語音複製功能登錄語音。")
            return
        print("\n已儲存的自製語音：")
        for i, v in enumerate(saved):
            print(f"  {i+1}. {v}")
        user_choice = input("\n選擇語音編號：").strip()
        try:
            idx = int(user_choice) - 1
            if idx < 0 or idx >= len(saved):
                print("選擇無效。")
                return
            name = saved[idx]
            ref_audio = os.path.join(VOICES_DIR, f"{name}.wav")
            txt_path = os.path.join(VOICES_DIR, f"{name}.txt")
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    ref_text = f.read().strip()
            else:
                ref_text = "."
            speaker = name
            print(f"已選擇：{name}")
        except (ValueError, IndexError):
            print("選擇無效。")
            return
    elif is_custom:
        print("\n可用語音：")
        idx = 1
        speaker_list = []
        for lang, names in SPEAKER_MAP.items():
            lang_zh = {"Chinese": "中文", "English": "英文", "Japanese": "日文", "Korean": "韓文"}.get(lang, lang)
            for n in names:
                print(f"  {idx}. {n}（{lang_zh}）")
                speaker_list.append(n)
                idx += 1
        user_choice = input("\n選擇語音（直接 Enter = Vivian）：").strip()
        if user_choice.isdigit():
            num = int(user_choice) - 1
            if 0 <= num < len(speaker_list):
                speaker = speaker_list[num]
        elif user_choice:
            for lang, names in SPEAKER_MAP.items():
                if user_choice in names:
                    speaker = user_choice
                    break

    # 4. 情緒
    instruct = None
    if is_clone:
        pass  # 語音複製不需要情緒指令
    elif is_custom:
        print("\n情緒範例：")
        for ex in EMOTION_EXAMPLES:
            print(f"  - {ex}")
        instruct = input("情緒指令（直接 Enter = 溫柔平靜）：").strip() or "溫柔平靜，語速適中"
    else:
        print("\n描述語音風格，例如：年輕女性，語調溫柔甜美")
        instruct = input("語音描述：").strip()
        if not instruct:
            print("語音設計模式需要描述，已取消。")
            return

    # 5. 語速
    speed = ask_speed()

    # 6. 確認
    print(f"\n{'=' * 40}")
    print(f"  檔案數：{len(txt_files)}")
    print(f"  模型  ：{info['name']}")
    if is_custom or is_clone:
        print(f"  語音  ：{speaker}")
    if instruct:
        print(f"  情緒  ：{instruct}")
    print(f"  語速  ：{speed}x")
    print(f"  輸出  ：.mp3（192kbps）")
    print(f"{'=' * 40}")

    confirm = input("\n開始批次轉換？(Y/n)：").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("已取消。")
        return

    # 7. 載入模型
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("錯誤：找不到模型。")
        return

    print(f"\n載入模型中...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"載入失敗：{e}")
        return

    # 8. 批次處理
    out_dir = os.path.join(BASE_OUTPUT_DIR, info["output_subfolder"])
    os.makedirs(out_dir, exist_ok=True)

    success = 0
    failed = 0
    total = len(txt_files)

    for i, txt_file in enumerate(txt_files, 1):
        txt_path = os.path.join(folder_path, txt_file)
        file_label = os.path.splitext(txt_file)[0]

        # 讀取文字
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
        except Exception as e:
            print(f"  [{i}/{total}] ✗ {txt_file}：讀取失敗 - {e}")
            failed += 1
            continue

        if not text:
            print(f"  [{i}/{total}] ✗ {txt_file}：內容為空")
            failed += 1
            continue

        print(f"  [{i}/{total}] {txt_file}（{len(text)} 字）")

        try:
            if is_clone:
                gen_kwargs = {"ref_audio": ref_audio, "ref_text": ref_text, "lang_code": "chinese"}
            elif is_custom:
                gen_kwargs = {"voice": speaker, "instruct": instruct, "speed": speed, "lang_code": "chinese"}
            else:
                gen_kwargs = {"instruct": instruct, "lang_code": "chinese"}

            # 使用分段生成（自動處理長文本）
            chunks = split_text(text)
            wav_parts = []
            temp_dirs = []

            if len(chunks) > 1:
                print(f"    自動分為 {len(chunks)} 段...")

            for ci, chunk in enumerate(chunks):
                if len(chunks) > 1:
                    print(f"    段 {ci+1}/{len(chunks)}（{len(chunk)} 字）...", end="", flush=True)

                temp_dir = make_temp_dir() + f"_b{i}_{ci}"
                temp_dirs.append(temp_dir)

                generate_audio(model=model, text=chunk, output_path=temp_dir, **gen_kwargs)

                part_wav = os.path.join(temp_dir, "audio_000.wav")
                if os.path.exists(part_wav):
                    wav_parts.append(part_wav)
                    if len(chunks) > 1:
                        print(" ✓")
                else:
                    if len(chunks) > 1:
                        print(" ✗")

            if not wav_parts:
                print(f"    ✗ 無輸出")
                failed += 1
                for td in temp_dirs:
                    if os.path.exists(td):
                        shutil.rmtree(td, ignore_errors=True)
                continue

            # 合併 WAV → MP3
            combined_wav = os.path.join(out_dir, f"{file_label}_tmp.wav")
            if len(wav_parts) > 1:
                concat_wavs(wav_parts, combined_wav)
            else:
                shutil.move(wav_parts[0], combined_wav)

            mp3_path = os.path.join(out_dir, f"{file_label}.mp3")
            if wav_to_mp3(combined_wav, mp3_path):
                print(f"    ✓ → {file_label}.mp3")
                success += 1
            else:
                os.rename(combined_wav, os.path.join(out_dir, f"{file_label}.wav"))
                print(f"    ⚠ MP3 轉換失敗，已存為 .wav")
                success += 1

            if os.path.exists(combined_wav):
                os.remove(combined_wav)

            for td in temp_dirs:
                if os.path.exists(td):
                    shutil.rmtree(td, ignore_errors=True)

        except Exception as e:
            print(f"    ✗ {e}")
            failed += 1

    # 9. 結果
    print(f"\n{'=' * 40}")
    print(f" 批次轉換完成！")
    print(f"  成功：{success}/{total}")
    if failed:
        print(f"  失敗：{failed}/{total}")
    print(f"  輸出：outputs/{info['output_subfolder']}/")
    print(f"{'=' * 40}")

    clean_memory()


def main_menu():
    print("\n" + "=" * 40)
    print(" Qwen3-TTS 語音合成管理器")
    print("=" * 40)

    print("\n  Pro 模型（1.7B - 最佳品質）")
    print("  ---------------------------------")
    print("  1. 自訂語音")
    print("  2. 語音設計")
    print("  3. 語音複製")

    print("\n  Lite 模型（0.6B - 較快速）")
    print("  ---------------------------")
    print("  4. 自訂語音")
    print("  5. 語音設計")
    print("  6. 語音複製")

    print("\n  7. 批次轉換（整個資料夾 .txt → .mp3）")

    print("\n  q. 離開")

    choice = input("\n選擇：").strip().lower()

    if choice == "q":
        sys.exit()

    if choice == "7":
        run_batch_session()
        return

    if choice not in MODELS:
        print("選擇無效。")
        flush_input()
        return

    mode = MODELS[choice]["mode"]

    if mode == "custom":
        run_custom_session(choice)
    elif mode == "design":
        run_design_session(choice)
    elif mode == "clone_manager":
        run_clone_manager(choice)


if __name__ == "__main__":
    try:
        os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
        while True:
            main_menu()
    except KeyboardInterrupt:
        print("\n離開中...")
