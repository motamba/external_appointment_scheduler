# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ExternalCalendarToken(models.Model):
    _name = 'external.calendar.token'
    _description = 'OAuth Token Storage'
    _order = 'create_date desc'

    config_id = fields.Many2one(
        'external.calendar.config',
        string='Configuration',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    provider = fields.Selection(
        related='config_id.provider',
        string='Provider',
        readonly=True,
        store=True
    )
    
    # OAuth tokens - these should be encrypted in production
    # For encryption, you can use Odoo's encrypted fields module
    # or implement custom encryption
    access_token = fields.Char(
        string='Access Token',
        required=True,
        help='OAuth access token (should be encrypted)'
    )
    
    refresh_token = fields.Char(
        string='Refresh Token',
        help='OAuth refresh token (should be encrypted)'
    )
    
    token_type = fields.Char(
        string='Token Type',
        default='Bearer'
    )
    
    scope = fields.Char(
        string='Scope',
        help='OAuth scopes granted'
    )
    
    expires_at = fields.Datetime(
        string='Expires At',
        help='When the access token expires'
    )
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=False
    )
    
    # Additional provider-specific data
    metadata = fields.Json(
        string='Metadata',
        help='Additional token metadata from provider'
    )
    
    # Audit fields
    company_id = fields.Many2one(
        related='config_id.company_id',
        string='Company',
        readonly=True,
        store=True
    )
    
    @api.depends('expires_at')
    def _compute_is_expired(self):
        """Check if token is expired or will expire soon."""
        now = fields.Datetime.now()
        # Consider token expired if it expires in less than 5 minutes
        buffer = timedelta(minutes=5)
        
        for token in self:
            if not token.expires_at:
                token.is_expired = False
            else:
                token.is_expired = (token.expires_at - buffer) <= now
    
    def refresh(self):
        """Refresh the access token using the refresh token."""
        self.ensure_one()
        
        if not self.refresh_token:
            _logger.warning(f"No refresh token available for token {self.id}")
            return False
        
        # Get adapter and refresh
        adapter = self.config_id._get_adapter()
        if not adapter:
            _logger.error(f"No adapter available for provider {self.provider}")
            return False
        
        try:
            new_token_data = adapter.refresh_access_token(self.refresh_token)
            
            self.write({
                'access_token': new_token_data['access_token'],
                'expires_at': fields.Datetime.now() + timedelta(seconds=new_token_data.get('expires_in', 3600)),
                'token_type': new_token_data.get('token_type', 'Bearer'),
            })
            
            # Update refresh token if provider sent a new one
            if 'refresh_token' in new_token_data:
                self.refresh_token = new_token_data['refresh_token']
            
            _logger.info(f"Successfully refreshed token {self.id}")
            return True
            
        except Exception as e:
            _logger.error(f"Failed to refresh token {self.id}: {e}")
            return False
    
    def revoke(self):
        """Revoke this token with the provider."""
        self.ensure_one()
        
        adapter = self.config_id._get_adapter()
        if adapter:
            try:
                adapter.revoke_token(self.access_token)
                _logger.info(f"Successfully revoked token {self.id}")
            except Exception as e:
                _logger.warning(f"Failed to revoke token {self.id}: {e}")
        
        # Delete token record
        self.unlink()
    
    @api.model
    def create(self, vals):
        """Override create to ensure only one active token per config."""
        # Deactivate/delete existing tokens for the same config
        if vals.get('config_id'):
            existing_tokens = self.search([('config_id', '=', vals['config_id'])])
            if existing_tokens:
                _logger.info(f"Removing {len(existing_tokens)} existing tokens for config {vals['config_id']}")
                existing_tokens.unlink()
        
        return super(ExternalCalendarToken, self).create(vals)
