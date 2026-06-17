"""Food Court Order Management."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FoodcourtOrder(models.Model):
    """Central order entity aggregating order lines from one or more tenants.

    Handles the complete order lifecycle from *draft* through *confirmed*,
    *preparing*, *ready*, *served*, and *done* (or *cancelled*).  Financial
    totals (subtotal, tax, grand total) are computed and stored for
    efficient reporting.  Payment tracking is integrated so the order
    knows its paid / due amounts at all times.
    """

    _name = 'foodcourt.order'
    _description = 'Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'order_date desc'

    # ------------------------------------------------------------------
    # Selection values
    # ------------------------------------------------------------------

    ORDER_STATES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]

    ORDER_TYPES = [
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
    ]

    PAYMENT_STATES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ]

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string='Order Reference',
        readonly=True,
        copy=False,
        default='New',
        help="Auto-generated order reference (ORD/YYYY/XXXXX).",
    )
    reservation_id = fields.Many2one(
        comodel_name='foodcourt.reservation',
        string='Reservation',
        index=True,
        help="Related reservation, if any.",
    )
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        index=True,
    )
    customer_name = fields.Char(
        string='Customer Name',
    )
    table_id = fields.Many2one(
        comodel_name='foodcourt.table',
        string='Table',
        index=True,
    )
    order_date = fields.Datetime(
        string='Order Date',
        default=fields.Datetime.now,
        required=True,
    )
    order_type = fields.Selection(
        selection=ORDER_TYPES,
        string='Order Type',
        default='dine_in',
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name='foodcourt.order.line',
        inverse_name='order_id',
        string='Order Lines',
    )
    state = fields.Selection(
        selection=ORDER_STATES,
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )

    # -- Financial fields --
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_amounts',
        store=True,
        digits=(12, 2),
    )
    tax_pct = fields.Float(
        string='Tax (%)',
        default=11.0,
        help="Tax percentage (PPN Indonesia default 11%).",
    )
    tax_amount = fields.Float(
        string='Tax Amount',
        compute='_compute_amounts',
        store=True,
        digits=(12, 2),
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        digits=(12, 2),
    )

    # -- Payment tracking --
    payment_ids = fields.One2many(
        comodel_name='foodcourt.payment',
        inverse_name='order_id',
        string='Payments',
    )
    amount_paid = fields.Float(
        string='Amount Paid',
        compute='_compute_payment',
        store=True,
        digits=(12, 2),
    )
    amount_due = fields.Float(
        string='Amount Due',
        compute='_compute_payment',
        store=True,
        digits=(12, 2),
    )
    payment_state = fields.Selection(
        selection=PAYMENT_STATES,
        string='Payment Status',
        compute='_compute_payment',
        store=True,
    )

    notes = fields.Text(
        string='Notes',
    )

    # -- Multi-company / currency --
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('line_ids.subtotal', 'tax_pct')
    def _compute_amounts(self):
        """Compute subtotal, tax amount, and grand total from order lines."""
        for order in self:
            subtotal = sum(order.line_ids.mapped('subtotal'))
            tax_amount = subtotal * (order.tax_pct or 0.0) / 100.0
            order.subtotal = subtotal
            order.tax_amount = tax_amount
            order.total_amount = subtotal + tax_amount

    @api.depends('payment_ids.amount', 'payment_ids.state', 'total_amount')
    def _compute_payment(self):
        """Derive paid / due amounts and payment status from linked payments."""
        for order in self:
            confirmed_payments = order.payment_ids.filtered(
                lambda p: p.state == 'confirmed'
            )
            amount_paid = sum(confirmed_payments.mapped('amount'))
            order.amount_paid = amount_paid
            order.amount_due = order.total_amount - amount_paid
            if amount_paid <= 0:
                order.payment_state = 'unpaid'
            elif amount_paid < order.total_amount:
                order.payment_state = 'partial'
            else:
                order.payment_state = 'paid'

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the order sequence on creation."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'foodcourt.order'
                ) or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State-transition actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Validate the order has at least one line and confirm it."""
        for order in self:
            if not order.line_ids:
                raise UserError(
                    _("You cannot confirm an order without any order lines.")
                )
            order.state = 'confirmed'

    def action_prepare(self):
        """Move the order into the preparing state."""
        self.write({'state': 'preparing'})

    def action_ready(self):
        """Mark the order as ready for pickup / serving."""
        self.write({'state': 'ready'})

    def action_serve(self):
        """Mark the order as served to the customer."""
        self.write({'state': 'served'})

    def action_done(self):
        """Close the order.  Payment must be complete before closing."""
        for order in self:
            if order.payment_state != 'paid':
                raise UserError(
                    _("The order cannot be completed until the full amount "
                      "has been paid.  Amount due: %s", order.amount_due)
                )
            order.state = 'done'

    def action_cancel(self):
        """Cancel the order."""
        self.write({'state': 'cancelled'})
