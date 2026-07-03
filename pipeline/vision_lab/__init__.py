"""vision_lab —— 基于视觉大模型的实验性入库模块

与主 pipeline 物理隔离：只新增，不修改现有文件；入库写独立影子库。
复用主 pipeline 的 render / dedup / ingest / logger 与 quant-qa-reviewer agent，
仅替换中间的「OCR + 正则切题 + 答案关联」为「视觉抽取 + 跨页合并」。
"""
