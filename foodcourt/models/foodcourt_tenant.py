"""Food Court Tenant/Vendor Management."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FoodcourtTenant(models.Model):
    """Represents a food vendor (tenant) operating within the food court.

    Manages the full tenant lifecycle from draft through active operation
    to suspension or termination. Tracks contract dates, revenue share
    percentage, and provides computed fields for menu item count, order
    count, and total revenue.
    """

    _name = 'foodcourt.tenant'
    _description = 'Food Court Tenant/Vendor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(
        string='Tenant Name',
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string='Tenant Code',
        readonly=True,
        copy=False,
        default='New',
        help="Auto-generated tenant code.",
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Related Contact',
        ondelete='restrict',
        tracking=True,
        help="Linked contact record for this tenant.",
    )
    image = fields.Image(
        string='Tenant Logo',
        max_width=256,
        max_height=256,
    )
    cuisine_type = fields.Selection(
        selection=[
            ('indonesian', 'Indonesian'),
            ('chinese', 'Chinese'),
            ('japanese', 'Japanese'),
            ('western', 'Western'),
            ('korean', 'Korean'),
            ('beverages', 'Beverages'),
            ('dessert', 'Dessert'),
            ('snacks', 'Snacks'),
            ('other', 'Other'),
        ],
        string='Cuisine Type',
        tracking=True,
    )
    stall_id = fields.Many2one(
        comodel_name='foodcourt.stall',
        string='Assigned Stall',
        ondelete='set null',
        tracking=True,
        check_company=True,
    )
    phone = fields.Char(
        string='Phone',
    )
    email = fields.Char(
        string='Email',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('terminated', 'Terminated'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    contract_start = fields.Date(
        string='Contract Start Date',
        tracking=True,
    )
    contract_end = fields.Date(
        string='Contract End Date',
        tracking=True,
    )
    revenue_share_pct = fields.Float(
        string='Revenue Share (%)',
        help="Percentage of revenue shared with the food court management.",
        tracking=True,
    )
    menu_item_ids = fields.One2many(
        comodel_name='foodcourt.menu.item',
        inverse_name='tenant_id',
        string='Menu Items',
    )
    order_line_ids = fields.One2many(
        comodel_name='foodcourt.order.line',
        inverse_name='tenant_id',
        string='Order Lines',
    )
    menu_count = fields.Integer(
        string='Menu Items',
        compute='_compute_menu_count',
    )
    order_count = fields.Integer(
        string='Orders',
        compute='_compute_order_count',
    )
    total_revenue = fields.Float(
        string='Total Revenue',
        compute='_compute_total_revenue',
        digits='Product Price',
        help="Total revenue from confirmed (done) orders.",
    )
    description = fields.Text(
        string='Description',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        precompute=True,
        readonly=True,
    )

    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'The tenant code must be unique per company.',
    )

    # ------------------------------------------------------------------
    # Python constraints
    # ------------------------------------------------------------------

    @api.constrains('revenue_share_pct')
    def _check_revenue_share_pct(self):
        """Ensure revenue share percentage is between 0 and 100."""
        for tenant in self:
            if tenant.revenue_share_pct < 0 or tenant.revenue_share_pct > 100:
                raise ValidationError(
                    "Revenue share percentage must be between 0 and 100."
                )

    @api.constrains('contract_start', 'contract_end')
    def _check_contract_dates(self):
        """Ensure contract end date is not before the start date."""
        for tenant in self:
            if (
                tenant.contract_start
                and tenant.contract_end
                and tenant.contract_end < tenant.contract_start
            ):
                raise ValidationError(
                    "Contract end date must be equal to or after the start date."
                )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('menu_item_ids')
    def _compute_menu_count(self):
        """Count menu items belonging to this tenant."""
        for tenant in self:
            tenant.menu_count = len(tenant.menu_item_ids)

    @api.depends('order_line_ids')
    def _compute_order_count(self):
        """Count order lines belonging to this tenant."""
        for tenant in self:
            tenant.order_count = len(tenant.order_line_ids)

    @api.depends('order_line_ids.subtotal', 'order_line_ids.order_id.state')
    def _compute_total_revenue(self):
        """Sum subtotals of order lines whose parent order state is 'done'."""
        for tenant in self:
            done_lines = tenant.order_line_ids.filtered(
                lambda l: l.order_id.state == 'done'
            )
            tenant.total_revenue = sum(done_lines.mapped('subtotal'))

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate tenant code from sequence on creation."""
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'foodcourt.tenant'
                ) or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Action methods
    # ------------------------------------------------------------------

    def action_activate(self):
        """Transition tenant to 'active' state."""
        self.write({'state': 'active'})

    def action_suspend(self):
        """Transition tenant to 'suspended' state."""
        self.write({'state': 'suspended'})

    def action_terminate(self):
        """Transition tenant to 'terminated' state."""
        self.write({'state': 'terminated'})

    def action_reset_draft(self):
        """Reset tenant back to 'draft' state."""
        self.write({'state': 'draft'})

    def action_view_menu_items(self):
        """Open list of menu items for this tenant."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Menu Items',
            'res_model': 'foodcourt.menu.item',
            'view_mode': 'list,kanban,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }

    def action_view_orders(self):
        """Open list of order lines for this tenant."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Order Lines',
            'res_model': 'foodcourt.order.line',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }
