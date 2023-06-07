# -*- coding: utf-8 -*-
{
    'name': "account_report_adjustment",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Uncategorized',
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': [
        'web',
        'account_reports',
        'account_asset'
    ],

    # always loaded
    'data': [
        'views/account_report_view.xml',
        'data/account.report.csv',
        'data/account_assets_report.xml'
    ]
}
