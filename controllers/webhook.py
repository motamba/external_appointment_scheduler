# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class CalendarWebhookController(http.Controller):
    """Webhook controller for calendar provider notifications."""
    
    @http.route('/webhook/calendar/google/<int:config_id>', type='http', auth='public', methods=['POST'], csrf=False)
    def google_calendar_webhook(self, config_id=None, **kw):
        """Handle Google Calendar webhook notifications.
        
        Google Calendar sends push notifications when calendar changes.
        """
        try:
            # Get headers
            headers = request.httprequest.headers
            channel_id = headers.get('X-Goog-Channel-ID')
            resource_id = headers.get('X-Goog-Resource-ID')
            resource_state = headers.get('X-Goog-Resource-State')
            resource_uri = headers.get('X-Goog-Resource-URI')
            token = headers.get('X-Goog-Channel-Token')
            
            _logger.info(f"Google webhook received: channel={channel_id}, state={resource_state}")
            
            # Prefer to locate config by provided URL parameter (config_id)
            config = None
            if config_id:
                config = request.env['external.calendar.config'].sudo().browse(int(config_id))
            # Fallback to channel lookup if config not found
            if not config or not config.exists():
                config = request.env['external.calendar.config'].sudo().search([
                    ('webhook_channel_id', '=', channel_id)
                ], limit=1)
            
            if not config or not config.exists():
                _logger.warning(f"No configuration found for channel {channel_id} or id {config_id}")
                return "OK"  # Return OK to avoid retries
            
            # Validate token
            if token != config.webhook_secret:
                _logger.warning(f"Invalid webhook token for channel {channel_id}")
                return ("Unauthorized", 401)
            
            # Process based on resource state
            if resource_state == 'sync':
                # Initial sync message
                _logger.info("Google Calendar sync message received")
                
            elif resource_state == 'exists':
                # Calendar has changes
                _logger.info("Google Calendar has changes, triggering sync")
                
                # Trigger sync in background
                request.env['external.appointment'].sudo()._process_google_webhook(config, resource_id)
            
            return "OK"
            
        except Exception as e:
            _logger.error(f"Error processing Google webhook: {e}")
            return "Error", 500
    
    @http.route('/webhook/calendar/calendly/<int:config_id>', type='http', auth='public', methods=['POST'], csrf=False)
    def calendly_webhook(self, config_id=None, **kw):
        """Handle Calendly webhook notifications.
        
        Calendly sends webhooks for various events.
        """
        try:
            # Get payload
            payload = request.httprequest.get_data()
            signature = request.httprequest.headers.get('Calendly-Webhook-Signature')
            
            # Parse JSON payload
            data = json.loads(payload)
            
            _logger.info(f"Calendly webhook received: {data.get('event')}")
            
            # Find configuration by id if provided, otherwise find an active Calendly config
            config = None
            if config_id:
                config = request.env['external.calendar.config'].sudo().browse(int(config_id))
            if not config or not config.exists():
                config = request.env['external.calendar.config'].sudo().search([
                    ('provider', '=', 'calendly'),
                    ('active', '=', True)
                ], limit=1)

            if not config or not config.exists():
                _logger.warning("No active Calendly configuration found")
                return "OK"
            
            # Validate signature (implement actual validation)
            # This is a placeholder - implement actual signature validation
            
            # Process event
            event_type = data.get('event')
            
            if event_type == 'invitee.created':
                # New booking created
                _logger.info("New Calendly booking created")
                # Process booking...
                
            elif event_type == 'invitee.canceled':
                # Booking cancelled
                _logger.info("Calendly booking cancelled")
                # Process cancellation...
            
            return "OK"
            
        except Exception as e:
            _logger.error(f"Error processing Calendly webhook: {e}")
            return "Error", 500
    
    @http.route('/calendar/oauth/callback', type='http', auth='public', methods=['GET'])
    def oauth_callback(self, code=None, state=None, error=None, **kw):
        """OAuth callback handler for calendar providers.
        
        Args:
            code (str): Authorization code
            state (str): State parameter
            error (str): Error message (if any)
        """
        if error:
            _logger.error(f"OAuth error: {error}")
            return request.render('external_appointment_scheduler.oauth_error', {
                'error': error,
                'error_description': kw.get('error_description', '')
            })
        
        if not code:
            return request.render('external_appointment_scheduler.oauth_error', {
                'error': 'missing_code',
                'error_description': 'Authorization code not received'
            })
        
        try:
            # Find configuration by state
            # The state should contain the config ID (implement secure state management)
            # For now, we'll get the most recent Google config
            config = request.env['external.calendar.config'].sudo().search([
                ('provider', '=', 'google'),
                ('active', '=', True)
            ], order='id desc', limit=1)
            
            if not config:
                raise Exception("No configuration found")
            
            # Get adapter
            adapter = config._get_adapter()
            if not adapter:
                raise Exception("Failed to get adapter")
            
            # Exchange code for token
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = f"{base_url}/calendar/oauth/callback"
            
            token_data = adapter.exchange_code_for_token(code, redirect_uri)
            
            # Update config
            config.write({
                'last_sync_date': request.env['ir.datetime'].now(),
                'sync_status': 'success',
                'sync_message': 'Successfully connected to Google Calendar'
            })
            
            return request.render('external_appointment_scheduler.oauth_success', {
                'config': config
            })
            
        except Exception as e:
            _logger.error(f"OAuth callback error: {e}")
            return request.render('external_appointment_scheduler.oauth_error', {
                'error': 'exchange_failed',
                'error_description': str(e)
            })
