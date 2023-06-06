# -*- coding: utf-8 -*-
{
    'name': "Account Report Difference NIIF-Colgaap",

    'description': """
        The purpose of the module is to create a report to see the IFRS
        differences - Colgaap
    """,

    'author': "Bits Americas",
    'website': "https://www.bitsamericas.com/",
    'category': 'Accounting',
    'version': '13.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['account_reports', 'account_journal_niif'],

    # always loaded
    'data': [
        'data/difference_niif_colgap.xml',
        'views/difference_niif_colgap_template.xml',
        'views/search_template_view.xml',
        'views/account_report_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_report_difference_niif_colgap/'\
            'static/src/js/account_report_accounts.js',
        ],
    },
    'installable': True,
}