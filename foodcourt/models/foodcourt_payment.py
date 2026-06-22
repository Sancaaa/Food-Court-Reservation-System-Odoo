"""Food Court Payment Processing."""

from odoo import api, fields, models


class FoodcourtPayment(models.Model):
    """Records a payment against an order.

    Supports multiple payment methods common in Indonesian food courts
    (cash, cards, e-wallet, bank transfer, QRIS).  Each payment goes
    through a simple *draft -> confirmed* flow; confirmed payments can
    be refunded if needed.
    """

    _name = 'foodcourt.payment'
    _description = 'Payment'
    _inherit = ['mail.thread']
    _check_company_auto = True
    _order = 'payment_date desc'

    # ------------------------------------------------------------------
    # Selection values
    # ------------------------------------------------------------------

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('debit_card', 'Debit Card'),
        ('credit_card', 'Credit Card'),
        ('ewallet', 'E-Wallet'),
        ('bank_transfer', 'Bank Transfer'),
        ('qris', 'QRIS'),
    ]

    PAYMENT_STATES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('refunded', 'Refunded'),
    ]

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string='Payment Reference',
        readonly=True,
        copy=False,
        default='New',
        help="Auto-generated payment reference (PAY/YYYY/XXXXX).",
    )
    order_id = fields.Many2one(
        comodel_name='foodcourt.order',
        string='Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        related='order_id.customer_id',
        store=True,
        precompute=True,
    )
    amount = fields.Float(
        string='Amount',
        required=True,
    )
    payment_method = fields.Selection(
        selection=PAYMENT_METHODS,
        string='Payment Method',
        required=True,
        default='cash',
    )
    payment_date = fields.Datetime(
        string='Payment Date',
        default=fields.Datetime.now,
        required=True,
    )
    state = fields.Selection(
        selection=PAYMENT_STATES,
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    reference = fields.Char(
        string='External Reference',
        help="External transaction or reference number.",
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

    _amount_positive = models.Constraint(
        'CHECK(amount > 0)',
        'The payment amount must be greater than zero.',
    )

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the payment sequence on creation."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'foodcourt.payment'
                ) or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State-transition actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Confirm the payment."""
        self.write({'state': 'confirmed'})

    def action_refund(self):
        """Mark the payment as refunded."""
        self.write({'state': 'refunded'})
