# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Appointment settings
    appointment_default_lead_hours = fields.Integer(
        string='Default Minimum Lead Time (Hours)',
        default=24,
        config_parameter='external_appointment_scheduler.default_lead_hours',
        help='Default minimum hours before appointment can be booked'
    )
    
    appointment_default_max_days = fields.Integer(
        string='Default Maximum Advance Booking (Days)',
        default=90,
        config_parameter='external_appointment_scheduler.default_max_days',
        help='Default maximum days in advance for bookings'
    )
    
    appointment_allow_cancellation = fields.Boolean(
        string='Allow Customer Cancellation',
        default=True,
        config_parameter='external_appointment_scheduler.allow_cancellation',
        help='Allow customers to cancel appointments via portal'
    )
    
    appointment_cancellation_hours = fields.Integer(
        string='Default Cancellation Notice (Hours)',
        default=24,
        config_parameter='external_appointment_scheduler.cancellation_hours',
        help='Default minimum hours notice for cancellation'
    )
    
    appointment_allow_reschedule = fields.Boolean(
        string='Allow Customer Reschedule',
        default=True,
        config_parameter='external_appointment_scheduler.allow_reschedule',
        help='Allow customers to reschedule appointments via portal'
    )
    
    appointment_send_confirmation = fields.Boolean(
        string='Send Confirmation Emails',
        default=True,
        config_parameter='external_appointment_scheduler.send_confirmation',
        help='Automatically send confirmation emails when appointment is booked'
    )
    
    appointment_send_reminders = fields.Boolean(
        string='Send Reminder Emails',
        default=True,
        config_parameter='external_appointment_scheduler.send_reminders',
        help='Automatically send reminder emails before appointments'
    )
    
    appointment_reminder_hours = fields.Integer(
        string='Reminder Time (Hours Before)',
        default=24,
        config_parameter='external_appointment_scheduler.reminder_hours',
        help='How many hours before appointment to send reminder'
    )
    
    # Calendar provider settings
    appointment_default_provider_id = fields.Many2one(
        'external.calendar.config',
        string='Default Calendar Provider',
        config_parameter='external_appointment_scheduler.default_provider_id',
        help='Default calendar provider for new services'
    )
    
    # Portal settings
    appointment_portal_show_past = fields.Boolean(
        string='Show Past Appointments in Portal',
        default=True,
        config_parameter='external_appointment_scheduler.portal_show_past',
        help='Show past appointments to portal users'
    )
    
    appointment_portal_max_future_days = fields.Integer(
        string='Portal Calendar View Range (Days)',
        default=60,
        config_parameter='external_appointment_scheduler.portal_max_future_days',
        help='How many days ahead to show in portal calendar'
    )
    
    # API settings
    appointment_api_rate_limit = fields.Integer(
        string='API Rate Limit (requests/minute)',
        default=60,
        config_parameter='external_appointment_scheduler.api_rate_limit',
        help='Rate limit for appointment API endpoints'
    )
    
    appointment_cache_ttl = fields.Integer(
        string='Availability Cache TTL (seconds)',
        default=300,
        config_parameter='external_appointment_scheduler.cache_ttl',
        help='How long to cache availability results (5 minutes default)'
    )
