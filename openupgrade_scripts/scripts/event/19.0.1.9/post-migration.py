# Copyright 2026 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def event_question(env):
    """
    Convert event_id, event_type_id to their many2many equivalents
    """
    openupgrade.m2o_to_x2m(
        env.cr, env["event.question"], "event_question", "event_ids", "event_id"
    )
    openupgrade.m2o_to_x2m(
        env.cr,
        env["event.question"],
        "event_question",
        "event_type_ids",
        "event_type_id",
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "event", "19.0.1.9/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "event",
        [
            "event_registration_mail_template_badge",
            "event_reminder",
            "event_subscription",
        ],
        ["body_html"],
    )
    event_question(env)
