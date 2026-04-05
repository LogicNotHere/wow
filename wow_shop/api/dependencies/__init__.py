from wow_shop.api.dependencies.app import handle_request_id, log_request
from wow_shop.api.dependencies.auth import get_current_user
from wow_shop.api.dependencies.permissions import (
    require_admin_access,
    require_booster_access,
    require_catalog_deleted_view_access,
    require_catalog_restore_access,
    require_catalog_soft_delete_access,
    require_roles,
)
from wow_shop.api.dependencies.token import (
    get_access_payload,
    get_bearer_token,
)
from wow_shop.shared.auth.context import (
    CurrentUser,
    cu,
    get_auth_user,
    get_auth_user_id,
    get_auth_user_role,
)
