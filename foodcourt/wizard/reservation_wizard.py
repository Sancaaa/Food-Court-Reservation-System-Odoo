from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command


class ReservationWizard(models.TransientModel):
    _name = 'foodcourt.reservation.wizard'
    _description = 'Quick Reservation Wizard'

    customer_name = fields.Char(string='Customer Name', required=True)
    customer_phone = fields.Char(string='Phone')
    customer_email = fields.Char(string='Email')
    customer_id = fields.Many2one('res.partner', string='Existing Customer')
    reservation_date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today)
    time_start = fields.Float(string='Start Time', required=True, default=12.0)
    time_end = fields.Float(string='End Time', required=True, default=13.0)
    guest_count = fields.Integer(string='Number of Guests', required=True, default=2)
    floor_id = fields.Many2one('foodcourt.floor', string='Floor/Area')
    table_ids = fields.Many2many(
        'foodcourt.table', string='Tables',
        domain="[('state', '=', 'available')]")
    notes = fields.Text(string='Special Requests')
    available_table_ids = fields.Many2many(
        'foodcourt.table', 'wizard_available_table_rel',
        string='Available Tables', compute='_compute_available_tables')

    @api.depends('reservation_date', 'time_start', 'time_end', 'floor_id')
    def _compute_available_tables(self):
        for wizard in self:
            domain = [('state', '=', 'available'), ('active', '=', True)]
            if wizard.floor_id:
                domain.append(('floor_id', '=', wizard.floor_id.id))
            
            # Find tables not reserved at this time
            if wizard.reservation_date and wizard.time_start and wizard.time_end:
                overlapping = self.env['foodcourt.reservation'].search([
                    ('reservation_date', '=', wizard.reservation_date),
                    ('state', 'in', ['confirmed', 'checked_in']),
                    ('time_start', '<', wizard.time_end),
                    ('time_end', '>', wizard.time_start),
                ])
                reserved_table_ids = overlapping.mapped('table_ids').ids
                if reserved_table_ids:
                    domain.append(('id', 'not in', reserved_table_ids))
            
            wizard.available_table_ids = self.env['foodcourt.table'].search(domain)

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        if self.customer_id:
            self.customer_name = self.customer_id.name
            self.customer_phone = self.customer_id.phone
            self.customer_email = self.customer_id.email

    def action_create_reservation(self):
        self.ensure_one()
        if not self.table_ids:
            raise ValidationError('Please select at least one table.')
        
        reservation = self.env['foodcourt.reservation'].create({
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'customer_id': self.customer_id.id if self.customer_id else False,
            'reservation_date': self.reservation_date,
            'time_start': self.time_start,
            'time_end': self.time_end,
            'guest_count': self.guest_count,
            'table_ids': [Command.set(self.table_ids.ids)],
            'notes': self.notes,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'foodcourt.reservation',
            'res_id': reservation.id,
            'view_mode': 'form',
            'target': 'current',
        }
