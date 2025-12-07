# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class BaseCalendarAdapter(ABC):
    """Abstract base class for calendar provider adapters.
    
    All calendar provider integrations should extend this class
    and implement the required abstract methods.
    """
    
    def __init__(self, env=None, config=None):
        """Initialize the adapter.

        Supports two calling conventions for backward compatibility with tests
        and other callers:

        - BaseCalendarAdapter(env, config)
        - BaseCalendarAdapter(config)

        If a single record argument is passed, `env` will be extracted from
        the record's `.env` attribute.
        """
        # Allow being called with (config) only
        if config is None and env is not None and hasattr(env, 'env'):
            # `env` is actually a recordset (config)
            config = env
            env = config.env

        self.env = env
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """Validate that configuration has required fields.
        
        Raises:
            ValueError: If required configuration is missing
        """
        if not self.config:
            raise ValueError("Configuration is required")
        if not self.config.active:
            raise ValueError("Configuration is not active")
    
    # ===== Abstract methods that must be implemented =====
    
    @abstractmethod
    def get_authorization_url(self):
        """Get the OAuth authorization URL for user to grant access.
        
        Returns:
            str: Authorization URL to redirect user to
        """
        pass
    
    @abstractmethod
    def exchange_code_for_token(self, code, redirect_uri=None):
        """Exchange authorization code for access token.
        
        Args:
            code (str): Authorization code from OAuth callback
            redirect_uri (str, optional): Redirect URI used in authorization
            
        Returns:
            dict: Token data including access_token, refresh_token, expires_in
        """
        pass
    
    @abstractmethod
    def refresh_access_token(self, refresh_token):
        """Refresh an expired access token.
        
        Args:
            refresh_token (str): The refresh token
            
        Returns:
            dict: New token data
        """
        pass
    
    @abstractmethod
    def revoke_token(self, token):
        """Revoke an access token.
        
        Args:
            token (str): The token to revoke
        """
        pass
    
    @abstractmethod
    def test_connection(self):
        """Test the connection to the provider.
        
        Returns:
            dict: Connection test result
            
        Raises:
            Exception: If connection test fails
        """
        pass
    
    @abstractmethod
    def get_available_slots(self, service, date_from, date_to, constraints):
        """Get available time slots for a service.
        
        Args:
            service: external.appointment.service record
            date_from (datetime): Start date for availability
            date_to (datetime): End date for availability
            constraints (dict): Additional constraints (duration, buffer, calendar_id)
            
        Returns:
            list: List of available slots, each with 'start' and 'end' datetime
        """
        pass
    
    @abstractmethod
    def create_event(self, event_data):
        """Create a calendar event.
        
        Args:
            event_data (dict): Event data including summary, start, end, description, etc.
            
        Returns:
            str: Provider event ID
        """
        pass
    
    @abstractmethod
    def update_event(self, event_id, event_data):
        """Update an existing calendar event.
        
        Args:
            event_id (str): Provider event ID
            event_data (dict): Updated event data
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def cancel_event(self, event_id):
        """Cancel/delete a calendar event.
        
        Args:
            event_id (str): Provider event ID
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def get_event(self, event_id):
        """Get details of a specific event.
        
        Args:
            event_id (str): Provider event ID
            
        Returns:
            dict: Event details
        """
        pass
    
    # ===== Optional methods with default implementations =====
    
    def setup_webhook(self, webhook_url, calendar_id=None):
        """Setup webhook subscription for calendar changes.
        
        Args:
            webhook_url (str): URL to receive webhook notifications
            calendar_id (str, optional): Specific calendar to watch
            
        Returns:
            dict: Webhook configuration (channel_id, resource_id, expiration)
        """
        _logger.warning(f"Webhook setup not implemented for {self.__class__.__name__}")
        return {}
    
    def stop_webhook(self, channel_id):
        """Stop an active webhook subscription.
        
        Args:
            channel_id (str): Webhook channel ID to stop
            
        Returns:
            bool: True if successful
        """
        _logger.warning(f"Webhook stop not implemented for {self.__class__.__name__}")
        return False
    
    def process_webhook(self, webhook_data):
        """Process incoming webhook notification.
        
        Args:
            webhook_data (dict): Webhook payload from provider
            
        Returns:
            dict: Processed event data
        """
        _logger.warning(f"Webhook processing not implemented for {self.__class__.__name__}")
        return {}
    
    def validate_webhook_signature(self, payload, signature, secret):
        """Validate webhook request signature.
        
        Args:
            payload (bytes): Raw webhook payload
            signature (str): Signature from webhook headers
            secret (str): Webhook secret
            
        Returns:
            bool: True if signature is valid
        """
        _logger.warning(f"Webhook signature validation not implemented for {self.__class__.__name__}")
        return False
    
    # ===== Helper methods =====
    
    def _get_valid_token(self):
        """Get a valid access token, refreshing if necessary.
        
        Returns:
            str: Valid access token
            
        Raises:
            Exception: If no valid token available
        """
        if not self.config.token_ids:
            raise Exception("No OAuth token available. Please connect first.")
        
        token = self.config.token_ids[0]
        
        # Refresh if expired
        if token.is_expired:
            _logger.info(f"Token expired, refreshing for config {self.config.id}")
            if not token.refresh():
                raise Exception("Failed to refresh expired token")
        
        return token.access_token


    
    
    def refresh_token_if_needed(self):
        """Refresh token if it's expired or expiring soon.
        
        Returns:
            bool: True if token was refreshed
        """
        if not self.config.token_ids:
            return False
        
        token = self.config.token_ids[0]
        if token.is_expired:
            return token.refresh()
        
        return False
    
    def revoke_tokens(self):
        """Revoke all tokens for this configuration."""
        for token in self.config.token_ids:
            try:
                self.revoke_token(token.access_token)
            except Exception as e:
                _logger.warning(f"Failed to revoke token {token.id}: {e}")
    
    def _generate_time_slots(self, start_date, end_date, duration_minutes, buffer_minutes=0):
        """Generate time slots between two dates.
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            duration_minutes (int): Slot duration in minutes
            buffer_minutes (int): Buffer time after each slot
            
        Returns:
            list: List of time slots with start and end times
        """
        slots = []
        current = start_date
        slot_delta = timedelta(minutes=duration_minutes)
        buffer_delta = timedelta(minutes=buffer_minutes)
        increment = slot_delta + buffer_delta
        
        while current + slot_delta <= end_date:
            slots.append({
                'start': current,
                'end': current + slot_delta,
            })
            current += increment
        
        return slots
    
    def _filter_slots_by_busy_times(self, slots, busy_times):
        """Filter out slots that overlap with busy times.
        
        Args:
            slots (list): List of available slots
            busy_times (list): List of busy periods with start/end times
            
        Returns:
            list: Filtered slots that don't overlap with busy times
        """
        available_slots = []
        
        for slot in slots:
            is_available = True
            slot_start = slot['start']
            slot_end = slot['end']
            
            for busy in busy_times:
                busy_start = busy['start']
                busy_end = busy['end']
                
                # Check for overlap
                if slot_start < busy_end and slot_end > busy_start:
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(slot)
        
        return available_slots
    
    def _parse_datetime(self, dt_string):
        """Parse datetime string from provider API.
        
        Args:
            dt_string (str): Datetime string in ISO format
            
        Returns:
            datetime: Parsed datetime object
        """
        try:
            # Try parsing with timezone info
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            # Fallback to basic parsing
            return datetime.strptime(dt_string[:19], '%Y-%m-%dT%H:%M:%S')
    
    def _format_datetime(self, dt):
        """Format datetime for provider API.
        
        Args:
            dt (datetime): Datetime object
            
        Returns:
            str: Formatted datetime string
        """
        return dt.isoformat()


# Module-level backwards-compatible alias (safe assignment)
try:
    BaseAdapter = BaseCalendarAdapter
except NameError:
    BaseAdapter = None
