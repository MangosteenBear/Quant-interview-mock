"""OCR 分流处理（A3-A4）

将渲染好的页面图片跑 PaddleOCR，产出与 render_meta.json 同结构的 ocr_meta.json。
split 步骤优先读 ocr_meta.json，自动兼容扫描版 PDF。

输入：render_meta.json（pages[].image 字段为 PNG 路径）
输出：ocr_meta.json（同结构，pages[].text 由 OCR 填充）

依赖（按需安装，避免影响文字版流水线）：
  pip install paddlepaddle paddleocr
"""
import json
from pathlib import Path
from typing import Any

from pipeline.logger import logger


def _load_ocr_engine():
    """延迟导入 PaddleOCR，避免文字版流水线强依赖。"""
    try:
        from paddleocr import PaddleOCR
    except ImportError as e:
        raise ImportError(
            "PaddleOCR 未安装，请执行：\n"
            "  pip install paddlepaddle paddleocr"
        ) from e

    return PaddleOCR(
        use_textline_orientation=True,
        lang="en",
    )


def _ocr_page(engine, image_path: str) -> str:
    """对单页图片跑 OCR，返回拼接文本。"""
    results = list(engine.predict(image_path))
    if not results:
        return ""

    lines = []
    for res in results:
        for block in res.get("rec_texts", []):
            if isinstance(block, str):
                lines.append(block)
    return "\n".join(lines)


def run_ocr(
    render_meta_path: str,
    out_dir: str | None = None,
) -> dict[str, Any]:
    """
    对扫描版 PDF 的所有页面跑 PaddleOCR。

    Args:
        render_meta_path: render_meta.json 路径
        out_dir: ocr_meta.json 输出目录（默认与 render_meta.json 同级）

    Returns:
        ocr_meta dict（同写入文件的内容）
    """
    meta_file = Path(render_meta_path)
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    if out_dir is None:
        out_dir = str(meta_file.parent)

    engine = _load_ocr_engine()
    logger.info("PaddleOCR 引擎已加载", extra={"stage": "ocr"})

    pages = meta.get("pages", [])
    total = len(pages)
    ocr_pages = []

    for i, page_info in enumerate(pages):
        img_path = page_info.get("image", "")
        page_num = page_info.get("page", i + 1)

        if not img_path or not Path(img_path).exists():
            logger.warning(f"页面图片不存在，跳过: {img_path}", extra={"stage": "ocr", "page": page_num})
            ocr_text = ""
        else:
            ocr_text = _ocr_page(engine, img_path)
            logger.info(
                f"OCR 完成 {page_num}/{total}  字符={len(ocr_text)}",
                extra={"stage": "ocr", "page": page_num},
            )

        ocr_pages.append({
            **page_info,
            "text": ocr_text,
            "char_count": len(ocr_text.strip()),
        })

    ocr_meta = {
        **meta,
        "ocr_engine": "paddleocr",
        "pages": ocr_pages,
    }

    out_path = Path(out_dir) / "ocr_meta.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ocr_meta, ensure_ascii=False, indent=2))
    logger.info(f"OCR 元数据写入 {out_path}", extra={"stage": "ocr"})

    return ocr_meta
