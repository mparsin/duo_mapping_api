from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@duo-mapping.cefhyz1bpgbv.us-east-2.rds.amazonaws.com:5432/duo-mapping-db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database Models
class Category(Base):
    __tablename__ = "category"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    Name = Column(String(200), nullable=False)
    percent_mapped = Column(Float, default=0.0)
    tab = Column(String(200), nullable=True)
    
    # Relationships
    lines = relationship("Lines", back_populates="category")
    sub_categories = relationship("SubCategory", back_populates="category")

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
    
    # Relationships
    erp_table = relationship("ERPTable", back_populates="columns")
    lines = relationship("Lines", back_populates="erp_column")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
