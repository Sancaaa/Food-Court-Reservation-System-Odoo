"""Product Template extension for Food Court tenant assignment."""

from odoo import fields, models


class ProductTemplate(models.Model):
    """Add tenant_id to product.template so each product (menu item)
    can be associated with a specific food court tenant."""

    _inherit = 'product.template'

    tenant_id = fields.Many2one(
        comodel_name='foodcourt.tenant',
        string='Tenant',
        ondelete='set null',
        index=True,
        help="The food court tenant that offers this product.",
    )
