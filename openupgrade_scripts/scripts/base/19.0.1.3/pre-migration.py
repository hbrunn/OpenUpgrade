# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.addons.openupgrade_scripts.apriori import merged_modules, renamed_modules


_renamed_xmlids = [
    (
        "base.state_id_pp",
        "base.state_id_pe",
    ),
]

_renamed_fields = [
    (
        'ir.actions.act_window', 'ir_act_window', 'groups_id', 'group_ids',
    ),
    (
        'ir.actions.report', 'ir_act_report_xml', 'groups_id', 'group_ids',
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        f"""
        CREATE TABLE {openupgrade.get_legacy_name("ir_module_module")
            } AS (SELECT name, state FROM ir_module_module);
        """,
    )
    openupgrade.update_module_names(env.cr, renamed_modules.items())
    openupgrade.update_module_names(env.cr, merged_modules.items(), merge_modules=True)
    openupgrade.clean_transient_models(env.cr)
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    openupgrade.rename_fields(env, _renamed_fields)
