"""
Kafka Producer - Publishes session events to Kafka
"""
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import boto3

from config import get_config

logger = logging.getLogger(__name__)


class SessionEventProducer:
    """Produces session events to Kafka"""

    def __init__(self):
        self.config = get_config()
        self.producer = self._create_producer()
        self.publish_success_count = 0
        self.publish_failure_count = 0

    def _create_producer(self) -> Producer:
        """Create Kafka producer with configuration"""
        kafka_config = {
            'bootstrap.servers': self.config.kafka.bootstrap_servers,
            'compression.type': self.config.kafka.compression_type,
            'batch.size': self.config.kafka.batch_size,
            'linger.ms': self.config.kafka.linger_ms,
            'acks': self.config.kafka.acks,
            'retries': self.config.kafka.retries,
            'client.id': 'p-gateway-simulator'
        }

        # Add security configuration for AWS MSK
        if self.config.kafka.security_protocol == 'SASL_SSL':
            kafka_config.update({
                'security.protocol': 'SASL_SSL',
                'sasl.mechanism': 'AWS_MSK_IAM',
                'sasl.jaas.config': 'software.amazon.msk.auth.iam.IAMLoginModule required;',
            })

        logger.info(f"Connecting to Kafka: {kafka_config['bootstrap.servers']}")
        return Producer(kafka_config)

    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err:
            self.publish_failure_count += 1
            logger.error(f"Message delivery failed: {err}")
        else:
            self.publish_success_count += 1
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[partition {msg.partition()}] at offset {msg.offset()}"
            )

    def publish_session_start(self, session) -> bool:
        """Publish SESSION_START event"""
        event = {
            'eventType': 'SESSION_START',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sessionId': session.session_id,
            'imsi': session.imsi,
            'msisdn': session.msisdn,
            'privateIP': session.private_ip,
            'publicIP': session.public_ip,
            'apn': session.apn,
            'ratType': session.rat_type,
            'sliceId': session.slice_id,
            'qci': session.qci,
            'expiresAt': session.expires_at.isoformat() + 'Z'
        }

        return self._publish(self.config.kafka.topic, event, session.msisdn)

    def publish_session_end(self, session) -> bool:
        """Publish SESSION_END event"""
        event = {
            'eventType': 'SESSION_END',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sessionId': session.session_id,
            'imsi': session.imsi,
            'msisdn': session.msisdn,
            'privateIP': session.private_ip,
            'publicIP': session.public_ip,
            'duration': (datetime.utcnow() - session.created_at).total_seconds()
        }

        return self._publish(self.config.kafka.topic, event, session.msisdn)

    def publish_ip_change(self, session, old_private_ip: str, old_public_ip: str) -> bool:
        """Publish IP_CHANGE event"""
        event = {
            'eventType': 'IP_CHANGE',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'sessionId': session.session_id,
            'imsi': session.imsi,
            'msisdn': session.msisdn,
            'oldPrivateIP': old_private_ip,
            'newPrivateIP': session.private_ip,
            'oldPublicIP': old_public_ip,
            'newPublicIP': session.public_ip,
            'reason': 'HANDOVER'
        }

        return self._publish(self.config.kafka.topic, event, session.msisdn)

    def _publish(self, topic: str, event: Dict, key: str = None) -> bool:
        """Publish event to Kafka topic"""
        try:
            # Use phone number as key for partitioning (ensures order per user)
            key_bytes = key.encode('utf-8') if key else None
            value_bytes = json.dumps(event).encode('utf-8')

            self.producer.produce(
                topic=topic,
                key=key_bytes,
                value=value_bytes,
                callback=self._delivery_callback
            )

            # Trigger callbacks (non-blocking)
            self.producer.poll(0)

            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            self.publish_failure_count += 1
            return False

    def flush(self, timeout: float = 10.0):
        """Flush pending messages"""
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages still pending after flush")

    def get_stats(self) -> Dict:
        """Get producer statistics"""
        return {
            'publish_success': self.publish_success_count,
            'publish_failure': self.publish_failure_count
        }

    def close(self):
        """Close producer"""
        logger.info("Flushing and closing Kafka producer...")
        self.flush()


class CloudWatchMetrics:
    """Publish metrics to CloudWatch"""

    def __init__(self):
        self.config = get_config()
        self.enabled = self.config.monitoring.enable_cloudwatch
        if self.enabled:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.config.aws_region)
            self.namespace = self.config.monitoring.cloudwatch_namespace
        else:
            self.cloudwatch = None

    def put_metric(self, metric_name: str, value: float, unit: str = 'Count'):
        """Put a metric to CloudWatch"""
        if not self.enabled:
            return

        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to publish CloudWatch metric: {e}")

    def put_metrics(self, metrics: Dict[str, float]):
        """Put multiple metrics to CloudWatch"""
        if not self.enabled:
            return

        try:
            metric_data = [
                {
                    'MetricName': name,
                    'Value': value,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
                for name, value in metrics.items()
            ]

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
        except Exception as e:
            logger.error(f"Failed to publish CloudWatch metrics: {e}")


def create_topics_if_not_exist():
    """Create Kafka topics if they don't exist"""
    config = get_config()

    admin_config = {
        'bootstrap.servers': config.kafka.bootstrap_servers
    }

    # Add security for AWS MSK
    if config.kafka.security_protocol == 'SASL_SSL':
        admin_config.update({
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'AWS_MSK_IAM',
        })

    admin_client = AdminClient(admin_config)

    # Define topics
    topics = [
        NewTopic(
            config.kafka.topic,
            num_partitions=6,
            replication_factor=3
        ),
        NewTopic(
            config.kafka.analytics_topic,
            num_partitions=3,
            replication_factor=3
        )
    ]

    # Create topics
    futures = admin_client.create_topics(topics)

    for topic, future in futures.items():
        try:
            future.result()  # Wait for operation to complete
            logger.info(f"Topic {topic} created successfully")
        except Exception as e:
            if 'already exists' in str(e).lower():
                logger.info(f"Topic {topic} already exists")
            else:
                logger.error(f"Failed to create topic {topic}: {e}")
