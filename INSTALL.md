# External Appointment Scheduler - Quick Start Guide

## Installation

### Step 1: Install Python Dependencies

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client cryptography
```

### Step 2: Install Odoo Module

1. Module is already in `custom_modules/external_appointment_scheduler`
2. Restart Odoo server
3. Go to Apps menu
4. Click "Update Apps List"
5. Search for "External Appointment Scheduler"
6. Click "Install"

### Step 3: Configure Google Calendar

1. **Create Google Cloud Project:**
   - Go to https://console.cloud.google.com
   - Create a new project
   - Enable Google Calendar API
   - Go to Credentials → Create Credentials → OAuth Client ID
   - Application type: Web application
   - Add authorized redirect URI: `http://localhost:8069/calendar/oauth/callback` (or your domain)
   - Download credentials (you'll need Client ID and Secret)

2. **Configure in Odoo:**
   - Go to Settings → Appointments → Configuration → Calendar Providers
   - Click "Create"
   - Name: "Google Calendar - Main"
   - Provider: Google Calendar
   - Client ID: (paste from Google Cloud Console)
   - Client Secret: (paste from Google Cloud Console)
   - Click "Save"
   - Click "Connect with Google"
   - Authorize access to your Google Calendar
   - You should see "Successfully Connected!"

### Step 4: Create Services

1. Go to Appointments → Configuration → Services
2. Click "Create"
3. Fill in service details:
   - Name: "Consultation"
   - Duration: 60 minutes
   - Buffer: 15 minutes
   - Price: 100.00 (optional)
   - Min Lead Hours: 24
   - Max Lead Days: 90
4. Click "Save"

Repeat for other services you want to offer.

### Step 5: Test Booking Flow

1. **Portal Access:**
   - Open browser in incognito mode
   - Go to `http://localhost:8069/book`
   - Select a service
   - Choose an available time slot
   - Fill in booking details
   - Submit booking

2. **Check in Backend:**
   - Go to Appointments → All Appointments
   - You should see the new appointment
   - Status should be "Confirmed"
   - Provider Event ID should be populated

3. **Check Google Calendar:**
   - Open your Google Calendar
   - You should see the appointment event

## Quick Test Checklist

- [ ] Module installed successfully
- [ ] Google Calendar connected
- [ ] At least one service created
- [ ] Test booking from portal works
- [ ] Appointment appears in Odoo
- [ ] Event created in Google Calendar
- [ ] Confirmation email sent
- [ ] Can view appointment in portal
- [ ] Can cancel appointment (if allowed)
- [ ] Cancellation syncs to Google Calendar

## Troubleshooting

### OAuth Connection Fails
- **Problem:** Can't connect to Google Calendar
- **Solution:** 
  - Verify Client ID and Secret are correct
  - Ensure redirect URI matches exactly (including http/https)
  - Check that Calendar API is enabled in Google Cloud Console

### No Available Slots
- **Problem:** Calendar shows no available time slots
- **Solution:**
  - Check service has "Calendar ID" set (or uses default "primary")
  - Verify Google Calendar is not fully booked
  - Check business hours (currently hardcoded 9 AM - 5 PM)

### Appointment Not Syncing
- **Problem:** Appointment not appearing in Google Calendar
- **Solution:**
  - Check token hasn't expired (go to Calendar Config, click "Test Connection")
  - Check Odoo logs for errors
  - Verify appointment status is "confirmed"

### Webhook Not Working
- **Problem:** Changes in Google Calendar not reflecting in Odoo
- **Solution:**
  - Webhooks require HTTPS and public URL
  - For local testing, use ngrok or similar
  - Click "Setup Webhook" in Calendar Configuration

## Development Mode Testing

For development testing without HTTPS:

1. **Disable Webhook (use polling instead)**
   - Webhooks require HTTPS
   - Can implement polling fallback for local dev

2. **Use ngrok for webhook testing:**
   ```bash
   ngrok http 8069
   ```
   - Use the ngrok URL as redirect URI
   - Update Google Cloud Console with ngrok URL

## Demo Data

The module includes demo services:
- Initial Consultation (60 min, $100)
- Follow-up Session (30 min, $50)
- Group Workshop (90 min, $150)

To load demo data:
- Check "Demo Data" when installing module
- Or go to Settings → Technical → Demo Data

## Common Configuration

### Adjust Settings

Go to Settings → Appointments to configure:
- Default minimum lead time (24 hours)
- Maximum advance booking (90 days)
- Allow customer cancellation
- Cancellation notice period
- Send confirmation emails
- Send reminder emails

### Create More Services

Services can have different:
- Durations
- Pricing
- Booking rules
- Cancellation policies
- Capacities (for group sessions)

## Next Steps

1. **Customize Email Templates:**
   - Go to Settings → Technical → Email Templates
   - Search for "Appointment"
   - Edit confirmation, cancellation, and reminder templates

2. **Setup Webhook (for production):**
   - Requires HTTPS domain
   - Go to Calendar Config
   - Click "Setup Webhook"
   - Copy webhook URL to configure in Google

3. **Add Portal Menu:**
   - Appointments automatically appear in portal
   - Users can view/manage their appointments at `/my/appointments`

4. **Test Complete Flow:**
   - Create portal user
   - Book appointment as portal user
   - Receive confirmation email
   - View in portal
   - Receive reminder email
   - Complete/cancel appointment

## Support

For issues or questions:
- Check DEVELOPMENT_STATUS.md for implementation details
- Review Odoo logs: `tail -f /var/log/odoo/odoo-server.log`
- Check module README.md for detailed documentation

---

**Module Version:** 19.0.1.0.0  
**Last Updated:** December 6, 2025
