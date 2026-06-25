"""Restaurant Table extension for Food Court reservation state tracking."""

from odoo import fields, models


class RestaurantTable(models.Model):
    """Add a state field and reservation link to restaurant.table for
    backend reservation management.  The native POS table model does
    not carry a stored state — this extension adds one so the backend
    reservation workflow can track table availability."""

    _inherit = 'restaurant.table'

    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('reserved', 'Reserved'),
            ('occupied', 'Occupied'),
        ],
        string='Status',
        default='available',
        required=True,
        tracking=True,
        help="Current reservation status of this table.",
    )
    reservation_ids = fields.Many2many(
        comodel_name='foodcourt.reservation',
        relation='foodcourt_reservation_table_rel',
        column1='table_id',
        column2='reservation_id',
        string='Reservations',
    )

    # ------------------------------------------------------------------
    # Action methods
    # ------------------------------------------------------------------

    def action_set_available(self):
        """Set the table state to 'available'."""
        self.write({'state': 'available'})

    def action_set_reserved(self):
        """Set the table state to 'reserved'."""
        self.write({'state': 'reserved'})

    def action_set_occupied(self):
        """Set the table state to 'occupied'."""
        self.write({'state': 'occupied'})
