from openupgradelib import openupgrade


@openupgrade.migrate(use_env=False)
def migrate(cr, version=None):
    # a lot of xmlids clash, this needs some general fixing
    cr.execute("update ir_model_data set name=name||'.delete' where module='l10n_nl'")
