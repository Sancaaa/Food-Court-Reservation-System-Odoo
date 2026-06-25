"""Restaurant Floor extension for Food Court stall management."""

from odoo import api, fields, models


class RestaurantFloor(models.Model):
    """Add stall_ids to restaurant.floor so that food court stalls
    can be associated with the native POS restaurant floor."""

    _inherit = 'restaurant.floor'

    stall_ids = fields.One2many(
        comodel_name='foodcourt.stall',
        inverse_name='floor_id',
        string='Stalls',
    )
    stall_count = fields.Integer(
        string='Number of Stalls',
        compute='_compute_stall_count',
        store=True,
        precompute=True,
    )

    @api.depends('stall_ids')
    def _compute_stall_count(self):
        """Count the number of stalls belonging to this floor."""
        for floor in self:
            floor.stall_count = len(floor.stall_ids)
