"""视觉抽取（vision_lab 核心新增）

页面图 → 结构化题目 JSON。滑动窗口把连续若干页整页图喂给 Claude 视觉模型，
用结构化输出（output_config.format）逐窗抽取题目 + 答案 + LaTeX。

- 复用主 pipeline 的 render 产物（render_meta.json）
- anthropic SDK 延迟导入：本文件可被 import 而不要求已安装 anthropic
- 每窗原始响应落盘 vision_raw.jsonl，可追溯 / 复跑
"""
import base64
import io
import json
from pathlib import Path
from typing import Any

from pipeline.logger import logger
from pipeline.vision_lab.vision_config import DEFAULT, VisionConfig

# 结构化输出 JSON schema（结构化输出限制：additionalProperties 必须为 false，
# 不支持数值/字符串长度约束，故 confidence 只声明为 number）
_QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "marker": {"type": "string"},
                    "stem_markdown": {"type": "string"},
                    "stem_latex": {"type": "string"},
                    "answer_markdown": {"type": "string"},
                    "book_page_start": {"type": "integer"},
                    "book_page_end": {"type": "integer"},
                    "confidence": {"type": "number"},
                    "needs_review": {"type": "boolean"},
                    "notes": {"type": "string"},
                },
                "required": [
                    "marker", "stem_markdown", "stem_latex", "answer_markdown",
                    "book_page_start", "book_page_end", "confidence",
                    "needs_review", "notes",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}

_PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_prompt.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _encode_image(path: str, max_long_edge: int) -> str:
    """读取 PNG 并按需降采样，返回 base64（无换行）。缺 Pillow 时发原图。"""
    data = Path(path).read_bytes()
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        long_edge = max(w, h)
        if max_long_edge and long_edge > max_long_edge:
            scale = max_long_edge / long_edge
            img = img.convert("RGB").resize((int(w * scale), int(h * scale)))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()
    except ImportError:
        pass  # 未装 Pillow：直接发原图
    return base64.standard_b64encode(data).decode("ascii")


def _windows(pages: list[dict], size: int, overlap: int) -> list[list[dict]]:
    """把页面列表切成重叠滑窗。step = size - overlap。"""
    step = max(1, size - overlap)
    out = []
    i = 0
    n = len(pages)
    while i < n:
        out.append(pages[i:i + size])
        if i + size >= n:
            break
        i += step
    return out


def _build_content(window: list[dict], cfg: VisionConfig) -> list[dict]:
    """构造单窗 user content：逐页 [标注文本 + 图片]，末尾附抽取指令。"""
    content: list[dict] = []
    page_nos = [p["page"] for p in window]
    for p in window:
        content.append({"type": "text", "text": f"【第 {p['page']} 页】"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": _encode_image(p["image"], cfg.max_image_long_edge),
            },
        })
    content.append({
        "type": "text",
        "text": (
            f"以上依次是第 {page_nos[0]}–{page_nos[-1]} 页。"
            f"请抽取其中所有面试题目，按 schema 输出 {{\"questions\": [...]}}。"
            f"book_page_start / book_page_end 用上面标注的页码。"
        ),
    })
    return content


def _estimate_cost(usage: dict, cfg: VisionConfig, batch: bool) -> float:
    """按 usage 估算单次成本（USD）。usage 键使用下划线命名。"""
    m = cfg.batch_mult if batch else 1.0
    in_tok = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)
    c_read = usage.get("cache_read_input_tokens", 0)
    c_write = usage.get("cache_creation_input_tokens", 0)
    cost = (
        in_tok * cfg.price_in
        + c_read * cfg.price_in * cfg.cache_read_mult
        + c_write * cfg.price_in * cfg.cache_write_mult
        + out_tok * cfg.price_out
    ) / 1_000_000
    return cost * m


def _usage_dict(usage: Any) -> dict:
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }


def _parse_questions(message: Any) -> list[dict]:
    """从结构化输出响应里取第一个 text block 的 JSON。"""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            data = json.loads(block.text)
            return data.get("questions", [])
    return []


def extract_pages(
    render_meta_path: str,
    out_dir: str,
    cfg: VisionConfig = DEFAULT,
    page_range: set[int] | None = None,
) -> dict[str, Any]:
    """
    对 render 产出的页面做视觉抽取。

    Args:
        render_meta_path: render_meta.json 路径
        out_dir:          产物目录（写 vision_raw.jsonl）
        cfg:              VisionConfig
        page_range:       只处理这些页码（1-based）；None = 全书

    Returns:
        {"windows": [...], "total_cost": float, "n_windows": int}
        每个 window: {"pages": [...], "questions": [...], "usage": {...}, "cost": float}
    """
    import anthropic  # 延迟导入

    meta = json.loads(Path(render_meta_path).read_text(encoding="utf-8"))
    pages = meta["pages"]
    if page_range is not None:
        pages = [p for p in pages if p["page"] in page_range]
    if not pages:
        raise ValueError("没有符合 page_range 的页面")

    wins = _windows(pages, cfg.window_size, cfg.window_overlap)
    logger.info(
        f"视觉抽取开始：{len(pages)} 页 → {len(wins)} 窗（size={cfg.window_size}, overlap={cfg.window_overlap}）"
        f"，model={cfg.model}, batch={cfg.use_batch}",
        extra={"stage": "vision_extract"},
    )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "vision_raw.jsonl"
    raw_path.write_text("", encoding="utf-8")  # 截断，供增量追加（崩溃不丢已付费结果）
    system = [{"type": "text", "text": _load_prompt(), "cache_control": {"type": "ephemeral"}}]

    client = anthropic.Anthropic()
    if cfg.use_batch:
        results = _run_batch(client, wins, system, cfg, str(raw_path))
    else:
        results = _run_sync(client, wins, system, cfg, str(raw_path))

    total_cost = sum(r["cost"] for r in results)
    n_err = sum(1 for r in results if r.get("error"))
    n_q = sum(len(r["questions"]) for r in results)
    if n_err:
        logger.warning(f"{n_err} 个窗口失败（内容过滤/限流等），已跳过，见 vision_raw.jsonl 的 error 字段",
                       extra={"stage": "vision_extract"})
    logger.info(
        f"视觉抽取完成：{n_q} 道原始题（未合并），估算成本 ${total_cost:.2f} → {raw_path}",
        extra={"stage": "vision_extract"},
    )
    return {"windows": results, "total_cost": total_cost, "n_windows": len(wins)}


