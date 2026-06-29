"""POS Order extension to sync table status."""

from odoo import api, fields, models


class PosOrder(models.Model):
    """Sync native POS orders with the custom table status."""

    _inherit = 'pos.order'

    @api.model_create_multi
    def create(self, vals_list):
        """When a POS order is created for a table, mark it occupied."""
        orders = super().create(vals_list)
        for order in orders:
            if order.table_id and order.state == 'draft':
                # Sync table to occupied (handles walk-in customers)
                order.table_id.write({'state': 'occupied'})
        return orders

    def write(self, vals):
        """When a POS order state changes, update the table status accordingly."""
        res = super().write(vals)
        if 'state' in vals:
            for order in self:
                if not order.table_id:
                    continue

                if order.state in ['paid', 'done', 'invoiced', 'cancel']:
                    # Ensure no other draft POS orders exist for this table
                    active_orders = self.env['pos.order'].search_count([
                        ('table_id', '=', order.table_id.id),
                        ('state', '=', 'draft'),
                        ('id', '!=', order.id)
                    ])
                    # Ensure no active checked_in reservations exist
                    active_reservations = self.env['foodcourt.reservation'].search_count([
                        ('table_ids', 'in', [order.table_id.id]),
                        ('state', '=', 'checked_in')
                    ])
                    
                    if active_orders == 0 and active_reservations == 0:
                        order.table_id.write({'state': 'available'})
                        
                elif order.state == 'draft':
                    order.table_id.write({'state': 'occupied'})
                    
        return res
