"""Model import aggregator for Alembic metadata discovery."""

# Import modules for side effects so all tables are registered in Base.metadata.
from wow_shop.modules.auth.infrastructure.db import models as auth_models  # noqa: F401
from wow_shop.modules.catalog.infrastructure.db import models as catalog_models  # noqa: F401
from wow_shop.modules.chat.infrastructure.db import models as chat_models  # noqa: F401
from wow_shop.modules.notifications.infrastructure.db import models as notifications_models  # noqa: F401
from wow_shop.modules.orders.infrastructure.db import models as orders_models  # noqa: F401
from wow_shop.modules.payments.infrastructure.db import models as payments_models  # noqa: F401
from wow_shop.modules.pricing.infrastructure.db import models as pricing_models  # noqa: F401
from wow_shop.infrastructure.db.base import Base


metadata = Base.metadata

__all__ = ["metadata"]
