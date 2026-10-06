"""Celery background tasks for report generation and processing."""
import os
import json
from datetime import datetime
from celery import shared_task
from app.models import db, Report
from app.pdf_generator import generate_report_pdf

@shared_task(bind=True, name='tasks.process_security_events')
def process_security_events_task(self, events):
    """Persist incoming telemetry independently of HTTP collectors."""
    try:
        from app.api_ingestion import process_event_batch
        return process_event_batch(events)
    except Exception as error:
        db.session.rollback()
        raise self.retry(exc=error, countdown=5, max_retries=3)

@shared_task(bind=True, name='tasks.generate_report')
def generate_report_task(self, report_id):
    """
    Background task to generate PDF report from database record.
    
    Args:
        report_id: ID of the report in database
    """
    try:
        # Update status to processing
        report = Report.query.get(report_id)
        if not report:
            return {'status': 'error', 'message': f'Report {report_id} not found'}
        
        report.status = 'processing'
        db.session.commit()
        
        # Prepare report data
        report_data = {
            'title': report.title or 'SIEM Report',
            'report_type': report.type or 'executive',
            'filters': json.loads(report.filters) if report.filters else {},
            'data': json.loads(report.data) if report.data else [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Generate PDF
        pdf_buffer = generate_report_pdf(report_data)
        pdf_bytes = pdf_buffer.getvalue()
        
        # Save to file system
        reports_dir = os.getenv('REPORTS_DIR', '/app/reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        file_path = os.path.join(reports_dir, f'report_{report_id}.pdf')
        with open(file_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Update report status
        report.status = 'completed'
        report.file_path = file_path
        report.file_size = len(pdf_bytes)
        report.generated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'status': 'success',
            'report_id': report_id,
            'file_path': file_path,
            'file_size': len(pdf_bytes)
        }
    
    except Exception as e:
        # Update report status to failed
        try:
            report = Report.query.get(report_id)
            if report:
                report.status = 'failed'
                report.error_message = str(e)
                db.session.commit()
        except:
            pass
        
        return {
            'status': 'error',
            'report_id': report_id,
            'error': str(e)
        }

@shared_task(bind=True, name='tasks.generate_alert_report')
def generate_alert_report_task(self, filters):
    """Generate report from alerts matching filters."""
    try:
        from app.models import Alert
        
        query = Alert.query
        filter_dict = json.loads(filters) if isinstance(filters, str) else filters
        
        # Apply filters
        if filter_dict.get('severity'):
            query = query.filter_by(severity=filter_dict['severity'])
        if filter_dict.get('source'):
            query = query.filter_by(source=filter_dict['source'])
        if filter_dict.get('status'):
            query = query.filter_by(status=filter_dict['status'])
        
        alerts = query.all()
        alert_data = [{
            'id': a.id,
            'title': a.title,
            'severity': a.severity,
            'source': a.source,
            'status': a.status,
            'timestamp': a.timestamp.isoformat() if a.timestamp else ''
        } for a in alerts]
        
        return {
            'status': 'success',
            'alert_count': len(alert_data),
            'data': alert_data
        }
    
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

@shared_task(bind=True, name='tasks.generate_incident_report')
def generate_incident_report_task(self, filters):
    """Generate report from incidents matching filters."""
    try:
        from app.models import Incident
        
        query = Incident.query
        filter_dict = json.loads(filters) if isinstance(filters, str) else filters
        
        # Apply filters
        if filter_dict.get('severity'):
            query = query.filter_by(severity=filter_dict['severity'])
        if filter_dict.get('status'):
            query = query.filter_by(status=filter_dict['status'])
        
        incidents = query.all()
        incident_data = [{
            'id': i.id,
            'title': i.title,
            'severity': i.severity,
            'status': i.status,
            'description': i.description,
            'created_at': i.created_at.isoformat() if i.created_at else ''
        } for i in incidents]
        
        return {
            'status': 'success',
            'incident_count': len(incident_data),
            'data': incident_data
        }
    
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
