from openupgradelib import openupgrade


@openupgrade.migrate(use_env=False)
def migrate(cr, version=None):
    # this xmlid for a view clashes with the xmlid of the new client action
    cr.execute(
        "UPDATE ir_model_data SET name=name || '.delete' "
        "WHERE module='website' AND name='website_configurator'"
    )
    # there's no group_ids any more on website.menu
    cr.execute(
        "UPDATE ir_model_data SET noupdate=False "
        "WHERE module='website' AND name='website_menu'"
    )
