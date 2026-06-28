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
    reservation_line_ids = fields.One2many(
        comodel_name='foodcourt.reservation.line',
        inverse_name='reservation_id',
        string='Food Orders',
    )
    amount_total = fields.Float(
        string='Total Amount',
        compute='_compute_amount_total',
        store=True,
    )
    is_paid_online = fields.Boolean(
        string='Paid Online',
        default=False,
        tracking=True,
        help="Indicates if the reservation food orders have been paid online via payment gateway.",
    )
    payment_reference = fields.Char(
        string='Payment Reference',
        tracking=True,
        help="Transaction ID from the payment gateway.",
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

    @api.depends('reservation_line_ids.price_subtotal')
    def _compute_amount_total(self):
        """Calculate the total amount for food orders."""
        for reservation in self:
            reservation.amount_total = sum(
                reservation.reservation_line_ids.mapped('price_subtotal')
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
        """Mark the guest as checked in, set tables to occupied, and create POS Order if needed."""
        for reservation in self:
            reservation.state = 'checked_in'
            reservation.table_ids.write({'state': 'occupied'})
            
            if reservation.reservation_line_ids:
                reservation._create_pos_order_from_reservation()

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

    def _create_pos_order_from_reservation(self):
        """Create a POS Order for the food orders and mark paid if is_paid_online."""
        self.ensure_one()
        
        pos_session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
        ], limit=1)
        
        if not pos_session:
            raise UserError(_("No active POS Session found. Please open a POS session before checking in this reservation."))
            
        order_vals = {
            'session_id': pos_session.id,
            'partner_id': self.customer_id.id if self.customer_id else False,
            'lines': [],
            'table_id': self.table_ids[0].id if self.table_ids else False,
            'amount_total': self.amount_total,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'amount_tax': 0.0,
        }
        
        for line in self.reservation_line_ids:
            order_vals['lines'].append((0, 0, {
                'product_id': line.product_id.id,
                'qty': line.quantity,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'price_subtotal_incl': line.price_subtotal,
                'full_product_name': line.product_id.name,
            }))
            
        pos_order = self.env['pos.order'].create(order_vals)
        
        if self.is_paid_online:
            payment_method = self.env['pos.payment.method'].search([
                ('is_cash_count', '=', False)
            ], limit=1)
            
            if payment_method:
                self.env['pos.payment'].create({
                    'pos_order_id': pos_order.id,
                    'amount': pos_order.amount_total,
                    'payment_method_id': payment_method.id,
                    'payment_date': fields.Datetime.now(),
                })
                pos_order.action_pos_order_paid()

    @api.model
    def get_available_tables_api(self, reservation_date_str, time_start, time_end, floor_id=False):
        """Helper function for Next.js to get available tables."""
        res_date = fields.Date.from_string(reservation_date_str)
        domain = [('state', '=', 'available'), ('active', '=', True)]
        if floor_id:
            domain.append(('floor_id', '=', int(floor_id)))

        overlapping = self.search([
            ('reservation_date', '=', res_date),
            ('state', 'in', ['confirmed', 'checked_in']),
            ('time_start', '<', time_end),
            ('time_end', '>', time_start),
        ])
        reserved_table_ids = overlapping.mapped('table_ids').ids
        if reserved_table_ids:
            domain.append(('id', 'not in', reserved_table_ids))

        tables = self.env['restaurant.table'].search_read(domain, ['id', 'name', 'floor_id', 'seats'])
        return tables


class FoodcourtReservationLine(models.Model):
    """Food orders associated with a reservation."""

    _name = 'foodcourt.reservation.line'
    _description = 'Reservation Food Order Line'

    reservation_id = fields.Many2one(
        comodel_name='foodcourt.reservation',
        string='Reservation',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain="[('available_in_pos', '=', True)]",
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
    )
    price_unit = fields.Float(
        string='Unit Price',
        related='product_id.list_price',
        readonly=True,
        store=True,
    )
    price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_price_subtotal',
        store=True,
    )
    tenant_id = fields.Many2one(
        comodel_name='foodcourt.tenant',
        related='product_id.product_tmpl_id.tenant_id',
        string='Tenant',
        store=True,
    )
    stall_id = fields.Many2one(
        comodel_name='foodcourt.stall',
        related='product_id.product_tmpl_id.stall_id',
        string='Stall',
        store=True,
    )

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
