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
    
    def _prepare_home_portal_values(self, counters):
        """Add appointment count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        
        if 'appointment_count' in counters:
            appointment_count = request.env['external.appointment'].search_count([
                ('portal_user_id', '=', request.env.user.id)
            ]) if request.env.user.id != request.website.user_id.id else 0
            values['appointment_count'] = appointment_count
        
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
            'upcoming': {'label': _('Upcoming'), 'domain': [('start_datetime', '>=', datetime.now()), ('status', '=', 'confirmed')]},
            'past': {'label': _('Past'), 'domain': [('start_datetime', '<', datetime.now())]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('status', '=', 'confirmed')]},
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
                return request.redirect('/my/appointments?message=cancelled')
            except Exception as e:
                _logger.error(f"Failed to cancel appointment {appointment_id}: {e}")
                return request.redirect(f'/my/appointments/{appointment_id}?error=cancel_failed')
        else:
            return request.redirect(f'/my/appointments/{appointment_id}?error=cannot_cancel')
