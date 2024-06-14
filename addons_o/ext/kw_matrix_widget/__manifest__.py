{
    'name': 'Matrix widget',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'category': 'Extra Tools',
    'license': 'OPL-1',
    'version': '11.0.1.0.1',

    'depends': [
        'web',
    ],
    'qweb': [
        'static/src/xml/qweb_matrix_template.xml',
    ],
    'data': [
        'template/add_matrix_assets.xml',
    ],

    'installable': True,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
}
