import json
import pika
# from common_util.json_tools import json_dumps  # 包不可用，改用标准库 json
from api.common.utils.logger import logger
from env import env


class RabbitMQMessageQueue:
    def __init__(self, queue_name):
        self.channel = None
        self.queue_name = queue_name
        # Connect after defining queue name and other parameters
        self._connect()

    def _connect(self):
        """Establish RabbitMQ connection"""
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

            # Declare queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,   # Queue persistence
                arguments={
                    'x-message-ttl': 60000  # Message survival time 60 seconds
                }
            )

            logger.info(f"RabbitMQ connection successful, {self.queue_name}")

        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {str(e)}")
            raise

    def send_message(self, message_data):
        """
        Send message to RabbitMQ queue
        """
        try:
            # Ensure connection is valid
            if self.connection is None or self.connection.is_closed:
                self._connect()
            # Serialize message
            message_body = json.dumps(message_data, ensure_ascii=False)
            # Publish message
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
            logger.info(f"Message sent successfully, queue: {self.queue_name}, message ID: {message_data['message_id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    def consume_messages(self, callback, auto_ack=False):
        """
        Consume messages
        callback: Callback function to process messages
        auto_ack: Whether to automatically acknowledge messages
        """
        try:
            # Ensure connection is valid
            if self.connection is None or self.connection.is_closed:
                self._connect()

            # Set QoS
            self.channel.basic_qos(prefetch_count=1)

            # Start consuming
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )

            logger.info(f"Start consuming messages, queue: {self.queue_name}")
            self.channel.start_consuming()

        except Exception as e:
            logger.error(f"Failed to consume messages: {str(e)}")
            raise

    def close_connection(self):
        """Close connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Failed to close connection: {str(e)}")

    def __del__(self):
        """Destructor, ensure connection is closed"""
        self.close_connection()