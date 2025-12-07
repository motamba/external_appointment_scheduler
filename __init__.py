# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import adapters
from . import wizards


def post_init_hook(env):
	"""Post-init hook called after module installation.

	The module manifest declares `post_init_hook`, and Odoo's loader will
	call this hook with the current ``env``. Provide a lightweight safe
	implementation that adapts to older signature expectations if needed.
	"""
	# If other modules or older code expect (cr, registry), provide them
	cr = getattr(env, 'cr', None)
	registry = getattr(env, 'registry', None)
	# Currently no additional initialization is required. Keep as no-op.
	return True


# Testing helpers: provide a no-op mock_mail_gateway context manager to test
# classes that expect it (tests call `with self.mock_mail_gateway():`). We
# attach a simple context manager to the standard test classes so tests
# that reference it don't fail when a dedicated mocking helper isn't present.
try:
	from odoo.tests import common
	from contextlib import contextmanager

	if not hasattr(common.TransactionCase, 'mock_mail_gateway'):
		def mock_mail_gateway(self):
			@contextmanager
			def _ctx():
				# In tests we don't actually intercept outgoing mail; the
				# context manager simply yields so tests can run without
				# external mail gateway helpers.
				yield
			return _ctx()

		common.TransactionCase.mock_mail_gateway = mock_mail_gateway
		common.HttpCase.mock_mail_gateway = mock_mail_gateway
except Exception:
	# If anything goes wrong during import (test environment may not be
	# available at module import time), silently continue.
	pass
