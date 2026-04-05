"""refactor lot options to normalized option/value model

Revision ID: 6b2c4cb08c11
Revises: a1f4c3d9b2e1
Create Date: 2026-03-30 20:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b2c4cb08c11"
down_revision: Union[str, None] = "a1f4c3d9b2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("catalog_service_options", "catalog_lot_options")

    op.add_column(
        "catalog_lot_options",
        sa.Column("label", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column(
            "input_type",
            sa.Enum(
                "CHECKBOX",
                "RADIO",
                "SELECT",
                "MULTISELECT",
                name="catalog_lot_option_input_type_enum",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column("depends_on_option_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column("depends_on_value_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE catalog_lot_options
        SET
            label = COALESCE(NULLIF(trim(code), ''), 'option-' || id::text),
            input_type = CASE lower(value_type)
                WHEN 'checkbox'
                    THEN 'CHECKBOX'::catalog_lot_option_input_type_enum
                WHEN 'radio'
                    THEN 'RADIO'::catalog_lot_option_input_type_enum
                WHEN 'select'
                    THEN 'SELECT'::catalog_lot_option_input_type_enum
                WHEN 'multiselect'
                    THEN 'MULTISELECT'::catalog_lot_option_input_type_enum
                ELSE 'SELECT'::catalog_lot_option_input_type_enum
            END
        """
    )
    op.alter_column(
        "catalog_lot_options",
        "label",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "catalog_lot_options",
        "input_type",
        existing_type=sa.Enum(
            "CHECKBOX",
            "RADIO",
            "SELECT",
            "MULTISELECT",
            name="catalog_lot_option_input_type_enum",
        ),
        nullable=False,
    )

    op.drop_column("catalog_lot_options", "value_type")
    op.drop_column("catalog_lot_options", "config_json")

    op.create_unique_constraint(
        op.f("uq_catalog_lot_options__lot_id_code"),
        "catalog_lot_options",
        ["lot_id", "code"],
    )

    op.create_foreign_key(
        op.f("fk_catalog_lot_options__depends_on_option_id__catalog_lot_options"),
        "catalog_lot_options",
        "catalog_lot_options",
        ["depends_on_option_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_catalog_lot_options__created_by_user_id__auth_users"),
        "catalog_lot_options",
        "auth_users",
        ["created_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_catalog_lot_options__updated_by_user_id__auth_users"),
        "catalog_lot_options",
        "auth_users",
        ["updated_by_user_id"],
        ["id"],
    )

    op.create_table(
        "catalog_lot_option_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "price_value",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["option_id"],
            ["catalog_lot_options.id"],
            name=op.f("fk_catalog_lot_option_values__option_id__catalog_lot_options"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["auth_users.id"],
            name=op.f("fk_catalog_lot_option_values__created_by_user_id__auth_users"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["auth_users.id"],
            name=op.f("fk_catalog_lot_option_values__updated_by_user_id__auth_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_lot_option_values")),
        sa.UniqueConstraint(
            "option_id",
            "code",
            name=op.f("uq_catalog_lot_option_values__option_id_code"),
        ),
    )
    op.create_foreign_key(
        op.f(
            "fk_catalog_lot_options__depends_on_value_id__catalog_lot_option_values"
        ),
        "catalog_lot_options",
        "catalog_lot_option_values",
        ["depends_on_value_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f(
            "fk_catalog_lot_options__depends_on_value_id__catalog_lot_option_values"
        ),
        "catalog_lot_options",
        type_="foreignkey",
    )
    op.drop_table("catalog_lot_option_values")
    op.drop_constraint(
        op.f("fk_catalog_lot_options__updated_by_user_id__auth_users"),
        "catalog_lot_options",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_catalog_lot_options__created_by_user_id__auth_users"),
        "catalog_lot_options",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_catalog_lot_options__depends_on_option_id__catalog_lot_options"),
        "catalog_lot_options",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("uq_catalog_lot_options__lot_id_code"),
        "catalog_lot_options",
        type_="unique",
    )

    op.add_column(
        "catalog_lot_options",
        sa.Column("value_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "catalog_lot_options",
        sa.Column("config_json", sa.JSON(), nullable=True),
    )
    op.execute(
        """
        UPDATE catalog_lot_options
        SET value_type = lower(input_type::text)
        WHERE value_type IS NULL
        """
    )
    op.alter_column(
        "catalog_lot_options",
        "value_type",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    op.drop_column("catalog_lot_options", "updated_by_user_id")
    op.drop_column("catalog_lot_options", "created_by_user_id")
    op.drop_column("catalog_lot_options", "updated_at")
    op.drop_column("catalog_lot_options", "created_at")
    op.drop_column("catalog_lot_options", "depends_on_value_id")
    op.drop_column("catalog_lot_options", "depends_on_option_id")
    op.drop_column("catalog_lot_options", "is_active")
    op.drop_column("catalog_lot_options", "input_type")
    op.drop_column("catalog_lot_options", "label")

    op.rename_table("catalog_lot_options", "catalog_service_options")
    op.execute("DROP TYPE IF EXISTS catalog_lot_option_input_type_enum")
