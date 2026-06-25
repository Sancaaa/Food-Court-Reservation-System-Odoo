"""POS Order Line extension for Food Court tenant tracking."""

from odoo import api, fields, models


class PosOrderLine(models.Model):
    """Add a computed tenant_id to pos.order.line derived from the
    product's template tenant assignment.  This enables revenue
    tracking per tenant directly from standard POS order lines."""

    _inherit = 'pos.order.line'

    tenant_id = fields.Many2one(
        comodel_name='foodcourt.tenant',
        string='Tenant',
        compute='_compute_tenant_id',
        store=True,
        precompute=True,
        index=True,
        help="Tenant derived from the product's template.",
    )

    @api.depends('product_id', 'product_id.product_tmpl_id.tenant_id')
    def _compute_tenant_id(self):
        """Resolve the tenant from the product template."""
        for line in self:
            line.tenant_id = line.product_id.product_tmpl_id.tenant_id
