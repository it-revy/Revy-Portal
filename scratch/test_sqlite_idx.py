from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Index, text

e = create_engine("sqlite:///:memory:")
m = MetaData()
t = Table("test", m, Column("id", Integer, primary_key=True), Column("status", String))
idx = Index("ix_test", t.c.status, sqlite_where=text("status = 'Open'"))
m.create_all(e)
print("Partial index with text() works perfectly on SQLite!")
