"""Food Court Table Management."""

from odoo import api, fields, models


class FoodcourtTable(models.Model):
    """Represents a table or seating area within the food court.

    Each table belongs to a floor and tracks its seating capacity and
    current operational state (available, reserved, occupied, cleaning).
    """

    _name = 'foodcourt.table'
    _description = 'Food Court Table'
    _inherit = ['mail.thread']
    _order = 'floor_id, name'
    _check_company_auto = True

    name = fields.Char(
        string='Table Number',
        required=True,
        tracking=True,
        help="Table number or name, e.g. 'T-01'.",
    )
    floor_id = fields.Many2one(
        comodel_name='foodcourt.floor',
        string='Floor/Area',
        required=True,
        ondelete='restrict',
        tracking=True,
        check_company=True,
    )
    capacity = fields.Integer(
        string='Seating Capacity',
        required=True,
        default=4,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('reserved', 'Reserved'),
            ('occupied', 'Occupied'),
            ('cleaning', 'Cleaning'),
        ],
        string='Status',
        default='available',
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    notes = fields.Text(
        string='Notes',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------

    _sql_constraints = [
        (
            'name_company_uniq',
            'UNIQUE(name, company_id)',
            'The table name must be unique per company.',
        ),
    ]

    # ------------------------------------------------------------------
    # Action methods
    # ------------------------------------------------------------------

    def action_set_available(self):
        """Set the table state to 'available'."""
        self.write({'state': 'available'})

    def action_set_occupied(self):
        """Set the table state to 'occupied'."""
        self.write({'state': 'occupied'})

    def action_set_cleaning(self):
        """Set the table state to 'cleaning'."""
        self.write({'state': 'cleaning'})
