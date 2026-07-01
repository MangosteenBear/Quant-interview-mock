"""
量化面试题库 - PDF 数据处理流水线 CLI

影印 PDF → 结构化题库的完整流水线，分阶段执行：
  render  → PDF 渲染与扫描版判定
  ocr     → 版面分析 + 分流 OCR（文字/公式/表格）
  split   → 题目边界识别
  link    → 答案关联
  dedup   → 去重（SimHash + MinHash）
  ingest  → 入库

用法:
  python -m pipeline --help
  python -m pipeline render --pdf /path/to/book.pdf
  python -m pipeline run --pdf /path/to/book.pdf  # 跑完整流水线
"""
import json
from pathlib import Path

import click

from pipeline.answer_linker import link_answers
from pipeline.dedup import dedup_questions
from pipeline.ingest import ingest_questions
from pipeline.logger import logger
from pipeline.pdf_renderer import render_pdf
from pipeline.question_splitter import split_questions


@click.group()
@click.version_option(version="0.1.0", prog_name="量化题库流水线")
def cli():
    """量化面试题库 PDF 数据处理流水线"""
    pass


@cli.command()
@click.option("--pdf", required=True, type=click.Path(exists=True), help="PDF 文件路径")
@click.option("--dpi", default=300, help="渲染 DPI（默认 300）")
@click.option("--out", default="./output/pages", help="输出目录")
def render(pdf, dpi, out):
    """PDF 渲染与扫描版判定"""
    meta = render_pdf(pdf, out, dpi)
    total = meta["total_pages"]
    for p in meta["pages"]:
        click.echo(f"  页 {p['page']:4d}/{total}  {'[扫描]' if p['is_scanned'] else '[文字]'}  字符={p['char_count']}")
    click.echo(f"\n完成：{total} 页 → {out}")
    click.echo(f"扫描版比例：{meta['scan_ratio']:.1%}，整体判定：{'扫描版' if meta['is_scanned_pdf'] else '文字版'}")
    click.echo(f"元数据：{Path(out) / 'render_meta.json'}")


@cli.command()
@click.option("--pages-dir", required=True, type=click.Path(exists=True), help="渲染页面目录（含 render_meta.json）")
@click.option("--out", default=None, help="book_profile.json 输出路径（默认与 pages-dir 相同）")
def analyze(pages_dir, out):
    """书籍结构分析（OCR 前调用，输出 book_profile.json）"""
    from pipeline.book_analyzer import analyze_book
    ocr_meta = Path(pages_dir) / "ocr_meta.json"
    render_meta = Path(pages_dir) / "render_meta.json"
    if ocr_meta.exists():
        meta_file = str(ocr_meta)
    elif render_meta.exists():
        meta_file = str(render_meta)
    else:
        click.echo(f"错误：{pages_dir} 中未找到 render_meta.json 或 ocr_meta.json", err=True)
        raise SystemExit(1)
    out_path = out or str(Path(pages_dir) / "book_profile.json")
    profile = analyze_book(meta_file, out_path)
    click.echo(f"书籍格式：{profile['detected_format']}")
    click.echo(f"推荐解析器：--format {profile['recommended_splitter']}")
    if profile.get("page_ranges"):
        click.echo(f"页码范围：{profile['page_ranges']}")
    if profile.get("noise_sections"):
        click.echo(f"噪声段落：{list(profile['noise_sections'].keys())}")
    click.echo(f"估算题目数：~{profile['estimated_questions']}")
    click.echo(f"结果写入：{out_path}")


@cli.command()
@click.option("--pages-dir", required=True, type=click.Path(exists=True), help="渲染页面目录（含 render_meta.json）")
@click.option("--out", default=None, help="ocr_meta.json 输出目录（默认与 pages-dir 相同）")
def ocr(pages_dir, out):
    """扫描版 PDF OCR（PaddleOCR，产出 ocr_meta.json）"""
    from pipeline.ocr_dispatcher import run_ocr

    render_meta = Path(pages_dir) / "render_meta.json"
    if not render_meta.exists():
        click.echo(f"错误：{pages_dir} 中未找到 render_meta.json，请先执行 render 步骤", err=True)
        raise SystemExit(1)

    click.echo(f"开始 OCR：{pages_dir}")
    ocr_meta = run_ocr(str(render_meta), out_dir=out or pages_dir)
    total_chars = sum(p["char_count"] for p in ocr_meta["pages"])
    click.echo(f"OCR 完成：{ocr_meta['total_pages']} 页，总字符数 {total_chars} → {Path(out or pages_dir) / 'ocr_meta.json'}")


