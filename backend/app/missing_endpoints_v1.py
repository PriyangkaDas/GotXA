
# ============================================================================
# MISSING ENDPOINTS - INCIDENTS & ALERTS DETAIL  
# ============================================================================

@api.route('/incidents/<incident_id>', methods=['GET'])
@authenticate
def get_incident_details(incident_id):
    """Get incident investigation details."""
    try:
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        tasks = db.session.query(Task).filter_by(incident_id=incident_id).all()
        related_alerts = db.session.query(Alert).filter_by(incident_id=incident_id).all()
        return success_response({'id': incident.id, 'incident_id': incident.incident_id, 'title': incident.title, 'tasks_count': len(tasks), 'alerts_count': len(related_alerts)})
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/suppress', methods=['POST'])
@authenticate
@require_permission('alerts.suppress')
def suppress_alert(alert_id):
    """Suppress alert."""
    try:
        data = request.get_json()
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        alert.status = 'suppressed'
        db.session.commit()
        return success_response({'alert_id': alert_id, 'status': 'suppressed'}, 'Alert suppressed', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/status', methods=['PUT'])
@authenticate
@require_permission('alerts.write')
def update_alert_status(alert_id):
    """Update alert status."""
    try:
        data = request.get_json()
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        alert.status = data.get('status', 'open')
        db.session.commit()
        return success_response({'alert_id': alert_id, 'status': alert.status}, 'Status updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)
