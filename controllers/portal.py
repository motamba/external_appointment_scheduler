# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AppointmentPortalController(CustomerPortal):
    """Portal controller for customer appointment management."""
    
    _items_per_page = 20
    
    def _prepare_home_portal_values(self, counters):
        """Add appointment count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        
        # Always provide the appointment count so the portal home can show the tile
        # without waiting for the async counters call.
        # Safely determine the website's public user id if available.
        website_user_id = None
        try:
            website = request.env['website'].sudo()
            current_website = website.get_current_website()
            website_user_id = current_website.user_id.id if current_website and current_website.user_id else None
        except Exception:
            website_user_id = None

        appointment_count = 0
        if request.env.user.id != website_user_id:
            appointment_count = request.env['external.appointment'].search_count([
                ('portal_user_id', '=', request.env.user.id)
            ])
        values['appointment_count'] = appointment_count

        # Ensure the async portal counters know about our appointment count
        try:
            portal_counters = request.session.get('portal_counters', {}).copy()
            portal_counters['appointment_count'] = bool(appointment_count)
            request.session['portal_counters'] = portal_counters
        except Exception:
            pass
        
        return values
    
    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointments(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """List all appointments for the current portal user."""
        values = self._prepare_portal_layout_values()
        AppointmentObj = request.env['external.appointment']
        
        domain = [('portal_user_id', '=', request.env.user.id)]
        
        # Search options
        searchbar_sortings = {
            'date': {'label': _('Appointment Date'), 'order': 'start_datetime desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'service': {'label': _('Service'), 'order': 'service_id'},
            'status': {'label': _('Status'), 'order': 'status'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'upcoming': {'label': _('Upcoming'), 'domain': [('start_datetime', '>=', datetime.now()), ('status', 'in', ['confirmed', 'checked_in'])]},
            'past': {'label': _('Past'), 'domain': [('start_datetime', '<', datetime.now())]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('status', '=', 'confirmed')]},
            'checked_in': {'label': _('Checked In'), 'domain': [('status', '=', 'checked_in')]},
            'completed': {'label': _('Completed'), 'domain': [('status', '=', 'completed')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('status', '=', 'cancelled')]},
        }
        
        # Default sort and filter
        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'all'
        
        order = searchbar_sortings[sortby]['order']
        domain += searchbar_filters[filterby]['domain']
        
        # Count for pager
        appointment_count = AppointmentObj.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/appointments",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=appointment_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get appointments
        appointments = AppointmentObj.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_appointments_history'] = appointments.ids[:100]
        
        values.update({
            'appointments': appointments,
            'page_name': 'appointment',
            'pager': pager,
            'default_url': '/my/appointments',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        
        return request.render("external_appointment_scheduler.portal_my_appointments", values)
    
    @http.route(['/my/appointments/<int:appointment_id>'], type='http', auth="user", website=True)
    def portal_my_appointment(self, appointment_id, access_token=None, **kw):
        """Display appointment details."""
        try:
            appointment_sudo = self._document_check_access('external.appointment', appointment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = {
            'appointment': appointment_sudo,
            'page_name': 'appointment',
        }
        
        return request.render("external_appointment_scheduler.portal_appointment_page", values)
    
    @http.route(['/book', '/book/<int:service_id>'], type='http', auth="public", website=True)
    def portal_book_appointment(self, service_id=None, **kw):
        """Booking landing page."""
        ServiceObj = request.env['external.appointment.service'].sudo()
        
        if service_id:
            service = ServiceObj.browse(service_id)
            if not service.exists() or not service.active:
                return request.redirect('/book')
        else:
            service = False
        
        # Get all active services
        services = ServiceObj.search([('active', '=', True)], order='sequence, name')
        
        values = {
            'service': service,
            'services': services,
            'page_name': 'book_appointment',
        }
        
        return request.render("external_appointment_scheduler.portal_book_appointment", values)
    
    @http.route(['/my/appointments/<int:appointment_id>/reschedule'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_appointment_reschedule(self, appointment_id, access_token=None, **kw):
        """Reschedule an appointment."""
        try:
            appointment_sudo = self._document_check_access('external.appointment', appointment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        if not appointment_sudo.can_reschedule:
            return request.redirect(f'/my/appointments/{appointment_id}?error=cannot_reschedule')
        
        # Handle POST - update appointment
        if request.httprequest.method == 'POST':
            new_start = kw.get('start_datetime')
            if new_start:
                try:
                    old_start = appointment_sudo.start_datetime
                    start_dt = datetime.fromisoformat(new_start.replace('Z', '+00:00'))
                    end_dt = start_dt + timedelta(minutes=appointment_sudo.service_id.duration_minutes)
                    appointment_sudo.sudo().write({
                        'start_datetime': start_dt,
                        'end_datetime': end_dt,
                    })
                    
                    # Send notification to customer
                    appointment_sudo.message_post(
                        body=f"Appointment rescheduled from {old_start.strftime('%Y-%m-%d %H:%M')} to {start_dt.strftime('%Y-%m-%d %H:%M')}",
                        subject="Appointment Rescheduled",
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                        partner_ids=[appointment_sudo.partner_id.id] if appointment_sudo.partner_id else [],
                    )
                    
                    # Send email notification
                    if appointment_sudo.customer_email:
                        mail_template = request.env.ref('external_appointment_scheduler.email_template_appointment_rescheduled', raise_if_not_found=False)
                        if mail_template:
                            mail_template.sudo().send_mail(appointment_sudo.id, force_send=True)
                    
                    return request.redirect(f'/my/appointments/{appointment_id}?message=rescheduled')
                except Exception as e:
                    _logger.error(f"Failed to reschedule appointment {appointment_id}: {e}")
                    return request.redirect(f'/my/appointments/{appointment_id}/reschedule?error=reschedule_failed')
        
        # Handle GET - show reschedule form
        values = {
            'appointment': appointment_sudo,
            'page_name': 'reschedule_appointment',
        }
        return request.render("external_appointment_scheduler.portal_reschedule_appointment", values)
    
    @http.route(['/my/appointments/<int:appointment_id>/cancel'], type='http', auth="user", website=True, methods=['POST'])
    def portal_appointment_cancel(self, appointment_id, access_token=None, **kw):
        """Cancel an appointment."""
        try:
            appointment_sudo = self._document_check_access('external.appointment', appointment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        if appointment_sudo.can_cancel:
            try:
                appointment_sudo.action_cancel()
                
                # Send notification to customer
                appointment_sudo.message_post(
                    body=f"Your appointment scheduled for {appointment_sudo.start_datetime.strftime('%Y-%m-%d %H:%M')} has been cancelled.",
                    subject="Appointment Cancelled",
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                    partner_ids=[appointment_sudo.partner_id.id] if appointment_sudo.partner_id else [],
                )
                
                # Send email notification
                if appointment_sudo.customer_email:
                    mail_template = request.env.ref('external_appointment_scheduler.email_template_appointment_cancelled', raise_if_not_found=False)
                    if mail_template:
                        mail_template.sudo().send_mail(appointment_sudo.id, force_send=True)
                
                return request.redirect('/my/appointments?message=cancelled')
            except Exception as e:
                _logger.error(f"Failed to cancel appointment {appointment_id}: {e}")
                return request.redirect(f'/my/appointments/{appointment_id}?error=cancel_failed')
        else:
            return request.redirect(f'/my/appointments/{appointment_id}?error=cannot_cancel')
