"""Student email unique; backfill legacy placeholder with synthetic emails.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-19

"""
import secrets

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

LEGACY = "add_email@gmail.com"


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM student ORDER BY id")).fetchall()
    emails_seen = set()

    def next_synthetic():
        for _ in range(128):
            em = f"add_email_{secrets.token_hex(4)}@gmail.com"
            if em.lower() not in emails_seen:
                emails_seen.add(em.lower())
                return em
        raise RuntimeError("Could not allocate synthetic student email")

    for sid, email in rows:
        e = (email or "").strip().lower()
        need_new = (
            not e
            or e == LEGACY.lower()
            or e in emails_seen
        )
        if need_new:
            new_em = next_synthetic()
            conn.execute(
                sa.text("UPDATE student SET email = :em WHERE id = :id"),
                {"em": new_em, "id": sid},
            )
        else:
            emails_seen.add(e)

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("student", schema=None) as batch_op:
            batch_op.create_unique_constraint("uq_student_email", ["email"])
    else:
        op.create_unique_constraint("uq_student_email", "student", ["email"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("student", schema=None) as batch_op:
            batch_op.drop_constraint("uq_student_email", type_="unique")
    else:
        op.drop_constraint("uq_student_email", "student", type_="unique")
