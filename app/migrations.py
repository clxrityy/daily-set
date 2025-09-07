"""
Database migration system for Daily Set application.
Handles schema changes and index creation.
"""

from sqlmodel import SQLModel, Field, create_engine, text, Session, select
from typing import Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class Migration(SQLModel, table=True):
    """Track applied migrations"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    applied_at: datetime


def get_engine():
    """Get database engine"""
    db_path = os.getenv("DATABASE_URL", "sqlite:///./set.db")
    return create_engine(db_path, echo=False, connect_args={"check_same_thread": False})


def ensure_migration_table(engine):
    """Ensure the migration tracking table exists"""
    Migration.metadata.create_all(engine)


def has_migration_been_applied(engine, migration_name: str) -> bool:
    """Check if a migration has already been applied"""
    ensure_migration_table(engine)
    
    with Session(engine) as session:
        result = session.exec(
            select(Migration).where(Migration.name == migration_name)
        ).first()
        return result is not None


def apply_migration(engine, migration_name: str, migration_sql: str):
    """Apply a migration and record it"""
    if has_migration_been_applied(engine, migration_name):
        logger.info(f"Migration {migration_name} already applied, skipping")
        return
    
    logger.info(f"Applying migration: {migration_name}")
    
    with Session(engine) as session:
        try:
            # Execute the migration SQL
            for statement in migration_sql.strip().split(';'):
                statement = statement.strip()
                if statement:
                    session.execute(text(statement))
            
            # Record the migration
            migration = Migration(name=migration_name, applied_at=datetime.now())
            session.add(migration)
            session.commit()
            
            logger.info(f"Migration {migration_name} applied successfully")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to apply migration {migration_name}: {e}")
            raise


def run_migrations():
    """Run all pending migrations"""
    engine = get_engine()
    
    # Migration 001: Add performance indexes
    migration_001 = """
    -- Index for leaderboard queries (player_id, date, seconds)
    CREATE INDEX IF NOT EXISTS idx_completion_player_date ON completion(player_id, date);
    CREATE INDEX IF NOT EXISTS idx_completion_date_seconds ON completion(date, seconds);
    CREATE INDEX IF NOT EXISTS idx_completion_date_player_seconds ON completion(date, player_id, seconds);
    
    -- Index for session queries
    CREATE INDEX IF NOT EXISTS idx_session_player_id ON gamesession(player_id);
    CREATE INDEX IF NOT EXISTS idx_session_date ON gamesession(date);
    CREATE INDEX IF NOT EXISTS idx_session_expires_at ON gamesession(expires_at);
    CREATE INDEX IF NOT EXISTS idx_session_finished ON gamesession(finished);
    
    -- Index for player username lookups
    CREATE INDEX IF NOT EXISTS idx_player_username ON player(username)
    """
    
    apply_migration(engine, "001_performance_indexes", migration_001)
    
    # Migration 002: Add cleanup indexes
    migration_002 = """
    -- Indexes for cleanup operations
    CREATE INDEX IF NOT EXISTS idx_session_cleanup ON gamesession(finished, expires_at);
    CREATE INDEX IF NOT EXISTS idx_session_rotation ON gamesession(last_rotated)
    """
    
    apply_migration(engine, "002_cleanup_indexes", migration_002)
    
    # Migration 003: Add completed_at timestamp to completion
    migration_003 = """
    ALTER TABLE completion ADD COLUMN completed_at TEXT
    """
    apply_migration(engine, "003_add_completed_at", migration_003)
    
    logger.info("All migrations completed")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run migrations
    run_migrations()
