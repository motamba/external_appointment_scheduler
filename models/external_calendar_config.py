# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import secrets
import logging

_logger = logging.getLogger(__name__)


class ExternalCalendarConfig(models.Model):
    _name = 'external.calendar.config'
    _description = 'External Calendar Provider Configuration'
    _order = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='A friendly name for this calendar configuration'
    )
    
    provider = fields.Selection(
        selection='_get_provider_selection',
        string='Provider',
        required=True,
        help='The external calendar provider'
    )
    
    def _get_provider_selection(self):
        """Return available provider options. Override to add custom providers."""
        return [
            ('google', 'Google Calendar'),
            ('calendly', 'Calendly'),
        ]
    
    active = fields.Boolean(
        string='Active',
        default=True
    )

    is_active = fields.Boolean(
        string='Is Active',
        default=False,
        help='Indicates if this configuration is the active one for its provider'
    )
    
    # OAuth/API credentials
    client_id = fields.Char(
        string='Client ID',
        help='OAuth Client ID from provider'
    )
    
    client_secret = fields.Char(
        string='Client Secret',
        help='OAuth Client Secret from provider (stored securely)'
    )
    
    api_key = fields.Char(
        string='API Key',
        help='API Key for providers that use API key authentication'
    )
    
    # Connection status
    is_connected = fields.Boolean(
        string='Connected',
        compute='_compute_is_connected',
        store=False
    )

    connection_status = fields.Selection([
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected'),
        ('error', 'Error')
    ], string='Connection Status', compute='_compute_connection_status', store=False)
    
    last_sync_date = fields.Datetime(
        string='Last Sync',
        readonly=True,
        help='Last time data was synced with provider'
    )
    
    sync_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('pending', 'Pending')
    ], 
        string='Sync Status',
        readonly=True
    )
    
    sync_message = fields.Text(
        string='Sync Message',
        readonly=True,
        help='Last sync status message or error'
    )
    
    # Webhook configuration
    webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_webhook_url',
        store=False,
        help='URL to configure in provider for receiving webhooks'
    )
    
    webhook_secret = fields.Char(
        string='Webhook Secret',
        default=lambda self: secrets.token_urlsafe(32),
        copy=False,
        help='Secret token for validating webhook requests'
    )
    
    webhook_channel_id = fields.Char(
        string='Webhook Channel ID',
        help='Channel ID for provider webhook subscription'
    )
    
    webhook_resource_id = fields.Char(
        string='Webhook Resource ID',
        help='Resource ID for provider webhook subscription'
    )
    
    webhook_expiration = fields.Datetime(
        string='Webhook Expiration',
        help='When the webhook subscription expires'
    )
    
    # Default calendar settings
    default_calendar_id = fields.Char(
        string='Default Calendar ID',
        help='Default calendar ID to use for appointments'
    )

    calendar_id = fields.Char(
        string='Calendar ID',
        default='primary',
        help='Default calendar ID (used by tests and adapters)'
    )
    
    # Token relation
    token_ids = fields.One2many(
        'external.calendar.token',
        'config_id',
        string='OAuth Tokens'
    )
    
    has_valid_token = fields.Boolean(
        string='Has Valid Token',
        compute='_compute_has_valid_token',
        store=False
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.constrains('name', 'company_id')
    def _check_unique_name_per_company(self):
        """Ensure configuration name is unique per company."""
        for rec in self:
            if not rec.name:
                continue
            domain = [
                ('id', '!=', rec.id),
                ('name', '=', rec.name),
                ('company_id', '=', rec.company_id.id),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(_('Configuration name must be unique per company!'))
    
    @api.depends('token_ids', 'token_ids.is_expired')
    def _compute_is_connected(self):
        """Check if configuration has valid connection."""
        for config in self:
            config.is_connected = bool(config.token_ids) and any(
                not token.is_expired for token in config.token_ids
            )
    
    @api.depends('token_ids', 'token_ids.is_expired')
    def _compute_has_valid_token(self):
        """Check if configuration has at least one valid token."""
        for config in self:
            config.has_valid_token = any(
                not token.is_expired for token in config.token_ids
            )

    @api.depends('has_valid_token', 'sync_status')
    def _compute_connection_status(self):
        for config in self:
            if config.has_valid_token:
                config.connection_status = 'connected'
            elif config.sync_status == 'error':
                config.connection_status = 'error'
            else:
                config.connection_status = 'not_connected'
    
    @api.depends('provider')
    def _compute_webhook_url(self):
        """Compute the webhook URL for this configuration."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for config in self:
            # Include the config id in the webhook URL so the provider
            # callbacks can be routed to the correct configuration.
            if not base_url:
                config.webhook_url = ''
                continue

            if config.provider == 'google':
                config.webhook_url = f"{base_url}/webhook/calendar/google/{config.id}"
            elif config.provider == 'calendly':
                config.webhook_url = f"{base_url}/webhook/calendar/calendly/{config.id}"
            else:
                config.webhook_url = f"{base_url}/webhook/calendar/{config.provider}/{config.id}"
    
    def action_connect_oauth(self):
        """Initiate OAuth connection flow."""
        self.ensure_one()
        
        if not self.client_id or not self.client_secret:
            raise UserError(_('Please configure Client ID and Client Secret before connecting.'))
        
        # Get the adapter
        adapter = self._get_adapter()
        if not adapter:
            raise UserError(_('Provider adapter not available.'))
        
        # Get authorization URL
        try:
            auth_url = adapter.get_authorization_url()
            
            return {
                'type': 'ir.actions.act_url',
                'url': auth_url,
                'target': 'self',
            }
        except Exception as e:
            _logger.error(f"Failed to get authorization URL: {e}")
            raise UserError(_('Failed to initiate OAuth connection: %s') % str(e))
    
    def action_disconnect(self):
        """Disconnect and revoke OAuth tokens."""
        self.ensure_one()
        
        # Revoke tokens via provider API
        adapter = self._get_adapter()
        if adapter:
            try:
                adapter.revoke_tokens()
            except Exception as e:
                _logger.warning(f"Failed to revoke tokens: {e}")
        
        # Delete local tokens
        self.token_ids.unlink()
        
        self.write({
            'last_sync_date': False,
            'sync_status': False,
            'sync_message': False,
            'webhook_channel_id': False,
            'webhook_resource_id': False,
            'webhook_expiration': False,
        })
        
        return True
    
    def action_test_connection(self):
        """Test the connection to provider."""
        self.ensure_one()
        
        if not self.has_valid_token:
            raise UserError(_('No valid token available. Please connect first.'))
        
        adapter = self._get_adapter()
        if not adapter:
            raise UserError(_('Provider adapter not available.'))
        
        try:
            # Test by fetching calendar list
            result = adapter.test_connection()
            
            self.write({
                'last_sync_date': fields.Datetime.now(),
                'sync_status': 'success',
                'sync_message': _('Connection test successful!')
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Connection to %s is working!') % self.provider,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Connection test failed: {e}")
            self.write({
                'sync_status': 'error',
                'sync_message': str(e)
            })
            raise UserError(_('Connection test failed: %s') % str(e))
    
    def action_setup_webhook(self):
        """Setup webhook subscription with provider."""
        self.ensure_one()
        
        if not self.has_valid_token:
            raise UserError(_('No valid token available. Please connect first.'))
        
        adapter = self._get_adapter()
        if not adapter:
            raise UserError(_('Provider adapter not available.'))
        
        try:
            webhook_data = adapter.setup_webhook(
                webhook_url=self.webhook_url,
                calendar_id=self.default_calendar_id
            )
            
            self.write({
                'webhook_channel_id': webhook_data.get('channel_id'),
                'webhook_resource_id': webhook_data.get('resource_id'),
                'webhook_expiration': webhook_data.get('expiration'),
                'sync_status': 'success',
                'sync_message': _('Webhook configured successfully!')
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Webhook configured successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Webhook setup failed: {e}")
            raise UserError(_('Webhook setup failed: %s') % str(e))
    
    def action_refresh_webhook(self):
        """Refresh webhook subscription before expiration."""
        self.ensure_one()
        
        # First stop existing webhook
        if self.webhook_channel_id:
            try:
                adapter = self._get_adapter()
                if adapter:
                    adapter.stop_webhook(self.webhook_channel_id)
            except Exception as e:
                _logger.warning(f"Failed to stop existing webhook: {e}")
        
        # Setup new webhook
        return self.action_setup_webhook()
    
    def _get_adapter(self):
        """Get the calendar adapter instance for this configuration."""
        # Use the adapter factory to obtain an adapter instance
        from odoo.addons.external_appointment_scheduler.adapters import get_adapter
        try:
            return get_adapter(self)
        except Exception:
            return None
    
    @api.model
    def _cron_refresh_tokens(self):
        """Cron job to refresh expiring OAuth tokens."""
        configs = self.search([('active', '=', True)])
        
        for config in configs:
            if config.has_valid_token:
                try:
                    adapter = config._get_adapter()
                    if adapter:
                        adapter.refresh_token_if_needed()
                        _logger.info(f"Refreshed token for config {config.name}")
                except Exception as e:
                    _logger.error(f"Failed to refresh token for config {config.id}: {e}")
    
    @api.model
    def _cron_refresh_webhooks(self):
        """Cron job to refresh expiring webhooks."""
        # Refresh webhooks that expire in next 24 hours
        cutoff = fields.Datetime.now() + fields.timedelta(hours=24)
        
        configs = self.search([
            ('active', '=', True),
            ('webhook_expiration', '!=', False),
            ('webhook_expiration', '<', cutoff)
        ])
        
        for config in configs:
            try:
                config.action_refresh_webhook()
                _logger.info(f"Refreshed webhook for config {config.name}")
            except Exception as e:
                _logger.error(f"Failed to refresh webhook for config {config.id}: {e}")

    @api.constrains('provider', 'is_active')
    def _check_single_active_per_provider(self):
        """Ensure only one configuration per provider is active at a time."""
        for config in self:
            if config.is_active:
                existing = self.search([
                    ('id', '!=', config.id),
                    ('provider', '=', config.provider),
                    ('is_active', '=', True),
                ])
                if existing:
                    raise ValidationError(_('Only one active configuration per provider is allowed.'))

    def _onchange_is_active(self):
        """Helper called from tests to deactivate other configs when this is activated."""
        for config in self:
            if config.is_active:
                others = self.search([
                    ('id', '!=', config.id),
                    ('provider', '=', config.provider),
                    ('is_active', '=', True),
                ])
                if others:
                    others.write({'is_active': False})

    def write(self, vals):
        """Ensure only one active configuration per provider.

        If a configuration is being activated, automatically deactivate
        any other active configuration for the same provider before
        allowing the write to proceed. This prevents a ValidationError
        during tests that set another config to active.
        """
        # Handle both single-record and multi-record writes
        if 'is_active' in vals and vals.get('is_active'):
            # For each record being activated, deactivate others
            for rec in self:
                # Only act when provider available (avoid None comparisons)
                provider = rec.provider
                if not provider:
                    continue
                others = self.search([
                    ('id', '!=', rec.id),
                    ('provider', '=', provider),
                    ('is_active', '=', True),
                ])
                if others:
                    others.write({'is_active': False})

        return super(ExternalCalendarConfig, self).write(vals)
