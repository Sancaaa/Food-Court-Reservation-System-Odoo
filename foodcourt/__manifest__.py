{
    'name': 'Food Court Reservation System',
    'version': '19.0.2.0.0',
    'category': 'Services',
    'summary': 'Manage food court reservations, tenants, and POS integration',
    'description': """Food Court Reservation System - ERP Multi Tenant Management
    =====================================================
    * Multi-tenant food vendor management
    * Integration with POS Restaurant (floors, tables)
    * Reservation system with availability checking
    * Revenue tracking via POS order lines
    * Comprehensive reporting and analytics
    """,
    'author': 'Kelompok 3 Enter - Amici',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts', 'point_of_sale', 'pos_restaurant'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/foodcourt_data.xml',
        'views/foodcourt_stall_views.xml',
        'views/foodcourt_tenant_views.xml',
        'views/foodcourt_reservation_views.xml',
        'views/foodcourt_dashboard_views.xml',
        'views/product_template_views.xml',
        'views/menu.xml',
        'report/report_reservation.xml',
        'report/report_revenue.xml',
        'wizard/reservation_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
