# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Sylvain LE GAL
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.openupgrade import openupgrade

xmlid_renames = [
    ('procurement.trans_confirm_mto_purchase', 'purchase.trans_confirm_mto_purchase'),
    ('procurement.act_produce_service', 'project_mrp.act_produce_service'),
    ('procurement.trans_produce_service_cancel', 'project_mrp.trans_produce_service_cancel'),
    ('procurement.trans_produce_service_make_done', 'project_mrp.trans_produce_service_make_done'),
    ('procurement.trans_product_check_produce_service', 'project_mrp.trans_product_check_produce_service'),
]

@openupgrade.migrate()
def migrate(cr, version):
    openupgrade.rename_xmlids(cr, xmlid_renames)
