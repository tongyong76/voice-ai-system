"""
RediSearch 全文检索索引管理
使用 Redis Stack Server 的 RediSearch 模块替代 Elasticsearch
"""
import json
from .redis import get_redis

# 索引名称
TRANSCRIPT_INDEX = "idx:transcript"

# 中文分词器 (Redis Stack 内置 chinese tokenizer)
CHINESE_TOKENIZER = "chinese"


async def create_transcript_index():
    """创建转写文本全文索引 (应用启动时调用)"""
    r = await get_redis()
    try:
        # 检查索引是否已存在
        info = await r.execute_command("FT.INFO", TRANSCRIPT_INDEX)
        print(f"RediSearch index '{TRANSCRIPT_INDEX}' already exists")
        return
    except Exception:
        pass  # 索引不存在, 需要创建

    try:
        # 创建索引:
        #   - HASH 类型, 前缀 doc:transcript:
        #   - full_text 字段: TEXT 类型, 中文分词, 权重 2.0
        #   - audio_id: NUMERIC 字段
        #   - language: TAG 字段
        await r.execute_command(
            "FT.CREATE", TRANSCRIPT_INDEX,
            "ON", "HASH",
            "PREFIX", "1", "doc:transcript:",
            "LANGUAGE", "chinese",
            "SCHEMA",
            "full_text", "TEXT", "WEIGHT", "2.0",
            "audio_id", "NUMERIC", "SORTABLE",
            "language", "TAG",
            "created_at", "TEXT",
        )
        print(f"Created RediSearch index: {TRANSCRIPT_INDEX}")
    except Exception as e:
        print(f"Failed to create RediSearch index: {e}")


async def index_transcript(transcript_id: int, audio_id: int, full_text: str, language: str = "zh"):
    """将转写文本索引到 RediSearch"""
    r = await get_redis()
    key = f"doc:transcript:{transcript_id}"
    await r.hset(key, mapping={
        "transcript_id": str(transcript_id),
        "audio_id": str(audio_id),
        "full_text": full_text,
        "language": language,
        "created_at": str(__import__("datetime").datetime.utcnow()),
    })


async def search_transcripts(
    query: str,
    device_id: int = None,
    start_time: str = None,
    end_time: str = None,
    offset: int = 0,
    limit: int = 50,
) -> list:
    """全文检索转写文本"""
    r = await get_redis()

    # 构建 RediSearch 查询
    # 基础: 全文搜索关键词
    search_query = f'@full_text:"{query}"'

    # 注意: device_id 和时间过滤需要在 MySQL 侧做二次过滤
    # RediSearch 只负责全文检索, 返回 transcript_id 列表后去 MySQL 补全数据

    try:
        result = await r.execute_command(
            "FT.SEARCH", TRANSCRIPT_INDEX,
            search_query,
            "LIMIT", offset, limit,
            "SORTBY", "audio_id", "DESC",
        )
    except Exception as e:
        print(f"RediSearch error: {e}, falling back to empty result")
        return []

    # 解析结果: [count, key1, fields1, key2, fields2, ...]
    if not result or len(result) < 2:
        return []

    count = result[0]
    results = []
    i = 1
    while i < len(result):
        key = result[i]  # e.g. "doc:transcript:123"
        fields = result[i + 1] if i + 1 < len(result) else []

        # 解析字段列表
        field_dict = {}
        for j in range(0, len(fields), 2):
            field_dict[fields[j].decode() if isinstance(fields[j], bytes) else fields[j]] = \
                fields[j + 1].decode() if isinstance(fields[j + 1], bytes) else fields[j + 1]

        results.append({
            "transcript_id": int(field_dict.get("transcript_id", 0)),
            "audio_id": int(field_dict.get("audio_id", 0)),
            "text": field_dict.get("full_text", ""),
            "language": field_dict.get("language", "zh"),
        })
        i += 2

    return results
