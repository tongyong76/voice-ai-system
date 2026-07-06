import redis.asyncio as redis
from .config import get_settings

settings = get_settings()

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=50)


async def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)


async def publish_message(channel: str, message: str):
    """Publish message to Redis channel for WebSocket broadcast"""
    r = await get_redis()
    await r.publish(channel, message)
    await r.close()
