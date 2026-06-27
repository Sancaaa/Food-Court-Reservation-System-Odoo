"""Food Court Reservation Management."""

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FoodcourtReservation(models.Model):
    """Manages table reservations for the food court.

    Supports walk-in customers (name/phone) as well as registered
    partners.  Provides a full state workflow from *draft* through
    *confirmed*, *checked_in*, and *completed* (or *cancelled* /
    *no_show*).  Table availability is validated before confirmation to
    prevent double-booking.
    """

    _name = 'foodcourt.reservation'
    _description = 'Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reservation_date desc, time_start'

    # ------------------------------------------------------------------
    # Selection values
    # ------------------------------------------------------------------

    STATES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='New',
        help="Auto-generated reservation reference (RES/YYYY/XXXXX).",
    )
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        index=True,
        help="Registered customer. Leave empty for walk-in guests.",
    )
    customer_name = fields.Char(
        string='Customer Name',
        required=True,
        help="Name of the customer (especially useful for walk-in guests).",
    )
    customer_phone = fields.Char(
        string='Phone',
    )
    customer_email = fields.Char(
        string='Email',
    )
    table_ids = fields.Many2many(
        comodel_name='restaurant.table',
        relation='foodcourt_reservation_table_rel',
        column1='reservation_id',
        column2='table_id',
        string='Reserved Tables',
    )
    reservation_date = fields.Date(
        string='Reservation Date',
        required=True,
        tracking=True,
        default=fields.Date.context_today,
        help="Date on which the reservation is made.",
    )
    time_start = fields.Float(
        string='Start Time',
        required=True,
        help="Reservation start time (use the time widget).",
    )
    time_end = fields.Float(
        string='End Time',
        required=True,
        help="Reservation end time (use the time widget).",
    )
    guest_count = fields.Integer(
        string='Number of Guests',
        required=True,
        default=2,
    )
    state = fields.Selection(
        selection=STATES,
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    notes = fields.Text(
        string='Special Requests',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    total_table_capacity = fields.Integer(
        string='Total Table Capacity',
        compute='_compute_total_capacity',
        help="Sum of seating capacities of all reserved tables.",
    )
    # Calendar datetime fields (computed from reservation_date + time_start/end)
    date_start = fields.Datetime(
        string='Start',
        compute='_compute_calendar_dates',
        store=True,
        precompute=True,
    )
    date_stop = fields.Datetime(
        string='End',
        compute='_compute_calendar_dates',
        store=True,
        precompute=True,
    )

    _guest_count_positive = models.Constraint(
        'CHECK(guest_count > 0)',
        'The number of guests must be at least 1.',
    )
    _time_end_after_start = models.Constraint(
        'CHECK(time_end > time_start)',
        'The end time must be after the start time.',
    )

    # ------------------------------------------------------------------
    # Python constraints
    # ------------------------------------------------------------------

    @api.constrains('reservation_date')
    def _check_reservation_date(self):
        """Ensure the reservation date is not in the past (on create)."""
        for record in self:
            # Only enforce the future-date check when creating a record.
            # We use _origin to detect whether the record already existed
            # (an update), so we skip the check and historical records
            # can still be edited.
            if not record._origin and record.reservation_date:
                if record.reservation_date < fields.Date.context_today(self):
                    raise ValidationError(
                        _("The reservation date cannot be in the past.")
                    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('table_ids', 'table_ids.seats')
    def _compute_total_capacity(self):
        """Sum seating capacity of the reserved tables."""
        for reservation in self:
            reservation.total_table_capacity = sum(
                reservation.table_ids.mapped('seats')
            )

    @api.depends('reservation_date', 'time_start', 'time_end')
    def _compute_calendar_dates(self):
        """Convert date + float time into Datetime for calendar view."""
        for reservation in self:
            if reservation.reservation_date:
                start_hour = int(reservation.time_start)
                start_min = int((reservation.time_start % 1) * 60)
                end_hour = int(reservation.time_end)
                end_min = int((reservation.time_end % 1) * 60)
                reservation.date_start = datetime.combine(
                    reservation.reservation_date,
                    datetime.min.time()
                ).replace(hour=start_hour, minute=start_min)
                reservation.date_stop = datetime.combine(
                    reservation.reservation_date,
                    datetime.min.time()
                ).replace(hour=end_hour, minute=end_min)
            else:
                reservation.date_start = False
                reservation.date_stop = False

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the reservation sequence on creation."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'foodcourt.reservation'
                ) or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Business logic helpers
    # ------------------------------------------------------------------

    def _check_table_availability(self):
        """Verify that no overlapping reservations exist for the selected
        tables on the same date and overlapping time window.

        Raises:
            UserError: If one or more tables are already reserved during
                the requested time slot.
        """
        self.ensure_one()
        if not self.table_ids:
            return
        overlapping = self.env['foodcourt.reservation'].search([
            ('id', '!=', self.id),
            ('reservation_date', '=', self.reservation_date),
            ('table_ids', 'in', self.table_ids.ids),
            ('state', 'in', ['confirmed', 'checked_in']),
            ('time_start', '<', self.time_end),
            ('time_end', '>', self.time_start),
        ])
        if overlapping:
            conflicting_tables = overlapping.mapped('table_ids') & self.table_ids
            raise UserError(
                _("The following tables are already reserved during this "
                  "time slot: %s", ', '.join(conflicting_tables.mapped('display_name')))
            )

    # ------------------------------------------------------------------
    # State-transition actions
    # ------------------------------------------------------------------

    def action_confirm(self):
        """Validate table availability and confirm the reservation."""
        for reservation in self:
            reservation._check_table_availability()
            reservation.state = 'confirmed'
            reservation.table_ids.write({'state': 'reserved'})

    def action_check_in(self):
        """Mark the guest as checked in and set tables to occupied."""
        for reservation in self:
            reservation.state = 'checked_in'
            reservation.table_ids.write({'state': 'occupied'})

    def action_complete(self):
        """Complete the reservation and free the tables."""
        for reservation in self:
            reservation.state = 'completed'
            reservation.table_ids.write({'state': 'available'})

    def action_cancel(self):
        """Cancel the reservation and free the tables."""
        for reservation in self:
            reservation.state = 'cancelled'
            if reservation.table_ids:
                reservation.table_ids.write({'state': 'available'})

    def action_no_show(self):
        """Mark the reservation as no-show and free the tables."""
        for reservation in self:
            reservation.state = 'no_show'
            if reservation.table_ids:
                reservation.table_ids.write({'state': 'available'})
