# db/database_setup.py

import sqlalchemy
from sqlalchemy import (
    MetaData, Table, Column, func,
    Integer, String, Text, Float, DateTime, Boolean, Enum, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID

# Define the table structure (this is just a definition, it doesn't execute anything)
metadata = MetaData()

# Table 1: Static, original dataset
original_training_data = Table('original_training_data', metadata,
    Column('data_id', Integer, primary_key=True),
    Column('subject', Text),
    Column('description', Text),
    Column('category', String(50)),
    Column('priority', String(50))
)

# Table 2: Tracks model versions for traceability
models = Table('models', metadata,
    Column('model_id', Integer, primary_key=True),
    Column('model_name', String(100)),
    Column('model_version', String(50)),
    Column('deployed_at', DateTime, server_default=func.now()),
    Column('is_active', Boolean, default=False)
)

# Table 3: Main transactional table for all tickets
tickets = Table('tickets', metadata,
    Column('ticket_id', UUID(as_uuid=True), primary_key=True),
    Column('subject', Text),
    Column('description', Text),
    Column('created_at', DateTime, server_default=func.now()),
    Column('status', Enum('PROCESSING', 'PENDING_REVIEW', 'COMPLETED', name='ticket_status_enum')),
    Column('predicted_category', String(50)),
    Column('predicted_priority', String(50)),
    Column('prediction_confidence_category', Float),
    Column('prediction_confidence_priority', Float),
    Column('category_model_id', Integer, ForeignKey('models.model_id')),
    Column('priority_model_id', Integer, ForeignKey('models.model_id')),
    Column('final_category', String(50), nullable=True),
    Column('final_priority', String(50), nullable=True),
    Column('reviewed_at', DateTime, nullable=True),
    Column('used_for_retraining', Boolean, server_default=sqlalchemy.sql.false())
)