from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select


class TermBase(SQLModel):
    word: str = Field(index=True)
    meaning: str = Field(index=True)


class Term(TermBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TermPublic(TermBase):
    id: int


class TermUpdate(TermBase):
    word: str | None = None
    meaning: str | None = None


SQLITE_DATABASE_FILE = 'glossary.db'
SQLITE_DATABASE_URL  = f'sqlite:///{SQLITE_DATABASE_FILE}'

engine = create_engine(SQLITE_DATABASE_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/terms/", response_model=list[TermPublic])
def read_terms(session: SessionDep):
    terms = session.exec(select(Term)).all()
    return terms


@app.get("/terms/{term_id}", response_model=TermPublic)
def read_term(term_id: int, session: SessionDep):
    term = session.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    return term


@app.post("/terms/", response_model=TermPublic)
def create_term(term: TermBase, session: SessionDep):
    db_term = Term.model_validate(term)
    session.add(db_term)
    session.commit()
    session.refresh(db_term)
    return db_term


@app.put("/terms/{term_id}", response_model=TermPublic)
def update_term(term_id: int, term: TermUpdate, session: SessionDep):
    term_db = session.get(Term, term_id)
    if not term_db:
        raise HTTPException(status_code=404, detail="Term not found")
    term_data = term.model_dump(exclude_unset=True)
    term_db.sqlmodel_update(term_data)
    session.add(term_db)
    session.commit()
    session.refresh(term_db)
    return term_db


@app.delete("/terms/{term_id}")
def delete_term(term_id: int, session: SessionDep):
    term = session.get(Term, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    session.delete(term)
    session.commit()
    return {"ok": True}

