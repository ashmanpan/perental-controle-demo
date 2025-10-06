"""
FTD Integration Service - REST API
Provides HTTP API for managing FTD firewall rules
"""
import logging
from flask import Flask, request, jsonify
from typing import Dict

from config import load_config
from rule_manager import RuleManager

# Configure logging
config = load_config()
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize rule manager
rule_manager = None


@app.before_request
def initialize():
    """Initialize rule manager on first request"""
    global rule_manager
    if rule_manager is None:
        rule_manager = RuleManager(config)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'FTD Integration Service',
        'version': '1.0.0'
    }), 200


@app.route('/api/v1/rules/block', methods=['POST'])
def create_block_rule():
    """Create a firewall rule to block an application"""
    try:
        data = request.json

        source_ip = data.get('sourceIP')
        app_name = data.get('appName')
        ports = data.get('ports', [])
        msisdn = data.get('msisdn')

        if not all([source_ip, app_name, ports, msisdn]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Create rule
        result = rule_manager.create_block_rule(
            source_ip=source_ip,
            app_name=app_name,
            ports=ports,
            msisdn=msisdn
        )

        if result:
            return jsonify(result), 201
        else:
            return jsonify({'error': 'Failed to create rule'}), 500

    except Exception as e:
        logger.error(f"Error creating block rule: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/rules/<rule_id>', methods=['PUT'])
def update_rule(rule_id: str):
    """Update a firewall rule with new source IP"""
    try:
        data = request.json

        new_source_ip = data.get('newSourceIP')
        policy_id = data.get('policyId')

        if not new_source_ip:
            return jsonify({'error': 'Missing newSourceIP'}), 400

        # Update rule
        result = rule_manager.update_rule(
            rule_id=rule_id,
            new_source_ip=new_source_ip,
            policy_id=policy_id
        )

        if result:
            return jsonify(result), 200
        else:
            return jsonify({'error': 'Failed to update rule'}), 500

    except Exception as e:
        logger.error(f"Error updating rule: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id: str):
    """Delete a firewall rule"""
    try:
        data = request.json or {}
        policy_id = data.get('policyId')

        # Delete rule
        success = rule_manager.delete_rule(
            rule_id=rule_id,
            policy_id=policy_id
        )

        if success:
            return jsonify({'status': 'deleted', 'ruleId': rule_id}), 200
        else:
            return jsonify({'error': 'Failed to delete rule'}), 500

    except Exception as e:
        logger.error(f"Error deleting rule: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/rules/<rule_id>', methods=['GET'])
def verify_rule(rule_id: str):
    """Verify that a rule exists"""
    try:
        policy_id = request.args.get('policyId')

        exists = rule_manager.verify_rule(
            rule_id=rule_id,
            policy_id=policy_id
        )

        return jsonify({
            'ruleId': rule_id,
            'exists': exists,
            'status': 'active' if exists else 'not_found'
        }), 200

    except Exception as e:
        logger.error(f"Error verifying rule: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/deployment', methods=['POST'])
def deploy_changes():
    """Deploy policy changes to FTD devices"""
    try:
        data = request.json
        device_ids = data.get('deviceIds', [])

        if not device_ids:
            return jsonify({'error': 'Missing deviceIds'}), 400

        deployment_id = rule_manager.deploy_changes(device_ids)

        if deployment_id:
            return jsonify({
                'deploymentId': deployment_id,
                'status': 'initiated'
            }), 202
        else:
            return jsonify({'error': 'Failed to initiate deployment'}), 500

    except Exception as e:
        logger.error(f"Error deploying changes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/deployment/<deployment_id>', methods=['GET'])
def get_deployment_status(deployment_id: str):
    """Get deployment status"""
    try:
        status = rule_manager.get_deployment_status(deployment_id)

        if status:
            return jsonify(status), 200
        else:
            return jsonify({'error': 'Deployment not found'}), 404

    except Exception as e:
        logger.error(f"Error getting deployment status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 handler"""
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("FTD Integration Service")
    logger.info("Cisco Parental Control - Firewall Rule Management API")
    logger.info("=" * 80)

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=config.api_port,
        debug=(config.log_level == 'DEBUG')
    )


if __name__ == '__main__':
    main()
