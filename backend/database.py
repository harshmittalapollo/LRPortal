import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable missing")

DATABASE_URL = DATABASE_URL.replace(
    "mysql://",
    "mysql+pymysql://"
)

# remove unsupported parameter
DATABASE_URL = DATABASE_URL.replace(
    "?ssl-mode=REQUIRED",
    ""
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "ssl": {}
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()