# utils/redis_server.py
import redis
import json
from api.common.utils.logger import logger
from api.settings.config import env


class RedisMessageQueue:
    def __init__(self, queue_name=None):
        self.redis_client = redis.Redis(
            host=env.REDIS_HOST,
            port=env.REDIS_PORT,
            db=env.REDIS_DB,
        )
        self.queue_name = queue_name

    def send_message(self, message_data):
        """
        Send message to Redis queue
        """
        try:
            # Serialize message data
            message_json = json.dumps(message_data, ensure_ascii=False)

            # Use LPUSH to add message to the head of the queue
            result = self.redis_client.lpush(self.queue_name, message_json)

            logger.info(f"Message sent successfully, queue: {self.queue_name}, message ID: {result}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    def receive_message(self, timeout=0):
        """
        Receive message from queue
        timeout: Blocking timeout in seconds, 0 means infinite wait
        """
        try:
            # Use BRPOP to blockingly get message from the tail of the queue
            result = self.redis_client.brpop(self.queue_name, timeout=timeout)

            if result:
                queue_name, message_json = result
                message_data = json.loads(message_json)
                return message_data
            return None

        except Exception as e:
            logger.error(f"Failed to receive message: {str(e)}")
            return None

    def get_queue_length(self):
        """Get current queue length"""
        return self.redis_client.llen(self.queue_name)

    def clear_queue(self):
        """Clear queue"""
        return self.redis_client.delete(self.queue_name)