@cli.command()
@click.option("--ocr-dir", required=True, type=click.Path(exists=True), help="OCR 结果目录")
@click.option("--out", default="./output/questions.json", help="切分结果输出")
@click.option("--format", "fmt", default="auto",
              type=click.Choice(["auto", "wilmott-faq", "heard-crack", "primer"]),
              help="解析格式：auto=通用题号模式，wilmott-faq=FAQ Quant Interview 专用，heard-crack=Heard on the Street 专用")
def split(ocr_dir, out, fmt):
    """题目边界识别"""
    ocr_meta = Path(ocr_dir) / "ocr_meta.json"
    render_meta = Path(ocr_dir) / "render_meta.json"
    if ocr_meta.exists():
        meta_path = str(ocr_meta)
    elif render_meta.exists():
        meta_path = str(render_meta)
        click.echo("未找到 ocr_meta.json，使用 render_meta.json（文字版直通模式）")
    else:
        click.echo(f"错误：{ocr_dir} 中未找到 ocr_meta.json 或 render_meta.json", err=True)
        raise SystemExit(1)

    if fmt == "wilmott-faq":
        from pipeline.faq_wilmott_splitter import split_faq_wilmott
        questions = split_faq_wilmott(meta_path, out)
    elif fmt == "heard-crack":
        from pipeline.heard_crack_splitter import split_heard_crack
        questions = split_heard_crack(meta_path, out)
    elif fmt == "primer":
        from pipeline.quantitative_primer_splitter import split_quantitative_primer
        questions = split_quantitative_primer(meta_path, out)
    else:
        questions = split_questions(meta_path, out)
    click.echo(f"切题完成：{len(questions)} 道题 → {out}")


@cli.command()
@click.option("--questions", required=True, type=click.Path(exists=True), help="题目 JSON")
@click.option("--meta", required=True, type=click.Path(exists=True), help="render_meta.json 或 ocr_meta.json")
@click.option("--out", default="./output/questions_linked.json", help="输出路径")
def link(questions, meta, out):
    """答案关联（内嵌答案提取 + 集中答案区匹配）"""
    linked = link_answers(questions, meta, out)
    answered = sum(1 for q in linked if q.get("answer_text"))
    click.echo(f"答案关联完成：{len(linked)} 题，{answered} 题有答案 → {out}")


@cli.command()
@click.option("--questions", required=True, type=click.Path(exists=True), help="题目 JSON")
@click.option("--out", default="./output/questions_deduped.json", help="输出路径")
@click.option("--threshold", default=3, help="SimHash 汉明距离阈值（默认 3）")
def dedup(questions, out, threshold):
    """近重复检测（SimHash 64-bit）"""
    before = len(json.loads(Path(questions).read_text()))
    result = dedup_questions(questions, out, hamming_threshold=threshold)
    click.echo(f"去重完成：{before} → {len(result)} 题 → {out}")


@cli.command()
@click.option("--questions", required=True, type=click.Path(exists=True), help="题目 JSON")
@click.option("--db-url", default="sqlite:///./quantquiz.db", help="数据库 URL")
@click.option("--source-title", default=None, help="来源书名（默认取文件名）")
@click.option("--source-file", default=None, type=click.Path(), help="原始 PDF 路径（用于 file_hash）")
def ingest(questions, db_url, source_title, source_file):
    """入库（幂等写入，simhash 相同自动跳过）"""
    summary = ingest_questions(questions, db_url, source_title, source_file)
    click.echo(
        f"入库完成：新增 {summary['inserted']} 题，跳过 {summary['skipped']} 题"
        f"（source_id={summary['source_id']}）→ {db_url}"
    )


