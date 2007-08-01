
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
import netsvc
import pooler
#field name="confirm_en"/>

take_form = """<?xml version="1.0"?>
<form title="Confirm">
	<separator string="Confirmation enable taken away" colspan="4"/>
	<newline/>
</form>
"""

take_fields = {
	'confirm_en': {'string':'Catalog Number', 'type':'integer'},
}
def _start(self,cr,uid,data,context):
	pool = pooler.get_pool(cr.dbname)
	recs=pool.get('auction.lots').browse(cr,uid,data['ids'],context)
	catalog_num=False
	for rec in recs:
		if rec.ach_emp:
			catalog_num= rec and rec.obj_num or False
	return {'confirm_en':catalog_num}


def _confirm_enable(self,cr,uid,data,context={}):
	res={}
	pool = pooler.get_pool(cr.dbname)
	lots=pool.get('auction.lots').browse(cr,uid,data['ids'],context)
	for lot in lots:
		lot_up=pooler.get_pool(cr.dbname).get('auction.lots').write(cr,uid,[lot.id],{'ach_emp':False})
	return {}

class enable_take_away(wizard.interface):
	states = {
		'init' : {
			'actions' : [],
			'result' : {
					'type' : 'form',
				    'arch' : take_form,
				    'fields' : take_fields,
				    'state' : [ ('end', 'Cancel'),('go', 'Enable Taken away')]}
		},
			'go' : {
			'actions' : [_confirm_enable],
			'result' : {'type' : 'state', 'state' : 'end'}
		},
}
enable_take_away('auction.lots.enable')

