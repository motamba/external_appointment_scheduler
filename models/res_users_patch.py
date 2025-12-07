# -*- coding: utf-8 -*-
from odoo import models, api


class ResUsersPatch(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        # Accept legacy key 'groups_id' used by some tests and translate
        normalized = []
        for vals in vals_list:
            if isinstance(vals, dict) and 'groups_id' in vals and 'group_ids' not in vals:
                v = vals.copy()
                # Map legacy test key 'groups_id' -> actual field 'group_ids'
                v['group_ids'] = v.pop('groups_id')
                normalized.append(v)
            else:
                normalized.append(vals)
        return super(ResUsersPatch, self).create(normalized)
