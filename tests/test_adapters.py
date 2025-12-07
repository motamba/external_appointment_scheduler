# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@tagged('post_install', '-at_install', 'external_appointment')
class TestGoogleAdapter(common.TransactionCase):
    """Test cases for Google Calendar adapter"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.config = cls.env['external.calendar.config'].create({
            'name': 'Test Google Calendar',
            'provider': 'google',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
        })

    def test_01_adapter_initialization(self):
        """Test adapter can be initialized"""
        from odoo.addons.external_appointment_scheduler.adapters.google_adapter import GoogleCalendarAdapter
        
        adapter = GoogleCalendarAdapter(self.config)
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.config, self.config)

    @patch('odoo.addons.external_appointment_scheduler.adapters.google_adapter.Flow')
    def test_02_get_authorization_url(self, mock_flow):
        """Test authorization URL generation"""
        from odoo.addons.external_appointment_scheduler.adapters.google_adapter import GoogleCalendarAdapter
        
        # Mock Flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = ('http://test.url', 'state')
        mock_flow.from_client_config.return_value = mock_flow_instance
        
        adapter = GoogleCalendarAdapter(self.config)
        url = adapter.get_authorization_url()
        
        self.assertTrue(isinstance(url, str))

    def test_03_format_event_data(self):
        """Test event data formatting"""
        from odoo.addons.external_appointment_scheduler.adapters.google_adapter import GoogleCalendarAdapter
        
        adapter = GoogleCalendarAdapter(self.config)
        
        start = datetime.now() + timedelta(days=7)
        end = start + timedelta(hours=1)
        
        event_data = adapter._format_event_data(
            summary='Test Appointment',
            description='Test Description',
            start_datetime=start,
            end_datetime=end,
            attendee_email='test@example.com'
        )
        
        self.assertIn('summary', event_data)
        self.assertIn('start', event_data)
        self.assertIn('end', event_data)
        self.assertEqual(event_data['summary'], 'Test Appointment')

    def test_04_scopes_defined(self):
        """Test required scopes are defined"""
        from odoo.addons.external_appointment_scheduler.adapters.google_adapter import GoogleCalendarAdapter
        
        adapter = GoogleCalendarAdapter(self.config)
        
        self.assertTrue(hasattr(adapter, 'SCOPES'))
        self.assertIn('calendar', adapter.SCOPES[0].lower())


@tagged('post_install', '-at_install', 'external_appointment')
class TestBaseAdapter(common.TransactionCase):
    """Test cases for base adapter"""

    def test_01_base_adapter_abstract_methods(self):
        """Test base adapter has required abstract methods"""
        from odoo.addons.external_appointment_scheduler.adapters.base_adapter import BaseCalendarAdapter
        
        # Should have abstract methods
        self.assertTrue(hasattr(BaseCalendarAdapter, 'get_authorization_url'))
        self.assertTrue(hasattr(BaseCalendarAdapter, 'get_available_slots'))
        self.assertTrue(hasattr(BaseCalendarAdapter, 'create_event'))
        self.assertTrue(hasattr(BaseCalendarAdapter, 'update_event'))
        self.assertTrue(hasattr(BaseCalendarAdapter, 'cancel_event'))

    def test_02_adapter_factory(self):
        """Test adapter factory returns correct adapter"""
        from odoo.addons.external_appointment_scheduler.adapters import get_adapter
        
        config = self.env['external.calendar.config'].create({
            'name': 'Test Google',
            'provider': 'google',
            'client_id': 'test',
            'client_secret': 'secret',
        })
        
        adapter = get_adapter(config)
        
        from odoo.addons.external_appointment_scheduler.adapters.google_adapter import GoogleCalendarAdapter
        self.assertIsInstance(adapter, GoogleCalendarAdapter)

    def test_03_unsupported_provider_error(self):
        """Test error for unsupported provider"""
        from odoo.addons.external_appointment_scheduler.adapters import get_adapter
        
        config = self.env['external.calendar.config'].create({
            'name': 'Test Unsupported',
            'provider': 'unsupported_provider',
            'client_id': 'test',
            'client_secret': 'secret',
        })
        
        with self.assertRaises(ValueError):
            get_adapter(config)
