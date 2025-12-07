# -*- coding: utf-8 -*-

"""Adapter package exports and a lazy-loading factory helper.

We avoid importing provider-specific adapters at package import time to
prevent circular import issues during module initialization. Adapters
are imported lazily inside `get_adapter`.
"""

__all__ = ["get_adapter"]


def get_adapter(config):
	"""Return an adapter instance for the given `external.calendar.config` record.

	Args:
		config: external.calendar.config record

	Returns:
		adapter instance
	"""
	if not config:
		raise ValueError('Configuration is required')

	provider = getattr(config, 'provider', None)
	if provider == 'google':
		# Import provider adapter lazily to avoid circular imports
		from .google_adapter import GoogleCalendarAdapter
		return GoogleCalendarAdapter(config)

	raise ValueError(f"Unsupported provider: {provider}")
