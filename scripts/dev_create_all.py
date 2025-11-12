# scripts/dev_create_all.py
import os
from sqlalchemy import create_engine
from sublease_matcher.api.adapters.sqlalchemy.models import Base

url = os.getenv("SM_DATABASE_URL")
assert url, "SM_DATABASE_URL not set"
engine = create_engine(url, future=True)

print("Create-all URL ->", engine.url)
Base.metadata.create_all(engine)
print("Done.")
