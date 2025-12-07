# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Pre-migration script to handle provider field type change.
    
    This script removes problematic field selections metadata before
    the module update proceeds, preventing AttributeError during migration.
    """
    # Delete any selection values for the provider field to avoid conflicts
    # when migrating from Char to Selection field type
    cr.execute("""
        DELETE FROM ir_model_fields_selection 
        WHERE field_id IN (
            SELECT id FROM ir_model_fields 
            WHERE model = 'external.calendar.config' 
            AND name = 'provider'
        )
    """)
    
    # Also clean up any orphaned field data
    cr.execute("""
        UPDATE ir_model_fields 
        SET ttype = 'selection'
        WHERE model = 'external.calendar.config' 
        AND name = 'provider'
        AND ttype = 'char'
    """)
