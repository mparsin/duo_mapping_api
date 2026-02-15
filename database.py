from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey, Float, Boolean, JSON, Text, DateTime, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@duo-mapping.cefhyz1bpgbv.us-east-2.rds.amazonaws.com:5432/duo-mapping-db"
)

# Use app_runtime role for normal app connections (DML only). All tables live in "app" schema.
# ORM uses metadata.schema="app" so all queries use app.table_name. Optionally set search_path
# on connect (set DATABASE_SET_SEARCH_PATH=1) if your role is allowed to SET session vars.
_connect_args = {}
if os.getenv("DATABASE_SET_SEARCH_PATH", "").strip() in ("1", "true", "yes"):
    _connect_args["options"] = "-c search_path=app"
engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All tables are in the "app" schema (owned by app_migrator; app_runtime has DML on them).
metadata = MetaData(schema="app")
Base = declarative_base(metadata=metadata)

# Database Models
class TableSet(Base):
    __tablename__ = "table_set"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    
    # Relationships
    categories = relationship("Category", back_populates="table_set")

class Category(Base):
    __tablename__ = "category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(200), nullable=False)
    percent_mapped = Column(Float, default=0.0)
    tab = Column(String(200), nullable=True)
    seq_no = Column(Integer, nullable=True)
    line_no = Column(Integer, nullable=True)
    epic = Column(String(200), nullable=True)
    config = Column(JSON, nullable=True)
    isaiload = Column(Boolean, default=False, nullable=False)
    table_set_id = Column(Integer, ForeignKey("table_set.id"), nullable=True)
    
    # Relationships
    lines = relationship("Lines", back_populates="category")
    sub_categories = relationship("SubCategory", back_populates="category")
    table_set = relationship("TableSet", back_populates="categories")

class Lines(Base):
    __tablename__ = "lines"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    categoryid = Column(Integer, ForeignKey("category.id"), nullable=False)
    default = Column(String(200), comment="Default")
    customer_settings = Column(String(200))
    no_of_chars = Column(String(200))
    field_name = Column(String(200))
    reason = Column(String(800))
    name = Column(String(200), nullable=False)
    comment = Column(String(800))
    sub_category_id = Column(Integer, ForeignKey("sub-category.id"))
    table_id = Column(Integer, ForeignKey("erp_table.id"))
    column_id = Column(Integer, ForeignKey("erp_column.id"))
    exclude = Column(Boolean, default=False, nullable=False)
    iskeyfield = Column(Boolean, default=False, nullable=False)
    isfkfield = Column(Boolean, default=False, nullable=False)
    seq_no = Column(Integer, nullable=True)
    
    # Relationships
    category = relationship("Category", back_populates="lines")
    sub_category = relationship("SubCategory", back_populates="lines")
    erp_table = relationship("ERPTable", back_populates="lines")
    erp_column = relationship("ERPColumn", back_populates="lines")

class SubCategory(Base):
    __tablename__ = "sub-category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    comment = Column(String(800))
    seq_no = Column(Integer, nullable=True)
    
    # Relationships
    category = relationship("Category", back_populates="sub_categories")
    lines = relationship("Lines", back_populates="sub_category")

class ERPTable(Base):
    __tablename__ = "erp_table"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200))
    description = Column(String(600))
    
    # Relationships
    lines = relationship("Lines", back_populates="erp_table")
    columns = relationship("ERPColumn", back_populates="erp_table")

class ERPColumn(Base):
    __tablename__ = "erp_column"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    comment = Column(String(800))
    type = Column(String(200))
    table_id = Column(Integer, ForeignKey("erp_table.id"))
    not_null = Column(Boolean, default=False)
    primary_key = Column(Boolean, default=False)
    unique = Column(Boolean, default=False)
    default = Column(String(100), default=None)
    
    # Relationships
    erp_table = relationship("ERPTable", back_populates="columns")
    lines = relationship("Lines", back_populates="erp_column")


class GitHubConnection(Base):
    """Single row: app-wide GitHub PAT stored encrypted for create-schema-pr."""
    __tablename__ = "github_connection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    encrypted_token = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
