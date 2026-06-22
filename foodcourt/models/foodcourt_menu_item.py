"""Food Court Menu Item Management."""

from odoo import api, fields, models


class FoodcourtMenuItem(models.Model):
    """Represents a single menu item offered by a tenant.

    Tracks dietary attributes (halal, vegetarian, spicy), pricing,
    estimated preparation time, and availability.  Integrates with
    the mail chatter for change tracking on key fields.
    """

    _name = 'foodcourt.menu.item'
    _description = 'Menu Item'
    _inherit = ['mail.thread']
    _order = 'tenant_id, category_id, name'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string='Item Name',
        required=True,
        tracking=True,
        help="Name of the menu item as displayed to customers.",
    )
    code = fields.Char(
        string='Item Code',
        help="Short internal code for the menu item.",
    )
    tenant_id = fields.Many2one(
        comodel_name='foodcourt.tenant',
        string='Tenant',
        required=True,
        ondelete='cascade',
        index=True,
        help="Tenant (food vendor) that offers this item.",
    )
    category_id = fields.Many2one(
        comodel_name='foodcourt.menu.category',
        string='Category',
        index=True,
        help="Menu category this item belongs to.",
    )
    price = fields.Float(
        string='Price',
        required=True,
        tracking=True,
        help="Selling price for a single unit of this item.",
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of the menu item.",
    )
    image = fields.Image(
        string='Food Image',
        max_width=512,
        max_height=512,
    )

    # -- Dietary / attribute flags --
    is_available = fields.Boolean(
        string='Available',
        default=True,
        help="Uncheck to temporarily mark this item as unavailable.",
    )
    is_halal = fields.Boolean(
        string='Halal Certified',
        default=True,
        help="Indicates whether the item is halal-certified.",
    )
    is_vegetarian = fields.Boolean(
        string='Vegetarian',
        help="Indicates whether the item is vegetarian.",
    )
    is_spicy = fields.Boolean(
        string='Spicy',
        help="Indicates whether the item is spicy.",
    )
    preparation_time = fields.Integer(
        string='Preparation Time (min)',
        default=15,
        help="Estimated preparation time in minutes.",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # -- Multi-company / currency --
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    _price_positive = models.Constraint(
        'CHECK(price >= 0)',
        'The price must be zero or positive.',
    )
    _name_tenant_unique = models.Constraint(
        'UNIQUE(name, tenant_id)',
        'The item name must be unique per tenant.',
    )

