# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta
import json
import base64
import logging

_logger = logging.getLogger(__name__)


class AppointmentAPIController(http.Controller):
    """JSON API endpoints for appointment operations."""
    
    @http.route('/api/appointments/availability', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def get_availability(self, **kw):
        """Get available time slots for a service.
        
        Args:
            service_id (int): Service ID
            date_from (str): Start date (ISO format)
            date_to (str): End date (ISO format)
            timezone (str): Timezone
            
        Returns:
            dict: Available slots and service info
        """
        try:
            # Support GET query params and POST JSON bodies
            if request.httprequest.method == 'POST' and request.httprequest.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    body = request.httprequest.get_data().decode('utf-8') or '{}'
                    payload = json.loads(body)
                except Exception:
                    payload = {}
                service_id = payload.get('service_id') or payload.get('service')
                date_from = payload.get('date_from') or payload.get('start')
                date_to = payload.get('date_to') or payload.get('end')
                timezone = payload.get('timezone', 'UTC')
            else:
                service_id = kw.get('service_id') or kw.get('service')
                date_from = kw.get('date_from') or kw.get('start')
                date_to = kw.get('date_to') or kw.get('end')
                timezone = kw.get('timezone', 'UTC')

            if not service_id:
                err = {'error': 'Missing required parameter: service_id'}
                return request.make_response(json.dumps(err), headers=[('Content-Type', 'application/json')])

            service = request.env['external.appointment.service'].sudo().browse(int(service_id))
            if not service.exists() or not service.active:
                return {'error': 'Service not found or inactive'}

            # Parse dates or provide sensible defaults (7 day window)
            if date_from and date_to:
                dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            else:
                now_dt = datetime.utcnow()
                dt_from = now_dt
                dt_to = now_dt + timedelta(days=7)

            # Get available slots
            slots = service.get_available_slots(dt_from, dt_to, timezone)
            
            # Format slots for response
            formatted_slots = []
            for slot in slots:
                start_dt = slot['start']
                end_dt = slot['end']
                formatted_slots.append({
                    'id': slot.get('id'),
                    'start': start_dt.isoformat(),
                    'end': end_dt.isoformat(),
                    'start_display': start_dt.strftime('%B %d, %Y at %I:%M %p'),
                    'end_display': end_dt.strftime('%I:%M %p'),
                    'available': True,
                    'capacity': slot.get('capacity'),
                })
            
            result = {
                'success': True,
                'slots': formatted_slots,
                'service': {
                    'id': service.id,
                    'name': service.name,
                    'duration': service.duration_minutes,
                    'price': service.price,
                    'currency': service.currency_id.name,
                }
            }

            return request.make_response(json.dumps(result), headers=[('Content-Type', 'application/json')])
            
        except Exception as e:
            _logger.error(f"Error getting availability: {e}")
            return request.make_response(json.dumps({'error': str(e)}), headers=[('Content-Type', 'application/json')])
    
    @http.route('/api/appointments/book', type='http', auth='public', methods=['POST'], csrf=False)
    def book_appointment(self, **kw):
        """Create a new appointment booking.
        
        Args:
            service_id (int): Service ID
            start_datetime (str): Start datetime (ISO format)
            partner_id (int, optional): Partner ID (for logged in users)
            partner_name (str, optional): Customer name
            partner_email (str, optional): Customer email
            partner_phone (str, optional): Customer phone
            notes (str, optional): Appointment notes
            
        Returns:
            dict: Booking result
        """
        try:
            # Parse JSON body if present
            payload = {}
            if request.httprequest.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    payload = json.loads(request.httprequest.get_data() or b'{}')
                except Exception:
                    payload = {}

            service_id = payload.get('service_id') or payload.get('service') or kw.get('service_id') or kw.get('service')
            start_datetime = payload.get('start') or payload.get('start_datetime') or kw.get('start_datetime') or kw.get('start')
            partner_id = payload.get('partner_id') or kw.get('partner_id')
            partner_name = payload.get('customer_name') or payload.get('partner_name') or kw.get('customer_name') or kw.get('partner_name') or kw.get('name')
            partner_email = payload.get('customer_email') or payload.get('partner_email') or kw.get('customer_email') or kw.get('partner_email') or kw.get('email')
            partner_phone = payload.get('customer_phone') or payload.get('partner_phone') or kw.get('customer_phone') or kw.get('partner_phone') or kw.get('phone')
            notes = payload.get('notes') or kw.get('notes')

            # Debug logging: record what was received to help diagnose missing partner fields
            try:
                received_body = request.httprequest.get_data().decode('utf-8') if request.httprequest.get_data() else ''
            except Exception:
                received_body = '<unreadable>'
            _logger.info(
                'Booking request received: headers=%s, form_keys=%s, payload_keys=%s, body=%s',
                dict(request.httprequest.headers),
                list(kw.keys()),
                list(payload.keys()),
                (received_body[:200] + '...') if len(received_body) > 200 else received_body,
            )

            if not service_id or not start_datetime:
                err = {'error': 'Missing required parameters: service_id and start_datetime'}
                return request.make_response(json.dumps(err), headers=[('Content-Type', 'application/json')])

            service = request.env['external.appointment.service'].sudo().browse(int(service_id))
            if not service.exists() or not service.active:
                err = {'error': 'Service not found or inactive'}
                return request.make_response(json.dumps(err), headers=[('Content-Type', 'application/json')])

            # Parse start datetime
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)
            
            # Get or create partner
            if partner_id:
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
                # Update partner phone if provided
                if partner_phone and partner.phone != partner_phone:
                    partner.write({'phone': partner_phone})
            elif partner_email:
                # Search for existing partner
                partner = request.env['res.partner'].sudo().search([
                    ('email', '=', partner_email)
                ], limit=1)
                
                if not partner:
                    # Create new partner
                    partner = request.env['res.partner'].sudo().create({
                        'name': partner_name or partner_email,
                        'email': partner_email,
                        'phone': partner_phone,
                    })
                else:
                    # Update existing partner phone if provided
                    if partner_phone and partner.phone != partner_phone:
                        partner.write({'phone': partner_phone})
            else:
                # Provide more context in the error to aid debugging (safe: only keys, not full values)
                err = {
                    'error': 'Partner information required',
                    'received': {
                        'form_keys': list(kw.keys()),
                        'json_keys': list(payload.keys()),
                    }
                }
                _logger.warning('Partner info missing for booking: %s', err['received'])
                return request.make_response(json.dumps(err), headers=[('Content-Type', 'application/json')])
            
            # Create appointment
            # Determine created_via and portal user without relying on request.website
            public_user = request.env.ref('base.public_user', False)
            public_user_id = public_user.id if public_user else None

            appointment_vals = {
                'service_id': service.id,
                'partner_id': partner.id,
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'notes': notes,
                'customer_email': partner_email,
                'customer_phone': partner_phone,
                'created_via': 'api' if request.env.user.id == public_user_id else 'portal',
                'status': 'draft',
            }
            
            # Set portal user if logged in
            if request.env.user.id != public_user_id:
                appointment_vals['portal_user_id'] = request.env.user.id
            
            appointment = request.env['external.appointment'].sudo().create(appointment_vals)

            # Process file attachments if any
            if request.httprequest.files:
                IrAttachment = request.env['ir.attachment'].sudo()
                # Get all files from the 'attachments' field (multiple files)
                files = request.httprequest.files.getlist('attachments')
                for file_upload in files:
                    if file_upload and file_upload.filename:
                        # Read file data
                        file_data = file_upload.read()
                        # Create attachment
                        IrAttachment.create({
                            'name': file_upload.filename,
                            'datas': base64.b64encode(file_data),
                            'res_model': 'external.appointment',
                            'res_id': appointment.id,
                            'type': 'binary',
                        })

            # Confirm appointment
            appointment.action_confirm()

            # Check if this is a form submission (form POST) vs API call (JSON)
            content_type = request.httprequest.headers.get('Content-Type', '')
            is_api_call = content_type.startswith('application/json')
            
            if is_api_call:
                # API call - return JSON response
                response = {
                    'success': True,
                    'appointment_id': appointment.id,
                    'appointment_ref': appointment.name,
                    'status': appointment.status,
                    'provider_event_id': appointment.provider_event_id,
                    'message': _('Appointment booked successfully! Confirmation email sent.'),
                    'id': appointment.id,
                    'reference': appointment.name,
                }
                return request.make_response(json.dumps(response), headers=[('Content-Type', 'application/json')])
            else:
                # Form submission - redirect to appointment detail page
                return request.redirect('/my/appointments/%s?booking_success=1' % appointment.id)

        except Exception as e:
            _logger.error(f"Error booking appointment: {e}")
            return request.make_response(json.dumps({'error': str(e)}), headers=[('Content-Type', 'application/json')])
    
    @http.route('/api/appointments/<int:appointment_id>/cancel', type='jsonrpc', auth='user', methods=['POST'])
    def cancel_appointment(self, appointment_id, **kw):
        """Cancel an appointment.
        
        Args:
            appointment_id (int): Appointment ID
            
        Returns:
            dict: Cancellation result
        """
        try:
            appointment = request.env['external.appointment'].browse(appointment_id)
            
            if not appointment.exists():
                return {'error': 'Appointment not found'}
            
            # Check access
            if appointment.portal_user_id.id != request.env.user.id:
                return {'error': 'Access denied'}
            
            if not appointment.can_cancel:
                return {'error': 'Appointment cannot be cancelled'}
            
            appointment.action_cancel()
            
            return {
                'success': True,
                'message': _('Appointment cancelled successfully'),
            }
            
        except Exception as e:
            _logger.error(f"Error cancelling appointment: {e}")
            return {'error': str(e)}
    
    @http.route('/api/appointments/<int:appointment_id>/reschedule', type='jsonrpc', auth='user', methods=['POST'])
    def reschedule_appointment(self, appointment_id, new_start_datetime, **kw):
        """Reschedule an appointment.
        
        Args:
            appointment_id (int): Appointment ID
            new_start_datetime (str): New start datetime (ISO format)
            
        Returns:
            dict: Reschedule result
        """
        try:
            appointment = request.env['external.appointment'].browse(appointment_id)
            
            if not appointment.exists():
                return {'error': 'Appointment not found'}
            
            # Check access
            if appointment.portal_user_id.id != request.env.user.id:
                return {'error': 'Access denied'}
            
            if not appointment.can_reschedule:
                return {'error': 'Appointment cannot be rescheduled'}
            
            # Parse new datetime
            new_start_dt = datetime.fromisoformat(new_start_datetime.replace('Z', '+00:00'))
            new_end_dt = new_start_dt + timedelta(minutes=appointment.service_duration)
            
            # Update appointment
            appointment.write({
                'start_datetime': new_start_dt,
                'end_datetime': new_end_dt,
            })
            
            return {
                'success': True,
                'message': _('Appointment rescheduled successfully'),
            }
            
        except Exception as e:
            _logger.error(f"Error rescheduling appointment: {e}")
            return {'error': str(e)}
    
    @http.route('/api/services', type='jsonrpc', auth='public', methods=['GET'])
    def get_services(self, **kw):
        """Get list of active services.
        
        Returns:
            dict: List of services
        """
        try:
            services = request.env['external.appointment.service'].sudo().search([
                ('active', '=', True)
            ], order='sequence, name')
            
            service_list = []
            for service in services:
                service_list.append({
                    'id': service.id,
                    'name': service.name,
                    'description': service.description,
                    'duration': service.duration_minutes,
                    'price': service.price,
                    'currency': service.currency_id.name,
                    'allow_cancellation': service.allow_cancellation,
                    'allow_reschedule': service.allow_reschedule,
                })
            
            return {
                'success': True,
                'services': service_list,
            }
            
        except Exception as e:
            _logger.error(f"Error getting services: {e}")
            return {'error': str(e)}
