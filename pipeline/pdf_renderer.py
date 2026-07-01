"""PDF 渲染与扫描版判定（A2）"""
import json
from pathlib import Path

import fitz  # PyMuPDF

from pipeline.logger import logger

# 文本字符数低于此阈值视为扫描页
_SCANNED_CHAR_THRESHOLD = 50
# 超过此比例的页为扫描页则整本标为扫描版
_SCANNED_RATIO_THRESHOLD = 0.8


def render_pdf(pdf_path: str, out_dir: str, dpi: int = 300) -> dict:
    """
    渲染 PDF 为图片并判断扫描版。

    输出目录结构：
      {out_dir}/page_XXXX.png
      {out_dir}/render_meta.json

    Returns:
        render_meta dict（同写入文件的内容）
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = len(doc)
    logger.info(f"开始渲染 {pdf_path}，共 {total} 页", extra={"source_file": pdf_path, "stage": "render"})

    pages_meta = []
    scanned_count = 0
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    for i, page in enumerate(doc):
        img_path = out / f"page_{i+1:04d}.png"
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(str(img_path))

        text = page.get_text()
        char_count = len(text.strip())
        is_scanned = char_count < _SCANNED_CHAR_THRESHOLD
        if is_scanned:
            scanned_count += 1

        pages_meta.append({
            "page": i + 1,
            "image": str(img_path),
            "text": text,           # 文字版 PDF 直接保留文本层，供 split 直接使用
            "char_count": char_count,
            "is_scanned": is_scanned,
        })

    doc.close()

    scan_ratio = scanned_count / total if total else 0
    meta = {
        "source": pdf_path,
        "total_pages": total,
        "dpi": dpi,
        "is_scanned_pdf": scan_ratio > _SCANNED_RATIO_THRESHOLD,
        "scan_ratio": round(scan_ratio, 3),
        "pages": pages_meta,
    }

    meta_path = out / "render_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    logger.info(f"渲染完成，元数据写入 {meta_path}", extra={"stage": "render"})

    return meta
