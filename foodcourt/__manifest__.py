{
    'name': 'Food Court Reservation System',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'summary': 'Manage food court reservations, tenants, orders, and payments',
    'description': """Food Court Reservation System - ERP Multi Tenant Management
    =====================================================
    * Multi-tenant food vendor management
    * Table and floor plan management
    * Reservation system with availability checking
    * Order management across multiple tenants
    * Payment processing with revenue sharing
    * Comprehensive reporting and analytics
    """,
    'author': 'Kelompok 3 Enter - Amici',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/foodcourt_data.xml',
        'views/foodcourt_floor_views.xml',
        'views/foodcourt_stall_views.xml',
        'views/foodcourt_tenant_views.xml',
        'views/foodcourt_table_views.xml',
        'views/foodcourt_menu_views.xml',
        'views/foodcourt_reservation_views.xml',
        'views/foodcourt_order_views.xml',
        'views/foodcourt_payment_views.xml',
        'views/foodcourt_dashboard_views.xml',
        'views/menu.xml',
        'report/report_reservation.xml',
        'report/report_sales.xml',
        'report/report_revenue.xml',
        'wizard/reservation_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
