import json
import asyncio
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


async def redis_subscriber_task():
    """Background task: subscribe to Redis channels and broadcast to WebSocket clients"""
    from ..api.ws import manager

    while True:
        try:
            r = await get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe("audio:inference_result", "alert:trigger")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        # Broadcast to "realtime" channel (default WebSocket channel)
                        channel = data.pop("channel", "realtime")
                        await manager.broadcast(channel, data)
                    except Exception as e:
                        print(f"Error processing Redis message: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Redis subscriber error: {e}, reconnecting in 5s...")
            await asyncio.sleep(5)
