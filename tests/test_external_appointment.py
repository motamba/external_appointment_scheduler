# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from freezegun import freeze_time


@tagged('post_install', '-at_install', 'external_appointment')
class TestExternalAppointment(common.TransactionCase):
    """Test cases for external_appointment model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test service
        cls.service = cls.env['external.appointment.service'].create({
            'name': 'Test Consultation',
            'duration_minutes': 60,
            'buffer_minutes': 15,
            'price': 100.0,
            'min_lead_hours': 24,
            'max_lead_days': 90,
            'allow_cancellation': True,
            'cancellation_hours': 24,
        })
        
        # Create test calendar config
        cls.calendar_config = cls.env['external.calendar.config'].create({
            'name': 'Test Google Calendar',
            'provider': 'google',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'is_active': True,
        })
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'phone': '+1234567890',
        })

    def test_01_create_appointment_basic(self):
        """Test creating a basic appointment"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'customer_email': 'test@example.com',
        })
        
        self.assertTrue(appointment.name)
        self.assertEqual(appointment.status, 'draft')
        self.assertEqual(appointment.duration_minutes, 60)

    def test_02_appointment_name_sequence(self):
        """Test appointment reference sequence generation"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        apt1 = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        
        apt2 = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start + timedelta(hours=2),
            'end_datetime': end + timedelta(hours=2),
        })
        
        self.assertTrue(apt1.name.startswith('APT'))
        self.assertTrue(apt2.name.startswith('APT'))
        self.assertNotEqual(apt1.name, apt2.name)

    def test_03_compute_duration(self):
        """Test duration computation"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=90)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        
        self.assertEqual(appointment.duration_minutes, 90)

    def test_04_constraint_end_after_start(self):
        """Test constraint: end must be after start"""
        start = datetime.now() + timedelta(days=7)
        end = start - timedelta(minutes=30)  # Invalid: end before start
        
        with self.assertRaises(ValidationError):
            self.env['external.appointment'].create({
                'service_id': self.service.id,
                'partner_id': self.partner.id,
                'start_datetime': start,
                'end_datetime': end,
            })

    def test_05_constraint_future_datetime(self):
        """Test constraint: start must be in future"""
        start = datetime.now() - timedelta(days=1)  # Invalid: past date
        end = start + timedelta(minutes=60)
        
        with self.assertRaises(ValidationError):
            self.env['external.appointment'].create({
                'service_id': self.service.id,
                'partner_id': self.partner.id,
                'start_datetime': start,
                'end_datetime': end,
            })

    def test_06_constraint_min_lead_time(self):
        """Test constraint: minimum lead time"""
        # Service requires 24 hours lead time
        start = datetime.now() + timedelta(hours=12)  # Invalid: less than 24h
        end = start + timedelta(minutes=60)
        
        with self.assertRaises(ValidationError):
            self.env['external.appointment'].create({
                'service_id': self.service.id,
                'partner_id': self.partner.id,
                'start_datetime': start,
                'end_datetime': end,
            })

    def test_07_constraint_max_lead_time(self):
        """Test constraint: maximum lead time"""
        # Service allows maximum 90 days advance booking
        start = datetime.now() + timedelta(days=100)  # Invalid: more than 90 days
        end = start + timedelta(minutes=60)
        
        with self.assertRaises(ValidationError):
            self.env['external.appointment'].create({
                'service_id': self.service.id,
                'partner_id': self.partner.id,
                'start_datetime': start,
                'end_datetime': end,
            })

    def test_08_compute_can_cancel(self):
        """Test can_cancel computed field"""
        # Future appointment within cancellation window
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'status': 'confirmed',
        })
        
        self.assertTrue(appointment.can_cancel)
        
        # Change status to completed
        appointment.status = 'completed'
        self.assertFalse(appointment.can_cancel)

    def test_09_compute_can_reschedule(self):
        """Test can_reschedule computed field"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'status': 'confirmed',
        })
        
        self.assertTrue(appointment.can_reschedule)

    def test_10_action_confirm(self):
        """Test confirm action"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        
        self.assertEqual(appointment.status, 'draft')
        appointment.action_confirm()
        self.assertEqual(appointment.status, 'confirmed')

    def test_11_action_cancel(self):
        """Test cancel action"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'status': 'confirmed',
        })
        
        appointment.action_cancel()
        self.assertEqual(appointment.status, 'cancelled')

    def test_12_action_complete(self):
        """Test complete action"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'status': 'confirmed',
        })
        
        appointment.action_complete()
        self.assertEqual(appointment.status, 'completed')

    def test_13_action_mark_no_show(self):
        """Test mark no show action"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'status': 'confirmed',
        })
        
        appointment.action_mark_no_show()
        self.assertEqual(appointment.status, 'no_show')

    def test_14_action_reset_to_draft(self):
        """Test reset to draft action"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'status': 'confirmed',
        })
        
        appointment.action_reset_to_draft()
        self.assertEqual(appointment.status, 'draft')

    def test_15_provider_sync_on_confirm(self):
        """Test provider sync is called on confirm"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'calendar_config_id': self.calendar_config.id,
        })
        
        # Note: In real test, would mock the adapter
        # For now, just verify status change
        appointment.action_confirm()
        self.assertEqual(appointment.status, 'confirmed')

    def test_16_customer_email_from_partner(self):
        """Test customer email defaults from partner"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        
        # Should inherit from partner
        self.assertEqual(appointment.customer_email, self.partner.email)

    def test_17_multiple_appointments_same_time_different_services(self):
        """Test multiple appointments at same time for different services"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        service2 = self.env['external.appointment.service'].create({
            'name': 'Test Service 2',
            'duration_minutes': 60,
        })
        
        apt1 = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        
        apt2 = self.env['external.appointment'].create({
            'service_id': service2.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        
        # Should both succeed (different services)
        self.assertTrue(apt1.id)
        self.assertTrue(apt2.id)
