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

