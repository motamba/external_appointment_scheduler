# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class AppointmentRescheduleWizard(models.TransientModel):
    _name = 'appointment.reschedule.wizard'
    _description = 'Appointment Reschedule Wizard'

    appointment_id = fields.Many2one(
        'external.appointment',
        string='Appointment',
        required=True,
        readonly=True
    )
    
    service_id = fields.Many2one(
        related='appointment_id.service_id',
        string='Service',
        readonly=True
    )
    
    old_start_datetime = fields.Datetime(
        string='Current Date & Time',
        readonly=True
    )
    
    new_start_datetime = fields.Datetime(
        string='New Date & Time',
        required=True
    )
    
    new_end_datetime = fields.Datetime(
        string='New End Time',
        compute='_compute_new_end_datetime',
        store=True
    )
    
    reason = fields.Text(
        string='Reason for Rescheduling',
        help='Optional reason for the reschedule'
    )
    
    @api.depends('new_start_datetime', 'service_id')
    def _compute_new_end_datetime(self):
        """Compute new end datetime based on service duration."""
        for wizard in self:
            if wizard.new_start_datetime and wizard.service_id:
                wizard.new_end_datetime = wizard.new_start_datetime + timedelta(
                    minutes=wizard.service_id.duration_minutes
                )
            else:
                wizard.new_end_datetime = False
    
    @api.constrains('new_start_datetime')
    def _check_new_datetime(self):
        """Validate new datetime."""
        for wizard in self:
            if wizard.new_start_datetime:
                # Check if in the future
                if wizard.new_start_datetime <= fields.Datetime.now():
                    raise ValidationError(_('New appointment time must be in the future.'))
                
                # Check lead time
                hours_until = (wizard.new_start_datetime - fields.Datetime.now()).total_seconds() / 3600
                if hours_until < wizard.service_id.min_lead_hours:
                    raise ValidationError(_(
                        'Appointments must be booked at least %d hours in advance.'
                    ) % wizard.service_id.min_lead_hours)
    
    def action_confirm_reschedule(self):
        """Confirm the reschedule."""
        self.ensure_one()
        
        # Update appointment
        self.appointment_id.write({
            'start_datetime': self.new_start_datetime,
            'end_datetime': self.new_end_datetime,
        })
        
        # Add note about reschedule
        if self.reason:
            self.appointment_id.message_post(
                body=_('Appointment rescheduled. Reason: %s') % self.reason
            )
        else:
            self.appointment_id.message_post(
                body=_('Appointment rescheduled from %s to %s') % (
                    self.old_start_datetime,
                    self.new_start_datetime
                )
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Appointment rescheduled successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }
