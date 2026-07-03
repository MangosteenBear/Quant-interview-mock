"""vision_lab 配置

所有可调参数集中于此，避免散落在各模块。
"""
from dataclasses import dataclass, field


@dataclass
class VisionConfig:
    # --- 模型（默认=省钱档；A/B 实测见 README）---
    # 省钱档 Sonnet4.6 + 无thinking + effort low + 图1500px：$0.32/20页，质量与 Opus 档持平
    # 密集数学/手写严重的书可临时切回 model="claude-opus-4-8" + use_thinking=True + effort="high"
    model: str = "claude-sonnet-4-6"    # 省钱档；Opus 档为 "claude-opus-4-8"
    use_thinking: bool = False          # 抽取不需深推理；关掉省一大半输出 token，且更不易触发内容过滤
    effort: str = "low"                 # output_config.effort（low/medium/high[/xhigh/max]）
    max_tokens: int = 8000              # 单窗口结构化输出上限（约 10~15 题）

    # --- 渲染 ---
    render_dpi: int = 200               # 视觉够用且省 token；密集小字扫描件可调到 300

    # --- 滑动窗口 ---
    # window_size 5 (overlap 1)：质检发现主流问题是超长解答跨过 3 页窗口被截断（DBID 35 等）。
    # 5 页窗口能装下更长解答，减少截断；且步长 4 比 size3/step2 窗口更少、redundancy 更低，反而略省。
    window_size: int = 5                # 每次送入模型的页数（3→5，降跨页截断，见 CHANGELOG v1.6）
    window_overlap: int = 1             # 相邻窗口重叠页数（保证跨页题被完整看到）

    # --- 图像 ---
    max_image_long_edge: int = 1500     # 发送前长边上限（需 Pillow；缺失则发原图）

    # --- 成本控制 ---
    use_batch: bool = False             # True 走 Batch API（-50%，异步轮询）
    max_cost_usd: float = 20.0          # 单本累计估算成本上限，超限告警/终止

    # --- 合并 ---
    merge_sim_threshold: float = 0.6    # 相邻窗口题目 token Jaccard，超过视为重叠重复

    # --- 影子库（与主库 quantquiz.db 隔离）---
    shadow_db_url: str = "sqlite:///./output/vision_lab/quantquiz_vision.db"

    # --- 定价（USD / 1M tokens，用于估算，非计费）---
    # 默认 sonnet-4-6: 输入 $3 / 输出 $15；换 opus-4-8 时改成 5 / 25。缓存读 ~0.1x，写 ~1.25x；Batch 0.5x
    price_in: float = 3.0
    price_out: float = 15.0
    cache_read_mult: float = 0.1
    cache_write_mult: float = 1.25
    batch_mult: float = 0.5


DEFAULT = VisionConfig()
