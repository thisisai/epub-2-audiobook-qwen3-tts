"""
EPUB 轉章節工具。
直接解析 EPUB（zip）結構，按內部 HTML 文件分章，
過濾掉封面、版權頁、目錄等非正文內容，
輸出乾淨的章節 .txt 檔供 TTS 批次轉換使用。

用法：
  python3 epub_to_chapters.py <epub檔案> [--output-dir chapters]
  python3 epub_to_chapters.py book.epub --output-dir my_chapters
  python3 epub_to_chapters.py book.epub --keep-all  # 不過濾，全部匯出

安裝依賴：
  pip install beautifulsoup4 lxml
"""

import argparse
import os
import re
import zipfile
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


# 要過濾掉的章節（標題符合即跳過）
SKIP_TITLE_PATTERNS = [
    r"^cover$",
    r"^封面$",
    r"^目錄$",
    r"^table\s*of\s*contents$",
    r"^toc$",
    r"^版權",
    r"^copyright",
    r"^colophon$",
    r"^title\s*page$",
    r"^書名頁$",
    r"^扉頁$",
    r"^also\s*by",
    r"^dedication$",
    r"^獻詞$",
]

# 結束標記：遇到這些標題後的章節全部不納入
END_TITLE_PATTERNS = [
    r"^致謝",
    r"^後記",
    r"^附錄",
    r"^參考文獻",
    r"^注釋",
    r"^acknowledgement",
    r"^appendix",
    r"^bibliography",
    r"^references$",
    r"^index$",
]


# ── 工具函式 ──────────────────────────────────────

def should_skip(title):
    """判斷此章節標題是否應該跳過。"""
    t = title.strip().lower()
    for pattern in SKIP_TITLE_PATTERNS:
        if re.match(pattern, t, re.IGNORECASE):
            return True
    return False


def is_end_marker(title):
    """判斷此章節標題是否為結束標記。"""
    t = title.strip().lower()
    for pattern in END_TITLE_PATTERNS:
        if re.match(pattern, t, re.IGNORECASE):
            return True
    return False


def is_too_short(content, min_chars=50):
    """內容太短的章節（封面、空白頁等）直接跳過。"""
    return len(content.strip()) < min_chars


def clean_chapter_text(content):
    """清理章節文字：移除多餘空行、前導空白。"""
    lines = []
    blank_count = 0
    for line in content.split("\n"):
        cleaned = line.strip()
        if cleaned == "":
            blank_count += 1
            if blank_count <= 1:
                lines.append("")
        else:
            blank_count = 0
            lines.append(cleaned)
    return "\n".join(lines).strip()


def safe_filename(name, max_len=80):
    """產生安全的檔名。"""
    safe = re.sub(r'[/\\:*?"<>|：]', '_', name)
    safe = re.sub(r'_+', '_', safe).strip('_')
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe


# ── EPUB 解析（純 zipfile + BeautifulSoup，不依賴 ebooklib）──

def _strip_ns(tag):
    """移除 XML namespace prefix。"""
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_opf(zf):
    """從 EPUB 的 OPF 檔案中取得 metadata 和 spine 順序的 HTML 檔案列表。"""
    # 1. 從 META-INF/container.xml 找 OPF 路徑
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    opf_path = None
    for elem in container.iter():
        if _strip_ns(elem.tag) == "rootfile":
            opf_path = elem.get("full-path")
            break
    if not opf_path:
        raise ValueError("找不到 OPF 檔案")

    opf_dir = os.path.dirname(opf_path)

    # 2. 解析 OPF
    opf = ET.fromstring(zf.read(opf_path))

    # metadata
    meta = {"title": "Unknown", "author": "Unknown"}
    for elem in opf.iter():
        local = _strip_ns(elem.tag)
        if local == "title" and elem.text:
            meta["title"] = elem.text.strip()
        elif local == "creator" and elem.text:
            meta["author"] = elem.text.strip()

    # manifest: id → href
    manifest = {}
    for elem in opf.iter():
        if _strip_ns(elem.tag) == "item":
            item_id = elem.get("id")
            href = elem.get("href")
            media_type = elem.get("media-type", "")
            if item_id and href:
                manifest[item_id] = {
                    "href": href,
                    "media_type": media_type,
                }

    # spine: 按閱讀順序排列的 itemref
    spine_ids = []
    for elem in opf.iter():
        if _strip_ns(elem.tag) == "itemref":
            idref = elem.get("idref")
            if idref:
                spine_ids.append(idref)

    # 組合：按 spine 順序，只取 HTML 類型
    html_files = []
    for sid in spine_ids:
        item = manifest.get(sid)
        if not item:
            continue
        mt = item["media_type"]
        if "html" in mt or "xhtml" in mt or "xml" in mt:
            href = item["href"]
            # href 是相對 OPF 的路徑
            full_path = os.path.normpath(os.path.join(opf_dir, href))
            # zip 路徑不會有 leading ./
            full_path = full_path.replace("\\", "/")
            html_files.append(full_path)

    return meta, html_files


