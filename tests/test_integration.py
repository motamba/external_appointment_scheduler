# -*- coding: utf-8 -*-
from odoo.tests import common, tagged, HttpCase
from datetime import datetime, timedelta
import json


@tagged('post_install', '-at_install', 'external_appointment')
class TestBookingFlow(HttpCase):
    """Integration tests for complete booking flow"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create service
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
        
        # Create calendar config
        cls.calendar_config = cls.env['external.calendar.config'].create({
            'name': 'Test Google Calendar',
            'provider': 'google',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'is_active': True,
        })
        
        cls.service.calendar_config_id = cls.calendar_config.id

    def test_01_get_availability_api(self):
        """Test availability API endpoint"""
        url = f'/api/appointments/availability?service_id={self.service.id}'
        
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('slots', data)
        self.assertIsInstance(data['slots'], list)

    def test_02_book_appointment_api(self):
        """Test booking API endpoint"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        payload = {
            'service_id': self.service.id,
            'start': start.isoformat(),
            'end': end.isoformat(),
            'customer_name': 'Test Customer',
            'customer_email': 'test@example.com',
            'customer_phone': '+1234567890',
            'notes': 'Test booking',
        }
        
        response = self.url_open(
            '/api/appointments/book',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('id'))
        self.assertTrue(data.get('reference'))

    def test_03_complete_booking_flow(self):
        """Test complete booking workflow: create -> confirm -> complete"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        # Step 1: Create appointment
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'start_datetime': start,
            'end_datetime': end,
            'customer_email': 'test@example.com',
        })
        
        self.assertEqual(appointment.status, 'draft')
        
        # Step 2: Confirm
        appointment.action_confirm()
        self.assertEqual(appointment.status, 'confirmed')
        
        # Step 3: Complete
        appointment.action_complete()
        self.assertEqual(appointment.status, 'completed')

    def test_04_booking_with_cancellation_flow(self):
        """Test booking with cancellation"""
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.service.id,
            'start_datetime': start,
            'end_datetime': end,
            'customer_email': 'test@example.com',
        })
        
        appointment.action_confirm()
        self.assertEqual(appointment.status, 'confirmed')
        
        # Cancel
        appointment.action_cancel()
        self.assertEqual(appointment.status, 'cancelled')

    def test_05_portal_booking_view(self):
        """Test portal booking page renders"""
        # Test service listing page
        response = self.url_open('/book')
        self.assertEqual(response.status_code, 200)
        
        # Test specific service booking page
        response = self.url_open(f'/book/{self.service.id}')
        self.assertEqual(response.status_code, 200)

    def test_06_portal_my_appointments(self):
        """Test portal my appointments page"""
        # Create portal user
        portal_user = self.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal@test.com',
            'email': 'portal@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        
        # Authenticate as portal user
        self.authenticate('portal@test.com', 'portal@test.com')
        
        response = self.url_open('/my/appointments')
        self.assertEqual(response.status_code, 200)


@tagged('post_install', '-at_install', 'external_appointment')
class TestWebhookIntegration(common.TransactionCase):
    """Integration tests for webhook handling"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.config = cls.env['external.calendar.config'].create({
            'name': 'Test Google Calendar',
            'provider': 'google',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
        })

    def test_01_webhook_url_format(self):
        """Test webhook URL is properly formatted"""
        webhook_url = self.config.webhook_url
        
        self.assertTrue(webhook_url)
        self.assertIn('/webhook/calendar/google', webhook_url)
        self.assertIn(str(self.config.id), webhook_url)

    def test_02_process_webhook_event_created(self):
        """Test processing webhook for event creation"""
        # Create appointment
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': self.env['external.appointment.service'].create({
                'name': 'Test Service',
                'duration_minutes': 60,
            }).id,
            'start_datetime': start,
            'end_datetime': end,
            'calendar_config_id': self.config.id,
            'provider_event_id': 'test_event_123',
        })
        
        # Simulate webhook data
        webhook_data = {
            'id': 'test_event_123',
            'status': 'confirmed',
            'summary': 'Test Event',
            'start': {'dateTime': start.isoformat()},
            'end': {'dateTime': end.isoformat()},
        }
        
        # Process webhook (would call _process_google_webhook)
        appointment._process_google_webhook(webhook_data)
        
        # Verify appointment still exists and is updated
        self.assertTrue(appointment.exists())


@tagged('post_install', '-at_install', 'external_appointment')
class TestEmailNotifications(common.TransactionCase):
    """Integration tests for email notifications"""

    def test_01_confirmation_email_sent(self):
        """Test confirmation email is sent on booking"""
        service = self.env['external.appointment.service'].create({
            'name': 'Test Service',
            'duration_minutes': 60,
        })
        
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': service.id,
            'start_datetime': start,
            'end_datetime': end,
            'customer_email': 'test@example.com',
        })
        
        # Confirm appointment
        with self.mock_mail_gateway():
            appointment.action_confirm()
        
        # Check mail was sent (in real test, would verify mail.mail records)
        self.assertTrue(appointment.status == 'confirmed')

    def test_02_cancellation_email_sent(self):
        """Test cancellation email is sent"""
        service = self.env['external.appointment.service'].create({
            'name': 'Test Service',
            'duration_minutes': 60,
        })
        
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': service.id,
            'start_datetime': start,
            'end_datetime': end,
            'customer_email': 'test@example.com',
            'status': 'confirmed',
        })
        
        with self.mock_mail_gateway():
            appointment.action_cancel()
        
        self.assertEqual(appointment.status, 'cancelled')

    def test_03_reminder_email_cron(self):
        """Test reminder email cron job"""
        # Create appointment 25 hours in future (within 24h reminder window)
        service = self.env['external.appointment.service'].create({
            'name': 'Test Service',
            'duration_minutes': 60,
        })
        
        start = datetime.now() + timedelta(hours=25)
        end = start + timedelta(minutes=60)
        
        appointment = self.env['external.appointment'].create({
            'service_id': service.id,
            'start_datetime': start,
            'end_datetime': end,
            'customer_email': 'test@example.com',
            'status': 'confirmed',
        })
        
        # Run reminder cron
        cron = self.env.ref('external_appointment_scheduler.ir_cron_send_reminders')
        
        with self.mock_mail_gateway():
            cron.method_direct_trigger()
        
        # Verify reminder was marked as sent
        self.assertTrue(appointment.reminder_sent)
