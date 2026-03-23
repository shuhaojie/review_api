import json
import pika
# from common_util.json_tools import json_dumps  # Package unavailable; using stdlib json instead
from api.common.utils.logger import logger
from api.settings.config import env


class RabbitMQMessageQueue:
    def __init__(self, queue_name):
        self.channel = None
        self.queue_name = queue_name
        self._connect()

    def _connect(self):
        """Establish a RabbitMQ connection and declare the queue."""
        try:
            credentials = pika.PlainCredentials(
                env.MQ_USERNAME,
                env.MQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=env.MQ_HOST,
                port=env.MQ_PORT,
                virtual_host=env.MQ_VIRTUAL_HOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 60000  # TTL: 60 seconds
                }
            )

            logger.info(f"RabbitMQ connected, queue: {self.queue_name}")

        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {str(e)}")
            raise

    def send_message(self, message_data):
        """Serialize and publish a message to the queue."""
        try:
            if self.connection is None or self.connection.is_closed:
                self._connect()
            message_body = json.dumps(message_data, ensure_ascii=False)
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent message
                    content_type='application/json',
                    message_id=message_data['message_id']
                )
            )
            logger.info(f"Message sent to queue '{self.queue_name}', message_id={message_data['message_id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    def consume_messages(self, callback, auto_ack=False):
        """
        Start consuming messages from the queue.

        :param callback: Function called for each received message.
        :param auto_ack: If True, messages are acknowledged automatically.
        """
        try:
            if self.connection is None or self.connection.is_closed:
                self._connect()

            self.channel.basic_qos(prefetch_count=1)

            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )

            logger.info(f"Consuming messages from queue: {self.queue_name}")
            self.channel.start_consuming()

        except Exception as e:
            logger.error(f"Failed to consume messages: {str(e)}")
            raise

    def close_connection(self):
        """Close the RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("RabbitMQ connection closed.")
        except Exception as e:
            logger.error(f"Failed to close connection: {str(e)}")

    def __del__(self):
        self.close_connection()