def _extract_title_from_soup(soup, filename, chapter_num):
    """從 HTML 內容或檔名中提取章節標題。"""
    for tag in ["h1", "h2", "h3", "title"]:
        elem = soup.find(tag)
        if elem and elem.get_text().strip():
            return elem.get_text().strip()

    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub(r"^chapter[-_]?\d*[-_]?", "", base, flags=re.IGNORECASE)
    base = base.replace("_", " ").replace("-", " ").strip()
    if base and base.lower() not in ["index", "cover", "toc", "contents"]:
        return base

    return f"Chapter {chapter_num}"


def _extract_text_from_soup(soup):
    """從 BeautifulSoup 物件中提取純文字。"""
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def read_epub(epub_path):
    """讀取 EPUB，回傳 (metadata, chapters_list)。

    chapters_list 中每個元素為 {"title": ..., "content": ..., "chapter_num": ...}
    """
    with zipfile.ZipFile(epub_path, "r") as zf:
        meta, html_files = _parse_opf(zf)

        chapters = []
        chapter_num = 1
        for html_path in html_files:
            try:
                raw = zf.read(html_path)
            except KeyError:
                continue

            soup = BeautifulSoup(raw, "html.parser")
            title = _extract_title_from_soup(soup, html_path, chapter_num)
            content = _extract_text_from_soup(soup)

            if content.strip():
                chapters.append({
                    "title": title,
                    "content": content,
                    "chapter_num": chapter_num,
                })
                chapter_num += 1

    return meta, chapters


# ── 主流程 ────────────────────────────────────────

def epub_to_chapters(epub_path, output_dir, keep_all=False, skip_end=True):
    """EPUB → 過濾 → 章節 txt 檔。"""
    if not os.path.exists(epub_path):
        print(f"錯誤：找不到檔案 '{epub_path}'")
        return []

    print(f"讀取 EPUB：{epub_path}")
    try:
        meta, chapters = read_epub(epub_path)
    except Exception as e:
        print(f"錯誤：無法讀取 EPUB - {e}")
        return []

    print(f"書名：{meta['title']}")
    print(f"作者：{meta['author']}")
    print(f"原始章節數：{len(chapters)}")

    os.makedirs(output_dir, exist_ok=True)
    saved_files = []
    chapter_idx = 1

    print(f"\n{'─' * 50}")
    print(f"{'過濾' if not keep_all else '匯出'}章節中...\n")

    for ch in chapters:
        title = ch["title"]
        content = ch["content"]

        if not keep_all:
            if should_skip(title):
                print(f"  跳過（非正文）：{title}")
                continue

            if is_end_marker(title) and skip_end:
                print(f"  截斷（結束標記）：{title}")
                print(f"  後續章節不再納入。")
                break

            if is_too_short(content):
                print(f"  跳過（內容過短）：{title}（{len(content.strip())} 字）")
                continue

        cleaned = clean_chapter_text(content)
        if not cleaned:
            continue

        safe_title = safe_filename(title)
        filename = f"{chapter_idx:02d}_{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cleaned)

        char_count = len(cleaned)
        print(f"  ✓ {filename}（{char_count} 字）")
        saved_files.append(filepath)
        chapter_idx += 1

    print(f"\n{'─' * 50}")
    print(f"共產生 {len(saved_files)} 個章節檔案 → {output_dir}/")

    if saved_files:
        print(f"\n下一步：用 main.py 批次模式將章節轉為語音")
        print(f"  source venv/bin/activate")
        print(f"  python main.py")
        print(f"  → 選擇 7（批次轉換）→ 拖入 {output_dir} 資料夾")

    return saved_files


def main():
    parser = argparse.ArgumentParser(
        description="EPUB 轉章節文字檔（供 TTS 批次轉換使用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python3 epub_to_chapters.py book.epub
  python3 epub_to_chapters.py book.epub --output-dir my_chapters
  python3 epub_to_chapters.py book.epub --keep-all
""",
    )
    parser.add_argument("epub", help="EPUB 檔案路徑")
    parser.add_argument(
        "--output-dir", default="chapters",
        help="輸出目錄（預設：chapters）",
    )
    parser.add_argument(
        "--keep-all", action="store_true",
        help="不過濾，匯出所有章節（包含封面、版權、致謝等）",
    )
    parser.add_argument(
        "--no-skip-end", action="store_true",
        help="不在致謝/附錄處截斷，繼續匯出後續章節",
    )
    args = parser.parse_args()

    epub_to_chapters(
        epub_path=args.epub,
        output_dir=args.output_dir,
        keep_all=args.keep_all,
        skip_end=not args.no_skip_end,
    )


if __name__ == "__main__":
    main()
