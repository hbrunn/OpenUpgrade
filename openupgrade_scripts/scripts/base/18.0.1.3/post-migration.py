# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade, openupgrade_180


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "base", "18.0.1.3/noupdate_changes.xml")
    openupgrade_180.convert_company_dependent(env, "res.partner", "barcode")
