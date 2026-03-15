"""Initial schema: field, clinical_instructor, student, assignment

Revision ID: 0001_initial
Revises:
Create Date: 2025-03-14

This migration creates the base tables so that 5116f52de221 and later can run
on an empty database (e.g. fresh Supabase).
"""
from alembic import op
from alembic import context
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _id_column():
    """Primary key with auto-increment: Identity on PostgreSQL, plain Integer on SQLite."""
    if context.get_context().dialect.name == "postgresql":
        return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)
    return sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True)


def upgrade():
    op.create_table(
        "field",
        _id_column(),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default=sa.text("'#FFFFFF'")),
    )
    op.create_table(
        "clinical_instructor",
        _id_column(),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("practice_location", sa.String(length=100), nullable=False),
        sa.Column("area_of_expertise_id", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("relevant_semesters", sa.String(length=100), nullable=False),
        sa.Column("years_of_experience", sa.Integer(), nullable=False),
        sa.Column("available_days_to_assign", sa.String(length=100), nullable=False),
        sa.Column("max_students_per_day", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default=sa.text("'#FFFFFF'")),
        sa.Column("single_assignment", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["area_of_expertise_id"], ["field.id"]),
    )
    op.create_table(
        "student",
        _id_column(),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False, server_default=sa.text("'add_email@gmail.com'")),
        sa.Column("preferred_field_id_1", sa.Integer(), nullable=False),
        sa.Column("preferred_field_id_2", sa.Integer(), nullable=False),
        sa.Column("preferred_field_id_3", sa.Integer(), nullable=False),
        sa.Column("preferred_practice_area", sa.String(length=100), nullable=False),
        sa.Column("semester", sa.String(length=1), nullable=False, server_default=sa.text("'א'")),
        sa.ForeignKeyConstraint(["preferred_field_id_1"], ["field.id"]),
        sa.ForeignKeyConstraint(["preferred_field_id_2"], ["field.id"]),
        sa.ForeignKeyConstraint(["preferred_field_id_3"], ["field.id"]),
    )
    op.create_table(
        "assignment",
        _id_column(),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=True),
        sa.Column("assigned_day", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["instructor_id"], ["clinical_instructor.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"]),
    )


def downgrade():
    op.drop_table("assignment")
    op.drop_table("student")
    op.drop_table("clinical_instructor")
    op.drop_table("field")
