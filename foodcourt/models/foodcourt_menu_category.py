"""Food Court Menu Category Management."""

from odoo import api, fields, models


class FoodcourtMenuCategory(models.Model):
    """Hierarchical categorisation of menu items.

    Supports nested categories through a parent–child relationship backed
    by ``_parent_store`` for efficient tree queries.  Each category may
    carry a small image and exposes a computed count of the menu items
    it contains.
    """

    _name = 'foodcourt.menu.category'
    _description = 'Menu Category'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'
    _order = 'sequence, name'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string='Category Name',
        required=True,
        help="Display name of the menu category.",
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Determines the display order of categories.",
    )
    parent_id = fields.Many2one(
        comodel_name='foodcourt.menu.category',
        string='Parent Category',
        index=True,
        ondelete='cascade',
        help="Parent category for building a hierarchy.",
    )
    parent_path = fields.Char(
        index=True,
        unaccent=False,
    )
    child_ids = fields.One2many(
        comodel_name='foodcourt.menu.category',
        inverse_name='parent_id',
        string='Child Categories',
    )
    image = fields.Image(
        string='Category Image',
        max_width=128,
        max_height=128,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    menu_item_ids = fields.One2many(
        comodel_name='foodcourt.menu.item',
        inverse_name='category_id',
        string='Menu Items',
    )
    item_count = fields.Integer(
        string='Item Count',
        compute='_compute_item_count',
        help="Number of menu items in this category.",
    )

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------

    _sql_constraints = [
        (
            'name_unique',
            'UNIQUE(name)',
            'The category name must be unique.',
        ),
    ]

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('menu_item_ids')
    def _compute_item_count(self):
        """Count the number of menu items belonging to this category."""
        for category in self:
            category.item_count = len(category.menu_item_ids)
