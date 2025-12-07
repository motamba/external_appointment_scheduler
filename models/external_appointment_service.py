# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ExternalAppointmentService(models.Model):
    _name = 'external.appointment.service'
    _description = 'Appointment Service'
    _order = 'sequence, name'

    name = fields.Char(
        string='Service Name',
        required=True,
        translate=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order services in lists'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    description = fields.Html(
        string='Description',
        translate=True,
        sanitize=True
    )
    
    # Duration settings
    duration_minutes = fields.Integer(
        string='Duration (Minutes)',
        required=True,
        default=60,
        help='Duration of the appointment in minutes'
    )
    
    buffer_minutes = fields.Integer(
        string='Buffer Time (Minutes)',
        default=0,
        help='Buffer time after appointment to prepare for next booking'
    )
    
    # Capacity and pricing
    capacity = fields.Integer(
        string='Capacity',
        default=1,
        help='Maximum number of simultaneous appointments for this service'
    )
    
    price = fields.Monetary(
        string='Price',
        currency_field='currency_id',
        help='Service price (optional)'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Booking rules
    min_lead_hours = fields.Integer(
        string='Minimum Lead Time (Hours)',
        default=24,
        help='Minimum hours before appointment can be booked'
    )
    
    max_lead_days = fields.Integer(
        string='Maximum Advance Booking (Days)',
        default=90,
        help='Maximum days in advance appointment can be booked'
    )
    
    allow_cancellation = fields.Boolean(
        string='Allow Cancellation',
        default=False,
        help='Allow customers to cancel appointments'
    )
    
    cancellation_hours = fields.Integer(
        string='Cancellation Notice (Hours)',
        default=24,
        help='Minimum hours notice required for cancellation'
    )
    
    allow_reschedule = fields.Boolean(
        string='Allow Reschedule',
        default=True,
        help='Allow customers to reschedule appointments'
    )
    
    # Provider settings
    calendar_id = fields.Char(
        string='Calendar ID',
        help='External provider calendar ID for this service'
    )
    
    provider_id = fields.Many2one(
        'external.calendar.config',
        string='Calendar Provider',
        help='Default calendar provider for this service'
    )

    # Backwards-compatible field expected by tests
    calendar_config_id = fields.Many2one(
        'external.calendar.config',
        string='Calendar Configuration',
        help='Alias for provider configuration',
        compute='_compute_calendar_config_alias',
        inverse='_inverse_calendar_config_alias',
        store=True
    )
    
    # Relations
    appointment_ids = fields.One2many(
        'external.appointment',
        'service_id',
        string='Appointments'
    )
    
    appointment_count = fields.Integer(
        string='Appointment Count',
        compute='_compute_appointment_count',
        store=True
    )
    
    # Display fields
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color index for kanban view'
    )
    
    image_1920 = fields.Image(
        string='Image',
        max_width=1920,
        max_height=1920
    )
    
    image_128 = fields.Image(
        string='Image 128',
        related='image_1920',
        max_width=128,
        max_height=128,
        store=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # SQL Constraints are handled via Python constraints in Odoo 19

    @api.constrains('duration_minutes', 'buffer_minutes', 'price', 'capacity')
    def _check_positive_values(self):
        for service in self:
            if service.duration_minutes <= 0:
                raise ValidationError(_('Duration must be positive!'))
            if service.buffer_minutes < 0:
                raise ValidationError(_('Buffer time cannot be negative!'))
            if service.price and service.price < 0:
                raise ValidationError(_('Price cannot be negative'))
            if service.capacity is not None and service.capacity <= 0:
                raise ValidationError(_('Capacity must be at least 1'))
    
    @api.depends('appointment_ids')
    def _compute_appointment_count(self):
        """Compute total number of appointments for this service."""
        for service in self:
            service.appointment_count = len(service.appointment_ids)

    def _compute_calendar_config_alias(self):
        for rec in self:
            rec.calendar_config_id = rec.provider_id and rec.provider_id.id or False

    def _inverse_calendar_config_alias(self):
        for rec in self:
            if rec.calendar_config_id:
                rec.provider_id = rec.calendar_config_id.id
            else:
                rec.provider_id = False
    
    @api.constrains('min_lead_hours', 'max_lead_days')
    def _check_booking_rules(self):
        """Validate booking rules make sense."""
        for service in self:
            if service.min_lead_hours > (service.max_lead_days * 24):
                raise ValidationError(_(
                    'Minimum lead time (%d hours) cannot be greater than maximum advance booking (%d days).'
                ) % (service.min_lead_hours, service.max_lead_days))
    
    def action_view_appointments(self):
        """View all appointments for this service."""
        self.ensure_one()
        return {
            'name': _('Appointments: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'external.appointment',
            'view_mode': 'tree,form,calendar,kanban',
            'domain': [('service_id', '=', self.id)],
            'context': {
                'default_service_id': self.id,
                'search_default_upcoming': 1,
            }
        }
    
    def get_available_slots(self, date_from, date_to, timezone='UTC'):
        """Get available time slots for this service.
        
        Args:
            date_from (datetime): Start date for availability check
            date_to (datetime): End date for availability check
            timezone (str): Timezone for the slots
            
        Returns:
            list: List of available slots
        """
        self.ensure_one()
        
        # Get provider adapter
        if not self.provider_id:
            return []
        
        adapter = self.provider_id._get_adapter()
        if not adapter:
            return []
        
        # Get available slots from provider
        try:
            slots = adapter.get_available_slots(
                service=self,
                date_from=date_from,
                date_to=date_to,
                constraints={
                    'duration': self.duration_minutes,
                    'buffer': self.buffer_minutes,
                    'calendar_id': self.calendar_id,
                }
            )
            return slots
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Failed to get available slots for service {self.id}: {e}")
            return []
    
    def copy(self, default=None):
        """Override copy to add (copy) to name."""
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super(ExternalAppointmentService, self).copy(default)
