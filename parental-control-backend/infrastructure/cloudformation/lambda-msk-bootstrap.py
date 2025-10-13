"""
Lambda function to get MSK bootstrap brokers for CloudFormation Custom Resource
"""
import json
import boto3
import urllib3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()
kafka_client = boto3.client('kafka')

def send_response(event, context, response_status, response_data, physical_resource_id=None, reason=None):
    """Send response to CloudFormation"""
    response_url = event['ResponseURL']

    response_body = {
        'Status': response_status,
        'Reason': reason or f'See CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': physical_resource_id or context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }

    json_response_body = json.dumps(response_body)

    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    try:
        response = http.request(
            'PUT',
            response_url,
            body=json_response_body,
            headers=headers
        )
        logger.info(f"Status code: {response.status}")
    except Exception as e:
        logger.error(f"send_response failed: {e}")

def lambda_handler(event, context):
    """Handle CloudFormation Custom Resource requests"""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        request_type = event['RequestType']

        if request_type == 'Delete':
            # Nothing to delete
            send_response(event, context, 'SUCCESS', {})
            return

        if request_type in ['Create', 'Update']:
            # Get MSK cluster ARN from properties
            cluster_arn = event['ResourceProperties']['ClusterArn']

            # Get bootstrap brokers
            response = kafka_client.get_bootstrap_brokers(ClusterArn=cluster_arn)

            logger.info(f"MSK Response: {json.dumps(response)}")

            # Extract bootstrap broker strings
            bootstrap_brokers_tls = response.get('BootstrapBrokerStringTls', '')
            bootstrap_brokers = response.get('BootstrapBrokerString', '')

            response_data = {
                'BootstrapBrokerStringTls': bootstrap_brokers_tls,
                'BootstrapBrokerString': bootstrap_brokers
            }

            send_response(event, context, 'SUCCESS', response_data, cluster_arn)
        else:
            send_response(event, context, 'FAILED', {}, reason=f'Unknown request type: {request_type}')

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        send_response(event, context, 'FAILED', {}, reason=str(e))
