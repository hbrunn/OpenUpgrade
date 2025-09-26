# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def _ir_actions_act_window_target(env):
    """
    selection value 'inline' was removed, map to 'current'
    """
    openupgrade.logged_query(
        env.cr,
        "UPDATE ir_act_window SET target='current' WHERE target='inline'",
    )


def _ir_actions_server_child_ids(env):
    """
    Field was changed from m2m to o2m - set parent_id from m2m table,
    """
    # TODO: handle case where a v18 child has multiple parents?
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_act_server SET parent_id=rel_server_actions.server_id
        FROM rel_server_actions
        WHERE rel_server_actions.action_id=ir_act_server.id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _ir_actions_act_window_target(env)
    _ir_actions_server_child_ids(env)
