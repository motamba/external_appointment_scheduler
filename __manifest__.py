# -*- coding: utf-8 -*-
{
    'name': 'External Appointment Scheduler',
    'version': '19.0.1.0.0',
    'category': 'Services/Appointments',
    'summary': 'Integrate Odoo with external calendar APIs for customer appointment booking',
    'description': """
        External Appointment Scheduler
        ================================
        
        Features:
        ---------
        * Integration with Google Calendar API (OAuth2)
        * Customer-facing portal booking interface
        * Real-time availability checking
        * Two-way synchronization with external calendars
        * OWL-based calendar components
        * Service-based appointment management
        * Email and SMS notifications
        * Webhook support for real-time updates
        * Admin configuration interface
        * Comprehensive reporting and analytics
        
        Supported Providers:
        -------------------
        * Google Calendar (Primary)
        * Calendly (Future enhancement)
        
        Requirements:
        -------------
        * Valid Google Cloud Project with Calendar API enabled
        * OAuth2 credentials (Client ID & Secret)
        * HTTPS domain for webhook callbacks
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'portal',
        'mail',
        'calendar',
        'contacts',
    ],
    'external_dependencies': {
        'python': [
            'google-auth',
            'google-auth-oauthlib',
            'google-auth-httplib2',
            'google-api-python-client',
            'cryptography',
        ],
    },
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/mail_templates.xml',
        'data/cron_jobs.xml',
        
        # Views
        'views/external_appointment_views.xml',
        'views/external_appointment_service_views.xml',
        'views/external_calendar_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/portal_templates.xml',
        'views/menu_views.xml',
        
        # Wizards
        'wizards/appointment_reschedule_wizard_views.xml',
    ],
    'demo': [
        'demo/appointment_services_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # OWL Components for backend
            'external_appointment_scheduler/static/src/components/**/*_owl.js',
            'external_appointment_scheduler/static/src/components/**/*.xml',
            'external_appointment_scheduler/static/src/components/**/*.scss',
        ],
        'web.assets_frontend': [
            # Vanilla JS for portal (no OWL dependency)
            'external_appointment_scheduler/static/src/utils/api.js',
            'external_appointment_scheduler/static/src/components/appointment_calendar/appointment_calendar.js',
            'external_appointment_scheduler/static/src/components/slot_picker/slot_picker.js',
            'external_appointment_scheduler/static/src/components/booking_form/booking_form.js',
            'external_appointment_scheduler/static/src/components/**/*.scss',
        ],
    },
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
