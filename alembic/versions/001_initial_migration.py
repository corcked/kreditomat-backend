"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-07-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Users table ###
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('referral_code', sa.String(length=10), nullable=True),
        sa.Column('referred_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['referred_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)
    op.create_index(op.f('ix_users_referral_code'), 'users', ['referral_code'], unique=True)

    # ### Personal data table ###
    op.create_table('personal_data',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=False),
        sa.Column('passport_series', sa.String(length=2), nullable=False),
        sa.Column('passport_number', sa.String(length=7), nullable=False),
        sa.Column('passport_issued_by', sa.String(length=255), nullable=False),
        sa.Column('passport_issue_date', sa.Date(), nullable=False),
        sa.Column('pinfl', sa.String(length=14), nullable=False),
        sa.Column('registration_address', sa.Text(), nullable=False),
        sa.Column('actual_address', sa.Text(), nullable=False),
        sa.Column('workplace', sa.String(length=255), nullable=False),
        sa.Column('position', sa.String(length=255), nullable=False),
        sa.Column('work_experience_months', sa.Integer(), nullable=False),
        sa.Column('marital_status', sa.Enum('single', 'married', 'divorced', 'widowed', name='maritalstatus'), nullable=False),
        sa.Column('children_count', sa.Integer(), nullable=False),
        sa.Column('contact_person_name', sa.String(length=255), nullable=False),
        sa.Column('contact_person_phone', sa.String(length=20), nullable=False),
        sa.Column('contact_person_relation', sa.String(length=100), nullable=False),
        sa.Column('additional_phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('employment_type', sa.Enum('employed', 'self_employed', 'unemployed', 'retired', 'student', name='employmenttype'), nullable=False),
        sa.Column('monthly_income', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('income_source', sa.Enum('salary', 'business', 'pension', 'rental', 'other', name='incomesource'), nullable=False),
        sa.Column('monthly_expenses', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('credit_payments', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('has_overdue_credits', sa.Boolean(), nullable=False),
        sa.Column('overdue_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('housing_status', sa.Enum('own', 'rent', 'family', 'mortgage', 'other', name='housingstatus'), nullable=False),
        sa.Column('living_arrangement', sa.Enum('alone', 'with_spouse', 'with_parents', 'with_children', 'with_roommates', name='livingarrangement'), nullable=False),
        sa.Column('education_level', sa.Enum('secondary', 'vocational', 'higher', 'postgraduate', name='educationlevel'), nullable=False),
        sa.Column('vehicle_ownership', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_personal_data_id'), 'personal_data', ['id'], unique=False)
    op.create_index(op.f('ix_personal_data_pinfl'), 'personal_data', ['pinfl'], unique=True)
    op.create_index(op.f('ix_personal_data_user_id'), 'personal_data', ['user_id'], unique=True)

    # ### Bank offers table ###
    op.create_table('bank_offers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('bank_name', sa.String(length=255), nullable=False),
        sa.Column('bank_logo', sa.String(length=500), nullable=True),
        sa.Column('min_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('max_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('min_term_months', sa.Integer(), nullable=False),
        sa.Column('max_term_months', sa.Integer(), nullable=False),
        sa.Column('annual_rate', sa.Float(), nullable=False),
        sa.Column('monthly_rate', sa.Float(), nullable=False),
        sa.Column('processing_fee', sa.Float(), nullable=False),
        sa.Column('insurance_required', sa.Boolean(), nullable=False),
        sa.Column('min_age', sa.Integer(), nullable=False),
        sa.Column('max_age', sa.Integer(), nullable=False),
        sa.Column('income_proof_required', sa.Boolean(), nullable=False),
        sa.Column('consider_credit_history', sa.Boolean(), nullable=False),
        sa.Column('decision_time_minutes', sa.Integer(), nullable=False),
        sa.Column('max_pdn', sa.Float(), nullable=False),
        sa.Column('special_offer', sa.String(length=255), nullable=True),
        sa.Column('requirements', sa.JSON(), nullable=True),
        sa.Column('documents', sa.JSON(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bank_offers_id'), 'bank_offers', ['id'], unique=False)
    op.create_index(op.f('ix_bank_offers_is_active'), 'bank_offers', ['is_active'], unique=False)

    # ### Applications table ###
    op.create_table('applications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('personal_data_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('term_months', sa.Integer(), nullable=False),
        sa.Column('purpose', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('draft', 'submitted', 'processing', 'approved', 'rejected', 'cancelled', name='applicationstatus'), nullable=False),
        sa.Column('scoring_data', sa.JSON(), nullable=True),
        sa.Column('credit_score', sa.Integer(), nullable=True),
        sa.Column('pdn_calculation', sa.JSON(), nullable=True),
        sa.Column('offers_data', sa.JSON(), nullable=True),
        sa.Column('selected_offer_id', sa.UUID(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['personal_data_id'], ['personal_data.id'], ),
        sa.ForeignKeyConstraint(['selected_offer_id'], ['bank_offers.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)


def downgrade() -> None:
    # ### Drop tables ###
    op.drop_index(op.f('ix_applications_user_id'), table_name='applications')
    op.drop_index(op.f('ix_applications_status'), table_name='applications')
    op.drop_index(op.f('ix_applications_id'), table_name='applications')
    op.drop_table('applications')
    
    op.drop_index(op.f('ix_bank_offers_is_active'), table_name='bank_offers')
    op.drop_index(op.f('ix_bank_offers_id'), table_name='bank_offers')
    op.drop_table('bank_offers')
    
    op.drop_index(op.f('ix_personal_data_user_id'), table_name='personal_data')
    op.drop_index(op.f('ix_personal_data_pinfl'), table_name='personal_data')
    op.drop_index(op.f('ix_personal_data_id'), table_name='personal_data')
    op.drop_table('personal_data')
    
    op.drop_index(op.f('ix_users_referral_code'), table_name='users')
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS applicationstatus')
    op.execute('DROP TYPE IF EXISTS housingstatus')
    op.execute('DROP TYPE IF EXISTS livingarrangement')
    op.execute('DROP TYPE IF EXISTS educationlevel')
    op.execute('DROP TYPE IF EXISTS incomesource')
    op.execute('DROP TYPE IF EXISTS employmenttype')
    op.execute('DROP TYPE IF EXISTS maritalstatus')