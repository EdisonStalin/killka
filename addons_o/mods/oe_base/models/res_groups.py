# -*- coding: utf-8 -*-

from lxml import etree
from lxml.builder import E

from odoo import models, _
from odoo.addons.base.res.res_users import name_boolean_group, name_selection_groups


class res_groups(models.Model):
    _inherit = 'res.groups'

    # copia del original
    def _update_user_groups_view(self):
        if self._context.get('install_mode'):
            # use installation/admin language for translatable names in the view
            user_context = self.env['res.users'].context_get()
            self = self.with_context(**user_context)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if view and view.exists() and view._name == 'ir.ui.view':
            try:
                group_no_one = [view.env.ref('base.group_no_one'), view.env.ref('oe_base.group_empty')]
            except:
                group_no_one = [view.env.ref('base.group_no_one')]
            xml1, xml2 = [], []
            xml1.append(E.separator(string=_('Application Accesses'), colspan="2"))
            for app, kind, gs in self.get_groups_by_application():
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                attrs = {}
                if app.xml_id in ('base.module_category_hidden', 'base.module_category_extra', 'base.module_category_usability', 'base.module_category_administration', 'oe_base.module_category_oe'):
                    attrs['groups'] = 'base.group_no_one'

                if kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())
                else:
                    # application separator with boolean fields
                    app_name = app.name or _('Other')
                    xml2.append(E.separator(string=app_name, colspan="4", **attrs))
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        if g in group_no_one:
                            # make the group_no_one invisible in the form view
                            xml2.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            xml2.append(E.field(name=field_name, **attrs))

            xml2.append({'class': "o_label_nowrap"})
            xml = E.field(E.group(*(xml1), col="2"), E.group(*(xml2), col="4"), name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")

            new_context = dict(view._context)
            new_context.pop('install_mode_data', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})
