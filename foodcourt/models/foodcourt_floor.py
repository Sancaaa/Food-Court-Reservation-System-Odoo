"""Food Court Floor/Area Management."""

from odoo import api, fields, models


class FoodcourtFloor(models.Model):
    """Represents a floor or area within the food court.

    Each floor can contain multiple stalls and tables. Provides computed
    fields for stall count, table count, and total seating capacity to
    give a quick overview of each area's utilisation.
    """

    _name = 'foodcourt.floor'
    _description = 'Food Court Floor/Area'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    name = fields.Char(
        string='Floor/Area Name',
        required=True,
        tracking=True,
        help="Name of the floor or area, e.g. 'Lantai 1', 'Area Outdoor'.",
    )
    code = fields.Char(
        string='Area Code',
        help="Short code identifying this area.",
    )
    description = fields.Text(
        string='Description',
    )
    stall_ids = fields.One2many(
        comodel_name='foodcourt.stall',
        inverse_name='floor_id',
        string='Stalls',
    )
    table_ids = fields.One2many(
        comodel_name='foodcourt.table',
        inverse_name='floor_id',
        string='Tables',
    )
    stall_count = fields.Integer(
        string='Number of Stalls',
        compute='_compute_stall_count',
        store=True,
        precompute=True,
    )
    table_count = fields.Integer(
        string='Number of Tables',
        compute='_compute_table_count',
        store=True,
        precompute=True,
    )
    total_capacity = fields.Integer(
        string='Total Seating Capacity',
        compute='_compute_total_capacity',
        store=True,
        precompute=True,
        help="Sum of seating capacities across all tables on this floor.",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('stall_ids')
    def _compute_stall_count(self):
        """Count the number of stalls belonging to this floor."""
        for floor in self:
            floor.stall_count = len(floor.stall_ids)

    @api.depends('table_ids')
    def _compute_table_count(self):
        """Count the number of tables belonging to this floor."""
        for floor in self:
            floor.table_count = len(floor.table_ids)

    @api.depends('table_ids.capacity')
    def _compute_total_capacity(self):
        """Sum seating capacity of all tables on this floor."""
        for floor in self:
            floor.total_capacity = sum(floor.table_ids.mapped('capacity'))
