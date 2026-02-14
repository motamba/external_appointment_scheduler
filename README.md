# External Appointment Scheduler

[![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-18%20%7C%2019-714B67)](https://www.odoo.com)

## Overview

**External Appointment Scheduler** is a full-featured Odoo module that integrates Odoo with external calendar providers (Google Calendar, other providers via adapters) and provides a customer-facing portal for booking, rescheduling and managing appointments. Designed for Odoo 18 and 19 Community editions.

✓ Optional demo services and example configuration to accelerate testing and deployment.

## Key Features

✓ Manual & portal-driven bookings and rescheduling

✓ Two-way synchronization with external calendars (Google Calendar adapter included)

✓ OWL-based portal components (calendar, slot picker, booking form) and vanilla JS fallbacks

✓ Email notifications for lifecycle events (confirmation, reminder, reschedule, cancel, checked-in, completed, no-show)

✓ Webhook support and background cron jobs for synchronization and reminders

✓ Configurable cancellation/reschedule rules, buffer times and capacities per service

✓ Access-control rules separating portal users from internal staff

## Screenshots

![Booking Calendar](static/description/screenshot_booking.png)
![Portal My Appointments](static/description/screenshot_services.png)

## Installation

1. Copy the module folder into your Odoo `addons` / `custom_modules` path.
2. Install Python dependencies if you plan to enable Google Calendar integration:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client cryptography
```

3. Restart Odoo and update the Apps list.
4. Install *External Appointment Scheduler* from Apps.

## Configuration

### Initial Setup

1. Navigate to **Settings → Appointments → External Calendar Configuration** and create a calendar config.
2. Set OAuth credentials (Client ID / Client Secret) or use a secure environment-backed secret store for production.
3. Create Services (Appointments → Configuration → Services): duration, buffer, capacity, cancellation/reschedule rules and calendar mapping.

### Scheduled Jobs & Reminders

- Cron jobs exist to send reminders and to synchronize with configured external calendars. Adjust frequency under **Settings → Technical → Automation → Scheduled Actions**.

## Usage

### Portal (Customers)

Customers may create, reschedule, and cancel appointments (subject to service rules) via the portal UI. Portal actions are recorded and notifications sent according to templates in `data/mail_templates.xml`.

### Back Office

Administrators and managers can view and manage all appointments, trigger manual syncs, and review logs.

## API Endpoints

Availability example:

```
GET /api/appointments/availability?service_id=1&date_from=2026-02-14&date_to=2026-02-21
```

Book appointment example:

```
POST /api/appointments/book
Content-Type: application/json

{
  "service_id": 1,
  "start_datetime": "2026-02-21T09:00:00Z",
  "partner_id": 10,
  "notes": "Consultation"
}
```

## Technical Details

### Models
- `external.appointment` — Core appointment model
- `external.appointment.service` — Service definitions

### Services
- Adapters for external calendar providers are located under `adapters/`
- Cron jobs and synchronization logic under `data/cron_jobs.xml` and `models/`

## Troubleshooting

### Common Issues

**OAuth Connection Fails**:
- Verify Client ID and Secret and the configured redirect URIs in the provider console.

**Emails Not Sent**:
- Ensure the Odoo outgoing mail server is configured and working.

**Portal Action Denied**:
- Check record rules in `security/security.xml` and that the portal user matches `portal_user_id` on the record.

## FAQ

### Can I use other calendar providers besides Google?
Yes. The module is adapter-based — add an adapter in `adapters/` to support another provider.

### Are appointments visible to portal users immediately after booking?
Yes — portal users can view their appointments in the My Appointments area.

## Compatibility

- **Odoo Versions**: 18, 19
- **Editions**: Community (CE).
- **OS**: Windows, Linux, macOS

## Support

For issues or paid support:
- Email: tambamodou68@gmail.com
- Documentation: see `/doc`

## Changelog

### Version 0.1 (2026-02-14)
- Initial release: booking portal, Google Calendar adapter, OWL components, email templates, cron jobs, basic logging.

## License

This module is licensed under **LGPL-3**. See `LICENSE` for full text.

## Credits

**Author**: Modou Tamba  
**Maintainer**: Modou Tamba

---

© 2026 Modou Tamba. All rights reserved.
## API Endpoints
