"""Food Court Stall/Booth Management."""

from odoo import api, fields, models


class FoodcourtStall(models.Model):
    """Represents a physical stall or booth within the food court.

    A stall belongs to a specific floor and may be assigned to a tenant.
    Tracks rental amount, size, facilities, and current operational state.
    """

    _name = 'foodcourt.stall'
    _description = 'Food Court Stall/Booth'
    _inherit = ['mail.thread']
    _order = 'floor_id, name'
    _check_company_auto = True

    name = fields.Char(
        string='Stall Name',
        required=True,
        tracking=True,
        help="Stall name or number.",
    )
    code = fields.Char(
        string='Stall Code',
    )
    floor_id = fields.Many2one(
        comodel_name='foodcourt.floor',
        string='Floor/Area',
        required=True,
        ondelete='restrict',
        tracking=True,
        check_company=True,
    )
    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('occupied', 'Occupied'),
            ('maintenance', 'Under Maintenance'),
        ],
        string='Status',
        default='available',
        required=True,
        tracking=True,
    )
    tenant_id = fields.Many2one(
        comodel_name='foodcourt.tenant',
        string='Current Tenant',
        ondelete='set null',
        tracking=True,
        check_company=True,
    )
    monthly_rent = fields.Float(
        string='Monthly Rent',
        digits='Product Price',
        help="Monthly rental amount for this stall.",
    )
    size = fields.Float(
        string='Size (sqm)',
        help="Size of the stall in square metres.",
    )
    facilities = fields.Text(
        string='Facilities',
        help="Available facilities in this stall (e.g. water, electricity, gas).",
    )
    notes = fields.Text(
        string='Notes',
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
        readonly=True,
    )
