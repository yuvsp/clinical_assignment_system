from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '1eff0acda2d2'
down_revision = '3ced2ddd68de'
branch_labels = None
depends_on = None


def table_exists(table_name):
    inspector = inspect(op.get_bind())
    return inspector.has_table(table_name)


def upgrade():
    # Check if the student table exists
    if table_exists('student'):
        # Ensure the semester column exists before trying to alter it
        inspector = inspect(op.get_bind())
        columns = [col['name'] for col in inspector.get_columns('student')]

        if 'semester' not in columns:
            with op.batch_alter_table('student', schema=None) as batch_op:
                batch_op.add_column(sa.Column('semester', sa.String(length=1), nullable=False))

    # Drop the temporary table if it exists
    op.drop_table('_alembic_tmp_assignment')

    # Add the column with a default value
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('allocation', sa.String(length=20), nullable=False, server_default='שפה'))
        batch_op.alter_column('instructor_id',
                              existing_type=sa.INTEGER(),
                              nullable=True)

    # Remove the default value after the column has been populated
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.alter_column('allocation', server_default=None)


def downgrade():
    # Remove the column and revert instructor_id nullable change
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.alter_column('instructor_id',
                              existing_type=sa.INTEGER(),
                              nullable=False)
        batch_op.drop_column('allocation')

    # Recreate the temporary table if necessary
    op.create_table('_alembic_tmp_assignment',
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column('student_id', sa.INTEGER(), nullable=False),
                    sa.Column('instructor_id', sa.INTEGER(), nullable=True),
                    sa.Column('assigned_day', sa.VARCHAR(length=20), nullable=False),
                    sa.Column('allocation', sa.VARCHAR(length=20), nullable=False),
                    sa.ForeignKeyConstraint(['instructor_id'], ['clinical_instructor.id'], ),
                    sa.ForeignKeyConstraint(['student_id'], ['student.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