def _append_jsonl(path: str, obj: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _request_params(win, system, cfg: VisionConfig) -> dict:
    """单窗请求参数（sync 与 batch 共用，保证两条路径一致）。"""
    return dict(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        system=system,
        thinking={"type": "adaptive"} if cfg.use_thinking else {"type": "disabled"},
        output_config={"effort": cfg.effort,
                       "format": {"type": "json_schema", "schema": _QUESTION_SCHEMA}},
        messages=[{"role": "user", "content": _build_content(win, cfg)}],
    )


def _create_with_retry(client, win, system, cfg: VisionConfig):
    """单窗调用；对限流/服务端错误重试一次，内容过滤(400)等直接抛出。"""
    import time
    import anthropic
    for attempt in range(2):
        try:
            return client.messages.create(**_request_params(win, system, cfg))
        except anthropic.APIStatusError as e:
            if attempt == 0 and getattr(e, "status_code", None) in (429, 500, 529):
                time.sleep(5)
                continue
            raise


def _run_sync(client, wins, system, cfg: VisionConfig, raw_path: str) -> list[dict]:
    """逐窗同步抽取。单窗失败(内容过滤/限流等)不中断整体，记 error 后继续。"""
    results = []
    cumulative = 0.0
    for idx, win in enumerate(wins):
        page_nos = [p["page"] for p in win]
        try:
            msg = _create_with_retry(client, win, system, cfg)
        except Exception as e:  # noqa: BLE001 —— 实验模块容错优先
            r = {"pages": page_nos, "questions": [], "usage": {}, "cost": 0.0,
                 "error": type(e).__name__ + ": " + str(e)[:160]}
            results.append(r)
            _append_jsonl(raw_path, r)
            logger.warning(f"窗 {idx+1}/{len(wins)} 页{page_nos} 失败并跳过：{r['error']}",
                           extra={"stage": "vision_extract", "page": page_nos[0]})
            continue
        usage = _usage_dict(msg.usage)
        cost = _estimate_cost(usage, cfg, batch=False)
        cumulative += cost
        questions = _parse_questions(msg)
        r = {"pages": page_nos, "questions": questions, "usage": usage, "cost": cost}
        results.append(r)
        _append_jsonl(raw_path, r)
        logger.info(
            f"窗 {idx+1}/{len(wins)} 页{page_nos}：{len(questions)} 题，${cost:.3f}（累计 ${cumulative:.2f}）",
            extra={"stage": "vision_extract", "page": page_nos[0]},
        )
        if cumulative > cfg.max_cost_usd:
            logger.warning(
                f"累计成本 ${cumulative:.2f} 超过上限 ${cfg.max_cost_usd}，提前终止（已处理 {idx+1}/{len(wins)} 窗）",
                extra={"stage": "vision_extract"},
            )
            break
    return results


def _run_batch(client, wins, system, cfg: VisionConfig, raw_path: str) -> list[dict]:
    """Batch API：整批提交后轮询。-50% 成本，适合全书。"""
    import time
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    win_by_id = {f"win_{i:04d}": win for i, win in enumerate(wins)}
    requests = [
        Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**_request_params(win, system, cfg)))
        for cid, win in win_by_id.items()
    ]
    batch = client.messages.batches.create(requests=requests)
    logger.info(f"Batch 已提交 id={batch.id}，{len(requests)} 窗，轮询中…", extra={"stage": "vision_extract"})
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        time.sleep(30)

    # Batch 结果顺序不保证，按 custom_id 归位
    by_cid: dict[str, dict] = {}
    for res in client.messages.batches.results(batch.id):
        win = win_by_id.get(res.custom_id, [])
        page_nos = [p["page"] for p in win]
        if res.result.type != "succeeded":
            logger.warning(f"{res.custom_id} 失败: {res.result.type}", extra={"stage": "vision_extract"})
            by_cid[res.custom_id] = {"pages": page_nos, "questions": [], "usage": {},
                                     "cost": 0.0, "error": res.result.type}
            continue
        msg = res.result.message
        usage = _usage_dict(msg.usage)
        by_cid[res.custom_id] = {"pages": page_nos, "questions": _parse_questions(msg),
                                 "usage": usage, "cost": _estimate_cost(usage, cfg, batch=True)}
    ordered = [by_cid[cid] for cid in win_by_id if cid in by_cid]
    for r in ordered:
        _append_jsonl(raw_path, r)
    return ordered
