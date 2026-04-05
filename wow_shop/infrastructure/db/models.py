"""Model import aggregator for Alembic metadata discovery."""

# Import modules for side effects so all tables are registered in Base.metadata.
from wow_shop.infrastructure.db.base import Base
from wow_shop.modules.auth.infrastructure.db import (  # noqa: F401
    models as auth_models,
)
from wow_shop.modules.chat.infrastructure.db import (  # noqa: F401
    models as chat_models,
)
from wow_shop.modules.orders.infrastructure.db import (  # noqa: F401
    models as orders_models,
)
from wow_shop.modules.catalog.infrastructure.db import (  # noqa: F401
    models as catalog_models,
)
from wow_shop.modules.pricing.infrastructure.db import (  # noqa: F401
    models as pricing_models,
)
from wow_shop.modules.payments.infrastructure.db import (  # noqa: F401
    models as payments_models,
)
from wow_shop.modules.notifications.infrastructure.db import (  # noqa: F401
    models as notifications_models,
)

metadata = Base.metadata
