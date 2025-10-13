"""
Analytics Dashboard API
Provides REST API for parental control analytics
"""
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from .config import load_config
from .analytics_client import AnalyticsClient

# Configure logging
config = load_config()
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app, origins=config.cors_origins)

# Initialize analytics client
analytics_client = None


@app.before_request
def initialize():
    """Initialize analytics client on first request"""
    global analytics_client
    if analytics_client is None:
        analytics_client = AnalyticsClient(config)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Analytics Dashboard API',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@app.route('/api/v1/parent/<parent_email>/dashboard', methods=['GET'])
def get_parent_dashboard(parent_email: str):
    """Get dashboard data for a parent"""
    try:
        dashboard = analytics_client.get_parent_dashboard(parent_email)

        if dashboard:
            return jsonify(dashboard), 200
        else:
            return jsonify({'error': 'No data found'}), 404

    except Exception as e:
        logger.error(f"Error getting parent dashboard: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/parent/<parent_email>/children', methods=['GET'])
def get_children(parent_email: str):
    """Get list of children for a parent"""
    try:
        children = analytics_client.get_children_for_parent(parent_email)

        return jsonify({
            'parentEmail': parent_email,
            'childrenCount': len(children),
            'children': children
        }), 200

    except Exception as e:
        logger.error(f"Error getting children: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/child/<child_phone>/daily', methods=['GET'])
def get_daily_summary(child_phone: str):
    """Get daily summary for a child"""
    try:
        date = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))

        summary = analytics_client.get_daily_summary(child_phone, date)

        if summary:
            return jsonify(summary), 200
        else:
            return jsonify({'error': 'No data found'}), 404

    except Exception as e:
        logger.error(f"Error getting daily summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/child/<child_phone>/weekly', methods=['GET'])
def get_weekly_summary(child_phone: str):
    """Get 7-day summary for a child"""
    try:
        summary = analytics_client.get_weekly_summary(child_phone)

        if summary:
            return jsonify(summary), 200
        else:
            return jsonify({'error': 'No data found'}), 404

    except Exception as e:
        logger.error(f"Error getting weekly summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/child/<child_phone>/history', methods=['GET'])
def get_enforcement_history(child_phone: str):
    """Get enforcement history for a child"""
    try:
        limit = int(request.args.get('limit', 50))

        history = analytics_client.get_enforcement_history(child_phone, limit)

        return jsonify({
            'childPhoneNumber': child_phone,
            'historyCount': len(history),
            'history': history
        }), 200

    except Exception as e:
        logger.error(f"Error getting enforcement history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/child/<child_phone>/report', methods=['GET'])
def get_detailed_report(child_phone: str):
    """Get detailed report for a date range"""
    try:
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')

        if not start_date or not end_date:
            return jsonify({'error': 'startDate and endDate required'}), 400

        report = analytics_client.get_detailed_report(child_phone, start_date, end_date)

        if report:
            return jsonify(report), 200
        else:
            return jsonify({'error': 'No data found'}), 404

    except Exception as e:
        logger.error(f"Error getting detailed report: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/session/phone/<phone_number>', methods=['GET'])
def get_session_by_phone(phone_number: str):
    """Get current active session for a phone number"""
    try:
        session = analytics_client.get_current_session(phone_number)

        if session:
            return jsonify(session), 200
        else:
            return jsonify({
                'phoneNumber': phone_number,
                'status': 'no_active_session',
                'message': 'No active session found for this phone number'
            }), 404

    except Exception as e:
        logger.error(f"Error getting session by phone: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/session/ip/<ip_address>', methods=['GET'])
def get_session_by_ip(ip_address: str):
    """Get session by IP address (reverse lookup)"""
    try:
        session = analytics_client.get_session_by_ip(ip_address)

        if session:
            return jsonify(session), 200
        else:
            return jsonify({
                'ipAddress': ip_address,
                'status': 'not_found',
                'message': 'No session found for this IP address'
            }), 404

    except Exception as e:
        logger.error(f"Error getting session by IP: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/sessions/active/count', methods=['GET'])
def get_active_sessions_count():
    """Get count of all active sessions"""
    try:
        count = analytics_client.get_active_sessions_count()

        return jsonify({
            'activeSessionsCount': count,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200

    except Exception as e:
        logger.error(f"Error getting active sessions count: {e}", exc_info=True)
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
    logger.info("Analytics Dashboard API")
    logger.info("Cisco Parental Control - Parent Analytics Service")
    logger.info("=" * 80)

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=config.api_port,
        debug=(config.log_level == 'DEBUG')
    )


if __name__ == '__main__':
    main()
