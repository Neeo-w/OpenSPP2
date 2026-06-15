from . import models


def pre_init_hook(env):
    """Reassign model external IDs that belonged to the defunct alkathiry_tribe module.

    When alkathiry_tribe was installed as a separate module, Odoo registered
    alkathiry.tribe and alkathiry.tribe.position under the 'alkathiry_tribe'
    namespace.  Now that these models live in alkathiry_base, the old external
    IDs must be removed before this module's security CSV is loaded — otherwise
    the CSV lookup for 'model_alkathiry_tribe' fails because Odoo searches for
    'alkathiry_base.model_alkathiry_tribe' and finds nothing.

    Deleting the old entries here causes Odoo to re-register them under
    'alkathiry_base' during the normal model-registration phase that follows.
    """
    defunct = "alkathiry_tribe"
    stale_names = [
        "model_alkathiry_tribe",
        "model_alkathiry_tribe_position",
    ]
    env["ir.model.data"].search(
        [("module", "=", defunct), ("name", "in", stale_names)]
    ).unlink()
