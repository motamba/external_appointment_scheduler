# -*- coding: utf-8 -*-

from odoo.addons.external_appointment_scheduler.adapters.base_adapter import BaseAdapter
from datetime import datetime, timedelta
import logging
import json

_logger = logging.getLogger(__name__)

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    import google.auth.exceptions
except ImportError:
    _logger.warning("Google Calendar API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


class GoogleCalendarAdapter(BaseAdapter):
    """Google Calendar API adapter for appointment scheduling."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self, env=None, config=None):
        super().__init__(env, config)
        self.service = None

    def _format_event_data(self, summary, description, start_datetime, end_datetime, attendee_email=None, location=None):
        """Helper to normalize event payload used by tests.

        Returns a dict compatible with create_event/update_event helpers.
        """
        attendees = []
        if attendee_email:
            attendees.append({'email': attendee_email})

        return {
            'summary': summary,
            'description': description,
            'start': start_datetime,
            'end': end_datetime,
            'attendees': attendees,
            'location': location or ''
        }
    
    def _get_service(self):
        """Get authenticated Google Calendar service.
        
        Returns:
            Resource: Google Calendar API service
        """
        if self.service:
            return self.service
        
        token = self._get_valid_token()
        
        # Get token record
        token_record = self.config.token_ids[0] if self.config.token_ids else None
        if not token_record:
            raise Exception("No token record found")
        
        # Create credentials
        credentials = Credentials(
            token=token_record.access_token,
            refresh_token=token_record.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            scopes=self.SCOPES
        )
        
        # Build service
        self.service = build('calendar', 'v3', credentials=credentials)
        return self.service
    
    def get_authorization_url(self):
        """Get OAuth2 authorization URL.
        
        Returns:
            str: Authorization URL
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f"{base_url}/calendar/oauth/callback"
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state for verification
        self.env['ir.config_parameter'].sudo().set_param(
            f'google_oauth_state_{self.config.id}', state
        )
        
        return authorization_url
    
    def exchange_code_for_token(self, code, redirect_uri=None):
        """Exchange authorization code for tokens.
        
        Args:
            code (str): Authorization code
            redirect_uri (str): Redirect URI
            
        Returns:
            dict: Token data
        """
        if not redirect_uri:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = f"{base_url}/calendar/oauth/callback"
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(seconds=credentials.expiry.timestamp() - datetime.now().timestamp())
        
        token_data = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'scope': ' '.join(self.SCOPES)
        }
        
        # Create token record
        self.env['external.calendar.token'].create({
            'config_id': self.config.id,
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_type': 'Bearer',
            'scope': ' '.join(self.SCOPES),
            'expires_at': expires_at,
        })
        
        return token_data
    
    def refresh_access_token(self, refresh_token):
        """Refresh access token.
        
        Args:
            refresh_token (str): Refresh token
            
        Returns:
            dict: New token data
        """
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            scopes=self.SCOPES
        )
        
        request = Request()
        credentials.refresh(request)
        
        return {
            'access_token': credentials.token,
            'token_type': 'Bearer',
            'expires_in': 3600,
        }
    
    def revoke_token(self, token):
        """Revoke access token.
        
        Args:
            token (str): Token to revoke
        """
        import requests
        
        revoke_url = 'https://oauth2.googleapis.com/revoke'
        response = requests.post(revoke_url, 
            params={'token': token},
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            _logger.warning(f"Failed to revoke token: {response.text}")
    
    def test_connection(self):
        """Test connection to Google Calendar.
        
        Returns:
            dict: Connection test result
        """
        service = self._get_service()
        
        # Try to list calendars
        calendar_list = service.calendarList().list(maxResults=10).execute()
        
        return {
            'success': True,
            'calendars_found': len(calendar_list.get('items', [])),
            'message': f"Successfully connected! Found {len(calendar_list.get('items', []))} calendars."
        }
    
    def get_available_slots(self, service, date_from, date_to, constraints):
        """Get available time slots from Google Calendar.
        
        Args:
            service: Appointment service record
            date_from (datetime): Start date
            date_to (datetime): End date
            constraints (dict): Constraints (duration, buffer, calendar_id)
            
        Returns:
            list: Available slots
        """
        calendar_service = self._get_service()
        calendar_id = constraints.get('calendar_id') or 'primary'
        
        # Get free/busy information
        body = {
            "timeMin": self._format_datetime(date_from),
            "timeMax": self._format_datetime(date_to),
            "items": [{"id": calendar_id}],
            "timeZone": "UTC"
        }
        
        freebusy_result = calendar_service.freebusy().query(body=body).execute()
        
        # Extract busy times
        busy_times = []
        calendar_busy = freebusy_result.get('calendars', {}).get(calendar_id, {}).get('busy', [])
        
        for busy_period in calendar_busy:
            busy_times.append({
                'start': self._parse_datetime(busy_period['start']),
                'end': self._parse_datetime(busy_period['end'])
            })
        
        # Generate potential slots based on working hours
        # For now, generate slots during business hours (9 AM - 5 PM)
        all_slots = self._generate_business_hour_slots(
            date_from,
            date_to,
            constraints.get('duration', 60),
            constraints.get('buffer', 15)
        )
        
        # Filter out busy slots
        available_slots = self._filter_slots_by_busy_times(all_slots, busy_times)
        
        return available_slots
    
    def _generate_business_hour_slots(self, start_date, end_date, duration_minutes, buffer_minutes):
        """Generate slots during business hours.
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            duration_minutes (int): Slot duration
            buffer_minutes (int): Buffer time
            
        Returns:
            list: Generated slots
        """
        slots = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        # Business hours: 9 AM to 5 PM
        business_start_hour = 9
        business_end_hour = 17
        
        while current_date <= end_date_only:
            # Create datetime for business start and end
            day_start = datetime.combine(current_date, datetime.min.time()).replace(
                hour=business_start_hour, minute=0, second=0, microsecond=0
            )
            day_end = datetime.combine(current_date, datetime.min.time()).replace(
                hour=business_end_hour, minute=0, second=0, microsecond=0
            )
            
            # Ensure we don't start before the requested start_date
            if day_start < start_date:
                day_start = start_date
            
            # Generate slots for this day
            day_slots = self._generate_time_slots(day_start, day_end, duration_minutes, buffer_minutes)
            slots.extend(day_slots)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return slots
    
    def create_event(self, event_data):
        """Create a Google Calendar event.
        
        Args:
            event_data (dict): Event data
            
        Returns:
            str: Event ID
        """
        service = self._get_service()
        calendar_id = 'primary'  # Can be made configurable
        
        event = {
            'summary': event_data.get('summary', 'Appointment'),
            'description': event_data.get('description', ''),
            'start': {
                'dateTime': self._format_datetime(event_data['start']),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': self._format_datetime(event_data['end']),
                'timeZone': 'UTC',
            },
        }
        
        # Add location if provided
        if event_data.get('location'):
            event['location'] = event_data['location']
        
        # Add attendees if provided
        if event_data.get('attendees'):
            event['attendees'] = event_data['attendees']
        
        # Add reminders
        event['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                {'method': 'popup', 'minutes': 60},  # 1 hour before
            ],
        }
        
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        _logger.info(f"Created Google Calendar event: {created_event['id']}")
        return created_event['id']
    
    def update_event(self, event_id, event_data):
        """Update a Google Calendar event.
        
        Args:
            event_id (str): Event ID
            event_data (dict): Updated event data
            
        Returns:
            bool: Success status
        """
        service = self._get_service()
        calendar_id = 'primary'
        
        # Get existing event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Update fields
        event['summary'] = event_data.get('summary', event.get('summary'))
        event['description'] = event_data.get('description', event.get('description'))
        
        if 'start' in event_data:
            event['start'] = {
                'dateTime': self._format_datetime(event_data['start']),
                'timeZone': 'UTC',
            }
        
        if 'end' in event_data:
            event['end'] = {
                'dateTime': self._format_datetime(event_data['end']),
                'timeZone': 'UTC',
            }
        
        if 'location' in event_data:
            event['location'] = event_data['location']
        
        if 'attendees' in event_data:
            event['attendees'] = event_data['attendees']
        
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        _logger.info(f"Updated Google Calendar event: {event_id}")
        return True
    
    def cancel_event(self, event_id):
        """Cancel/delete a Google Calendar event.
        
        Args:
            event_id (str): Event ID
            
        Returns:
            bool: Success status
        """
        service = self._get_service()
        calendar_id = 'primary'
        
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        
        _logger.info(f"Deleted Google Calendar event: {event_id}")
        return True
    
    def get_event(self, event_id):
        """Get event details from Google Calendar.
        
        Args:
            event_id (str): Event ID
            
        Returns:
            dict: Event details
        """
        service = self._get_service()
        calendar_id = 'primary'
        
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        return {
            'id': event['id'],
            'summary': event.get('summary', ''),
            'description': event.get('description', ''),
            'start': self._parse_datetime(event['start'].get('dateTime', event['start'].get('date'))),
            'end': self._parse_datetime(event['end'].get('dateTime', event['end'].get('date'))),
            'location': event.get('location', ''),
            'attendees': event.get('attendees', []),
            'status': event.get('status', ''),
        }
    
    def setup_webhook(self, webhook_url, calendar_id=None):
        """Setup Google Calendar webhook (push notification).
        
        Args:
            webhook_url (str): Webhook URL
            calendar_id (str): Calendar ID to watch
            
        Returns:
            dict: Webhook configuration
        """
        service = self._get_service()
        calendar_id = calendar_id or 'primary'
        
        import uuid
        channel_id = str(uuid.uuid4())
        
        body = {
            'id': channel_id,
            'type': 'web_hook',
            'address': webhook_url,
            'token': self.config.webhook_secret,
        }
        
        watch_response = service.events().watch(calendarId=calendar_id, body=body).execute()
        
        # Parse expiration
        expiration_ms = int(watch_response['expiration'])
        expiration = datetime.fromtimestamp(expiration_ms / 1000.0)
        
        return {
            'channel_id': watch_response['id'],
            'resource_id': watch_response['resourceId'],
            'expiration': expiration,
        }
    
    def stop_webhook(self, channel_id):
        """Stop Google Calendar webhook.
        
        Args:
            channel_id (str): Channel ID
            
        Returns:
            bool: Success status
        """
        service = self._get_service()
        
        body = {
            'id': channel_id,
            'resourceId': self.config.webhook_resource_id,
        }
        
        service.channels().stop(body=body).execute()
        
        _logger.info(f"Stopped webhook channel: {channel_id}")
        return True
    
    def process_webhook(self, webhook_data):
        """Process Google Calendar webhook notification.
        
        Args:
            webhook_data (dict): Webhook data
            
        Returns:
            dict: Processed event data
        """
        # Google sends webhook headers, not detailed event data
        # We need to sync the calendar to get actual changes
        resource_id = webhook_data.get('resource_id')
        resource_state = webhook_data.get('resource_state')
        
        _logger.info(f"Processing Google Calendar webhook: {resource_state}")
        
        # Sync calendar changes
        # This is a simplified version - in production you'd want to:
        # 1. Get the sync token
        # 2. Fetch only changed events
        # 3. Update corresponding Odoo appointments
        
        return {
            'resource_id': resource_id,
            'state': resource_state,
        }
    
    def validate_webhook_signature(self, payload, signature, secret):
        """Validate Google Calendar webhook.
        
        Google uses a token in the webhook request instead of signature.
        
        Args:
            payload (bytes): Payload
            signature (str): Token from header
            secret (str): Expected token
            
        Returns:
            bool: Valid status
        """
        return signature == secret
