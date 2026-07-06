#!/usr/bin/env python3
"""
SQLite → PostgreSQL 数据迁移脚本

用法:
  python migrate_to_supabase.py "postgresql+asyncpg://user:pass@host:5432/db"
"""
import asyncio
import sys
import os
from datetime import datetime

SQLITE_URL = "sqlite+aiosqlite:///./quantquiz.db"
PG_URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PG_URL", "")

TABLES = [
    "sources",
    "tags",
    "questions",
    "question_tags",
    "options",
    "solutions",
    "attempt_logs",
    "favorites",
    "question_reports",
]

DT_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)


def parse_dt(v: str) -> datetime | None:
    v = v.strip().replace("Z", "+00:00")
    for fmt in DT_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def build_coerce(bool_cols: set, dt_cols: set, notnull_dt: set, int_defaults: dict):
    _now = datetime.now()

    def coerce(row: dict) -> dict:
        result = {}
        for k, v in row.items():
            if k in bool_cols:
                result[k] = bool(v) if v is not None else False
            elif k in dt_cols:
                if v is None:
                    result[k] = _now if k in notnull_dt else None
                else:
                    result[k] = parse_dt(str(v)) or (_now if k in notnull_dt else None)
            elif k in int_defaults and v is None:
                result[k] = int_defaults[k]
            else:
                result[k] = v
        return result

    return coerce


async def migrate():
    if not PG_URL:
        print("❌ 请提供连接串作为参数")
        sys.exit(1)

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlalchemy import text, Boolean, DateTime, Integer

    sqlite = create_async_engine(SQLITE_URL)
    pg = create_async_engine(PG_URL, poolclass=NullPool)

    print("🏗  建表...")
    from app.database import Base
    import app.models  # noqa
    async with pg.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   ✅ 建表完成")

    # 从模型中提取每张表的 bool / datetime 列
    table_meta: dict[str, dict] = {}
    for tbl in Base.metadata.tables.values():
        table_meta[tbl.name] = {
            "bool_cols":    {c.name for c in tbl.columns if isinstance(c.type, Boolean)},
            "dt_cols":      {c.name for c in tbl.columns if isinstance(c.type, DateTime)},
            "notnull_dt":   {c.name for c in tbl.columns if isinstance(c.type, DateTime) and not c.nullable},
            "int_defaults": {c.name: c.default.arg for c in tbl.columns if isinstance(c.type, Integer) and c.default is not None},
        }

    async with sqlite.connect() as src, pg.connect() as dst:
        # 一次性清空所有表，避免逐表 CASCADE 互相影响
        all_tables = ", ".join(reversed(TABLES))
        await dst.execute(text(f"TRUNCATE TABLE {all_tables} RESTART IDENTITY CASCADE"))
        await dst.commit()

        for table in TABLES:
            result = await src.execute(text(f"SELECT * FROM {table}"))
            rows = result.mappings().all()
            if not rows:
                print(f"   ⏭  {table}: 空表，跳过")
                continue

            cols = list(rows[0].keys())
            col_names = ", ".join(cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            insert_sql = text(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})")

            meta = table_meta.get(table, {"bool_cols": set(), "dt_cols": set(), "notnull_dt": set()})
            coerce = build_coerce(meta["bool_cols"], meta["dt_cols"], meta["notnull_dt"], meta.get("int_defaults", {}))

            # 过滤掉 question_id 孤儿行（SQLite 中外键未强制，可能存在脏数据）
            if "question_id" in cols:
                valid_qids = {r["id"] for r in (await src.execute(text("SELECT id FROM questions"))).mappings().all()}
                rows = [r for r in rows if r["question_id"] in valid_qids]

            batch = [coerce(dict(r)) for r in rows]
            for i in range(0, len(batch), 1000):
                await dst.execute(insert_sql, batch[i:i + 1000])

            await dst.commit()
            print(f"   ✅ {table}: {len(rows)} 行")

    await sqlite.dispose()
    await pg.dispose()
    print("\n🎉 迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate())
