"""Food Court Order Line Management."""

from odoo import api, fields, models


class FoodcourtOrderLine(models.Model):
    """Represents a single line item within an order.

    Each line links to a specific menu item from a tenant.  The unit
    price and description are auto-populated from the selected menu
    item via an ``onchange`` handler, and the line subtotal is computed
    and stored for aggregation at the order level.
    """

    _name = 'foodcourt.order.line'
    _description = 'Order Line'
    _order = 'order_id, tenant_id'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    order_id = fields.Many2one(
        comodel_name='foodcourt.order',
        string='Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    tenant_id = fields.Many2one(
        comodel_name='foodcourt.tenant',
        string='Tenant',
        required=True,
        index=True,
        help="The food vendor supplying this item.",
    )
    menu_item_id = fields.Many2one(
        comodel_name='foodcourt.menu.item',
        string='Menu Item',
        required=True,
        index=True,
    )
    name = fields.Char(
        string='Description',
        help="Auto-filled from the selected menu item.",
    )
    quantity = fields.Integer(
        string='Quantity',
        required=True,
        default=1,
    )
    unit_price = fields.Float(
        string='Unit Price',
        required=True,
        digits=(12, 2),
    )
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        digits=(12, 2),
    )
    notes = fields.Text(
        string='Special Instructions',
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('preparing', 'Preparing'),
            ('ready', 'Ready'),
            ('served', 'Served'),
        ],
        string='Status',
        default='pending',
        required=True,
    )

    # -- Related company / currency --
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='order_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='order_id.currency_id',
    )

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------

    _sql_constraints = [
        (
            'quantity_positive',
            'CHECK(quantity > 0)',
            'The quantity must be at least 1.',
        ),
        (
            'unit_price_positive',
            'CHECK(unit_price >= 0)',
            'The unit price must be zero or positive.',
        ),
    ]

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        """Calculate line subtotal as quantity × unit price."""
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    # ------------------------------------------------------------------
    # Onchange handlers
    # ------------------------------------------------------------------

    @api.onchange('menu_item_id')
    def _onchange_menu_item_id(self):
        """Auto-fill tenant, unit price, and description from the menu item."""
        if self.menu_item_id:
            self.tenant_id = self.menu_item_id.tenant_id
            self.unit_price = self.menu_item_id.price
            self.name = self.menu_item_id.name
