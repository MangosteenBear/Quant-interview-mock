"""vision_lab CLI —— 实验性视觉入库流水线

复用主 pipeline 的 render / dedup / ingest；新增 vision_extract / window_merge；
入库写独立影子库（默认 output/vision_lab/quantquiz_vision.db），不碰主库。

用法:
  python -m pipeline.vision_lab run --book /path/to/book.pdf                # 全书
  python -m pipeline.vision_lab run --book /path/to/book.pdf --pages 1-20   # 小样验证
  python -m pipeline.vision_lab run --book /path/to/book.pdf --batch        # Batch API(-50%)

  # 也可分步执行：
  python -m pipeline.vision_lab extract --book book.pdf --out-dir output/vision_lab
  python -m pipeline.vision_lab merge   --raw <dir>/vision_raw.jsonl --out <dir>/vision_questions.json
"""
import json
from pathlib import Path

import click

from pipeline.dedup import dedup_questions
from pipeline.ingest import ingest_questions
from pipeline.pdf_renderer import render_pdf
from pipeline.vision_lab.vision_config import DEFAULT
from pipeline.vision_lab.vision_extractor import extract_pages
from pipeline.vision_lab.window_merger import merge_windows


def _parse_pages(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.update(range(int(a), int(b) + 1))
        elif part:
            pages.add(int(part))
    return pages


def _write_report(base: Path, deduped: list[dict], extract_summary: dict, ingest_summary: dict) -> Path:
    """生成 extraction_report.md：题数、置信度分布、成本、needs_review 清单。"""
    n = len(deduped)
    need = [q for q in deduped if q.get("needs_review")]
    confs = [q["confidence"] for q in deduped if isinstance(q.get("confidence"), (int, float))]
    buckets = {"≥0.9": 0, "0.7–0.9": 0, "0.5–0.7": 0, "<0.5": 0}
    for c in confs:
        if c >= 0.9:
            buckets["≥0.9"] += 1
        elif c >= 0.7:
            buckets["0.7–0.9"] += 1
        elif c >= 0.5:
            buckets["0.5–0.7"] += 1
        else:
            buckets["<0.5"] += 1
    answered = sum(1 for q in deduped if q.get("answer_text"))

    lines = [
        f"# 视觉抽取报告 · {base.name}",
        "",
        "## 概览",
        f"- 去重后题数: **{n}**（有答案 {answered}）",
        f"- 抽取窗口数: {extract_summary.get('n_windows', '-')}",
        f"- 估算成本: **${extract_summary.get('total_cost', 0):.2f}**",
        f"- 入库(影子库): 新增 {ingest_summary.get('inserted', 0)}，跳过 {ingest_summary.get('skipped', 0)}，"
        f"source_id={ingest_summary.get('source_id', '-')}",
        "",
        "## 置信度分布",
        *[f"- {k}: {v}" for k, v in buckets.items()],
        "",
        f"## 需人工复核（needs_review = true，共 {len(need)}）",
    ]
    if need:
        for q in need[:200]:
            marker = q.get("question_marker", "")
            pages = q.get("source_pages", [])
            note = q.get("notes", "")
            preview = (q.get("raw_text", "")[:60] or "").replace("\n", " ")
            lines.append(f"- `{q['id']}` p{pages} [{marker}] {preview}…  {('— ' + note) if note else ''}")
    else:
        lines.append("- （无）")
    lines.append("")

    path = base / "extraction_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


@click.group()
@click.version_option(version="0.1.0", prog_name="vision_lab")
def cli():
    """vision_lab —— 实验性视觉入库流水线（与主 pipeline 隔离）"""
    pass


@cli.command()
@click.option("--book", required=True, type=click.Path(exists=True), help="PDF 文件路径")
@click.option("--out-dir", default="./output/vision_lab", help="产物根目录")
@click.option("--pages", default=None, help="页码范围，如 1-20 或 1-20,25（默认全书）")
@click.option("--batch/--no-batch", default=None, help="是否走 Batch API(-50%)，默认取配置")
@click.option("--dpi", default=None, type=int, help="渲染 DPI（默认取配置）")
@click.option("--db-url", default=None, help="入库数据库 URL（默认影子库）")
@click.option("--source-title", default=None, help="来源书名（默认取 PDF 文件名，加 [vision] 后缀）")
def run(book, out_dir, pages, batch, dpi, db_url, source_title):
    """完整流水线：render → vision_extract → window_merge → dedup → ingest(影子库) → report"""
    cfg = DEFAULT
    if batch is not None:
        cfg.use_batch = batch
    if dpi is not None:
        cfg.render_dpi = dpi
    db_url = db_url or cfg.shadow_db_url

    pdf = Path(book)
    base = Path(out_dir) / pdf.stem
    pages_dir = base / "pages"
    page_range = _parse_pages(pages)

    def _step(name):
        click.echo(f"\n── {name} {'─' * (36 - len(name))}")

    # 1. render（复用）
    _step("render")
    meta = render_pdf(str(pdf), str(pages_dir), cfg.render_dpi)
    click.echo(f"   {meta['total_pages']} 页 @ {cfg.render_dpi}DPI，"
               f"{'扫描版' if meta['is_scanned_pdf'] else '文字版'}")

    # 2. vision_extract（新增）
    _step("vision_extract")
    ex = extract_pages(str(pages_dir / "render_meta.json"), str(base), cfg, page_range)
    click.echo(f"   {ex['n_windows']} 窗，估算成本 ${ex['total_cost']:.2f}")

    # 3. window_merge（新增）
    _step("window_merge")
    q_merged = base / "vision_questions.json"
    merged = merge_windows(str(base / "vision_raw.jsonl"), str(q_merged), cfg)
    click.echo(f"   合并后 {len(merged)} 题 → {q_merged}")
    if not merged:
        click.echo("   [警告] 未抽到任何题目，终止。", err=True)
        raise SystemExit(1)

    # 4. dedup（复用）
    _step("dedup")
    q_deduped = base / "vision_deduped.json"
    deduped = dedup_questions(str(q_merged), str(q_deduped))
    click.echo(f"   {len(merged)} → {len(deduped)} 题")

    # 5. ingest（复用 → 影子库）
    _step("ingest → 影子库")
    if db_url.startswith("sqlite"):
        # 确保 sqlite 文件目录存在
        db_file = db_url.split(":///", 1)[-1]
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    title = source_title or f"{pdf.stem} [vision]"
    summary = ingest_questions(str(q_deduped), db_url, source_title=title, source_file=str(pdf))
    click.echo(f"   新增 {summary['inserted']}，跳过 {summary['skipped']}（source_id={summary['source_id']}）→ {db_url}")

    # 6. report
    _step("report")
    rpt = _write_report(base, deduped, ex, summary)
    click.echo(f"   报告 → {rpt}")

    click.echo(f"\n完成 ✓  {len(deduped)} 题入影子库。下一步：跑 quant-qa-reviewer 质检 {q_deduped}")


@cli.command()
@click.option("--book", required=True, type=click.Path(exists=True), help="PDF 文件路径")
@click.option("--out-dir", default="./output/vision_lab", help="产物根目录")
@click.option("--pages", default=None, help="页码范围，如 1-20（默认全书）")
@click.option("--batch/--no-batch", default=None, help="是否走 Batch API")
@click.option("--dpi", default=None, type=int, help="渲染 DPI")
def extract(book, out_dir, pages, batch, dpi):
    """仅 render + 视觉抽取（产出 vision_raw.jsonl，用于调试/复跑）"""
    cfg = DEFAULT
    if batch is not None:
        cfg.use_batch = batch
    if dpi is not None:
        cfg.render_dpi = dpi
    pdf = Path(book)
    base = Path(out_dir) / pdf.stem
    pages_dir = base / "pages"
    render_pdf(str(pdf), str(pages_dir), cfg.render_dpi)
    ex = extract_pages(str(pages_dir / "render_meta.json"), str(base), cfg, _parse_pages(pages))
    click.echo(f"抽取完成：{ex['n_windows']} 窗，${ex['total_cost']:.2f} → {base / 'vision_raw.jsonl'}")


@cli.command()
@click.option("--raw", required=True, type=click.Path(exists=True), help="vision_raw.jsonl 路径")
@click.option("--out", required=True, help="vision_questions.json 输出路径")
def merge(raw, out):
    """仅跨页合并（vision_raw.jsonl → questions_linked 兼容 JSON）"""
    merged = merge_windows(raw, out, DEFAULT)
    click.echo(f"合并完成：{len(merged)} 题 → {out}")


if __name__ == "__main__":
    cli()
