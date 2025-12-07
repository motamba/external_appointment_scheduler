# External Appointment Scheduler

## Overview

The External Appointment Scheduler module integrates Odoo with external calendar/booking APIs (Google Calendar, Calendly) to provide a seamless customer-facing appointment booking experience through the Odoo portal.

## Features

- **Google Calendar Integration**: OAuth2-based integration with real-time sync
- **Portal Booking**: Customer-facing interface for viewing availability and booking appointments
- **OWL Components**: Modern, responsive calendar and booking form components
- **Two-Way Sync**: Automatic synchronization between Odoo and external calendars
- **Service Management**: Define services with durations, pricing, and booking rules
- **Notifications**: Automated email confirmations and reminders
- **Webhook Support**: Real-time updates via webhooks
- **Admin Interface**: Comprehensive backend for managing appointments and configurations

## Installation

### Prerequisites

1. **Python Dependencies**:
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client cryptography
```

2. **Google Cloud Setup**:
   - Create a Google Cloud Project
   - Enable Google Calendar API
   - Create OAuth2 credentials (Web application)
   - Configure authorized redirect URIs

3. **Odoo Requirements**:
   - Odoo 19.0 or higher
   - HTTPS enabled (required for OAuth callbacks)

### Installation Steps

1. Copy the module to your Odoo addons directory:
```bash
cp -r external_appointment_scheduler /path/to/odoo/custom_modules/
```

2. Update the addons list:
   - Go to Apps menu
   - Click "Update Apps List"

3. Install the module:
   - Search for "External Appointment Scheduler"
   - Click "Install"

## Configuration

### 1. Google Calendar Setup

1. Navigate to **Settings → Appointments → External Calendar Configuration**
2. Create a new configuration:
   - **Name**: e.g., "Google Calendar - Main"
   - **Provider**: Select "Google Calendar"
   - **Client ID**: Your Google OAuth Client ID
   - **Client Secret**: Your Google OAuth Client Secret

3. Click "Connect with Google" to authorize access
4. Configure webhook URL in Google Cloud Console

### 2. Service Configuration

1. Go to **Appointments → Configuration → Services**
2. Create services:
   - **Name**: Service name (e.g., "Consultation")
   - **Duration**: Duration in minutes
   - **Buffer**: Buffer time after appointment
   - **Price**: Service price (optional)
   - **Booking Rules**: Min/max lead times, cancellation policy

### 3. Booking Rules

Navigate to **Settings → Appointments** to configure:
- Default working hours
- Minimum lead time before booking
- Maximum advance booking period
- Cancellation and rescheduling policies

## Usage

### For Customers (Portal)

1. **View Services**: Browse available appointment services
2. **Check Availability**: Select a service and view available time slots
3. **Book Appointment**: Choose a slot and fill in required information
4. **Manage Bookings**: View, cancel, or reschedule appointments from portal

### For Administrators

1. **View Appointments**: Access all appointments from Appointments menu
2. **Manual Booking**: Create appointments on behalf of customers
3. **Manage Sync**: Monitor synchronization status
4. **Reports**: View booking analytics and reports

## API Endpoints

### Availability
```
GET /api/appointments/availability?service_id=1&date_from=2025-12-10&date_to=2025-12-17
```

### Book Appointment
```
POST /api/appointments/book
Content-Type: application/json

{
  "service_id": 1,
  "start_datetime": "2025-12-10T09:00:00Z",
  "partner_id": 10,
  "notes": "First consultation"
}
```

### Cancel Appointment
```
PUT /api/appointments/<id>/cancel
```

## Webhook Configuration

### Google Calendar Webhook

1. Configure webhook URL: `https://yourdomain.com/webhook/calendar/google`
2. Set up Google Calendar watch channel
3. Webhook will automatically process calendar changes

## Troubleshooting

### Common Issues

**OAuth Connection Fails**:
- Verify Client ID and Secret are correct
- Ensure redirect URI is configured in Google Cloud Console
- Check that HTTPS is enabled

**Appointments Not Syncing**:
- Check webhook configuration
- Verify token hasn't expired (refresh from config)
- Check system logs for API errors

**Double Booking Occurs**:
- Ensure proper calendar is selected for service
- Check for race conditions in high-traffic scenarios
- Verify buffer times are configured

### Logs

Check Odoo logs for detailed error messages:
```bash
tail -f /var/log/odoo/odoo-server.log | grep appointment
```

## Development

### Extending Adapters

To add support for a new calendar provider:

1. Create a new adapter class extending `BaseAdapter`:
```python
from odoo.addons.external_appointment_scheduler.adapters.base_adapter import BaseAdapter

class CustomAdapter(BaseAdapter):
    def get_available_slots(self, service, date_from, date_to, constraints):
        # Implementation
        pass
```

2. Register the adapter in the provider selection

### Adding Custom Fields

Add custom fields to appointments by inheriting the model:
```python
class ExternalAppointment(models.Model):
    _inherit = 'external.appointment'
    
    custom_field = fields.Char(string='Custom Field')
```

## Security

- OAuth tokens are encrypted at rest
- CSRF protection on all endpoints
- Webhook signature validation
- Portal access controls
- Rate limiting on API endpoints

## Support

For issues, questions, or contributions:
- **Documentation**: See `/doc` directory
- **Issues**: Report bugs via issue tracker
- **Email**: support@yourcompany.com

## License

LGPL-3

## Credits

**Author**: Your Company  
**Maintainer**: Your Company  
**Contributors**: 
- Developer Name

## Changelog

### Version 19.0.1.0.0 (2025-12-06)
- Initial release
- Google Calendar integration
- Portal booking interface
- OWL calendar components
- Two-way synchronization
- Email notifications
- Webhook support