@cli.command()
@click.option("--pdf", required=True, type=click.Path(exists=True), help="PDF 文件路径")
@click.option("--out-dir", default="./output", help="中间产物根目录（默认 ./output）")
@click.option("--db-url", default="sqlite:///./quantquiz.db", help="数据库 URL")
@click.option("--dpi", default=300, help="渲染 DPI（默认 300）")
@click.option("--source-title", default=None, help="来源书名（默认取 PDF 文件名）")
@click.option("--hamming", default=3, help="SimHash 汉明距离阈值（默认 3）")
def run(pdf, out_dir, db_url, dpi, source_title, hamming):
    """完整流水线：render → split → link → dedup → ingest（文字版 PDF 直通）"""
    pdf_path = Path(pdf)
    base = Path(out_dir) / pdf_path.stem
    pages_dir = base / "pages"
    q_raw = base / "questions.json"
    q_linked = base / "questions_linked.json"
    q_deduped = base / "questions_deduped.json"

    def _step(name: str):
        click.echo(f"\n── {name} {'─' * (40 - len(name))}")

    # 1. render
    _step("render")
    meta = render_pdf(str(pdf_path), str(pages_dir), dpi)
    click.echo(f"   {meta['total_pages']} 页，{'扫描版' if meta['is_scanned_pdf'] else '文字版'} (scan_ratio={meta['scan_ratio']:.1%})")

    render_meta_path = str(pages_dir / "render_meta.json")

    if meta["is_scanned_pdf"]:
        # 扫描版：先 OCR，再对 ocr_meta 做结构分析
        _step("ocr")
        from pipeline.ocr_dispatcher import run_ocr
        run_ocr(render_meta_path, out_dir=str(pages_dir))
        meta_path = str(pages_dir / "ocr_meta.json")
        click.echo(f"   OCR 完成 → {meta_path}")
    else:
        meta_path = render_meta_path

    # analyze（结构分析，决定 splitter）
    _step("analyze")
    from pipeline.book_analyzer import analyze_book
    profile = analyze_book(meta_path)
    detected_fmt = profile["recommended_splitter"]
    click.echo(f"   格式={detected_fmt}，估算题数≈{profile['estimated_questions']}")
    if profile.get("noise_sections"):
        click.echo(f"   噪声段落：{list(profile['noise_sections'].keys())}")

    # 2. split（按 analyze 推荐格式）
    _step("split")
    if detected_fmt == "wilmott-faq":
        from pipeline.faq_wilmott_splitter import split_faq_wilmott
        questions = split_faq_wilmott(meta_path, str(q_raw))
    elif detected_fmt == "heard-crack":
        from pipeline.heard_crack_splitter import split_heard_crack
        questions = split_heard_crack(meta_path, str(q_raw))
    elif detected_fmt == "primer":
        from pipeline.quantitative_primer_splitter import split_quantitative_primer
        questions = split_quantitative_primer(meta_path, str(q_raw))
    else:
        questions = split_questions(meta_path, str(q_raw))
    click.echo(f"   {len(questions)} 道题")

    if not questions:
        click.echo("   [警告] 未检测到任何题目，流水线终止。", err=True)
        raise SystemExit(1)

    # 3. link
    _step("link")
    linked = link_answers(str(q_raw), meta_path, str(q_linked))
    answered = sum(1 for q in linked if q.get("answer_text"))
    click.echo(f"   {answered}/{len(linked)} 题有答案")

    # 4. dedup
    _step("dedup")
    deduped = dedup_questions(str(q_linked), str(q_deduped), hamming_threshold=hamming)
    click.echo(f"   {len(linked)} → {len(deduped)} 题（移除 {len(linked) - len(deduped)} 近重复）")

    # 5. ingest
    _step("ingest")
    title = source_title or pdf_path.stem
    summary = ingest_questions(str(q_deduped), db_url, source_title=title, source_file=str(pdf_path))
    click.echo(f"   新增 {summary['inserted']} 题，跳过 {summary['skipped']} 题")

    click.echo(f"\n完成 ✓  {len(deduped)} 题入库 → {db_url}")


if __name__ == "__main__":
    cli()
