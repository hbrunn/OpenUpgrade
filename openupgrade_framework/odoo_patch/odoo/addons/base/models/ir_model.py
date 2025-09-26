# Copyright Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

from odoo import api, models

from odoo.addons.base.models.ir_model import (
    IrModel,
    IrModelData,
    IrModelFields,
    IrModelRelation,
)


def _drop_table(self):
    """Never drop tables"""
    for model in self:
        if self.env.get(model.model) is not None:
            openupgrade.message(
                self.env.cr,
                "Unknown",
                False,
                False,
                "Not dropping the table or view of model %s",
                model.model,
            )


IrModel._drop_table = _drop_table


def _drop_column(self):
    """Never drop columns"""
    for field in self:
        if field.name in models.MAGIC_COLUMNS:
            continue
        openupgrade.message(
            self.env.cr,
            "Unknown",
            False,
            False,
            "Not dropping the column of field %s of model %s",
            field.name,
            field.model,
        )
        continue


IrModelFields._drop_column = _drop_column


@api.model
def _module_data_uninstall(self, modules_to_remove):
    """To pass context, that the patch in __getitem__ of api.Environment uses"""
    patched_self = self.with_context(**{"missing_model": True})
    return IrModelData._module_data_uninstall._original_method(
        patched_self, modules_to_remove
    )

_module_data_uninstall._original_method = IrModelData._module_data_uninstall
IrModelData._module_data_uninstall = _module_data_uninstall


def _module_data_uninstall(self):
    """Don't delete many2many relation tables. Only unlink the
    ir.model.relation record itself.
    """
    self.unlink()


IrModelRelation._module_data_uninstall = _module_data_uninstall
