from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Float, ForeignKey,
    CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.types import TypeDecorator, TEXT
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid
from pydantic import BaseModel
import json

class DbType(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"

class FeedbackCreate(BaseModel):
    score: float
    comment: Optional[str] = None

# SQLAlchemy의 TyepDecorator를 활용해 타입을 커스터마이징해서 한글이 유니코드로 출력되는 문제 해결
class JSONEncodedDict(TypeDecorator):
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

Base = declarative_base()

class Session(Base):
    __tablename__ = "session"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    start_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_timestamp = Column(DateTime)
    status = Column(
        String, 
        CheckConstraint("status IN ('active', 'completed', 'error')"),
        default='active'
    )
    
    # Relationships
    qnas = relationship("QNA", back_populates="session")

class Trace(Base):
    __tablename__ = "trace"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    trace_type = Column(String, nullable=False)  # e.g., 'process', 'error'
    node_type = Column(String)  # 'planner', 'executor', 'solver' 등
    model = Column(String)
    duration_ms = Column(Float)
    token_usage = Column(Integer)
    user_feedback = Column(Float)
    feedback_comment = Column(String)
    
    # Relationships
    qna = relationship("QNA", back_populates="trace")
    state = relationship("State", back_populates="trace", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "trace_type": self.trace_type,
            "node_type": self.node_type,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "token_usage": self.token_usage,
            "user_feedback": self.user_feedback,
            "feedback_comment": self.feedback_comment,
            "state": self.state.to_dict() if self.state else None
        }
    
class QNA(Base):
    __tablename__ = "qna"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    session_id = Column(String, ForeignKey('session.id'), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(String)
    question_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    answer_timestamp = Column(DateTime)
    trace_id = Column(String, ForeignKey('trace.id'), nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="qnas")
    trace = relationship("Trace", back_populates="qna")

class State(Base):
    __tablename__ = "state"
    
    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey('trace.id'), nullable=False)
    plan_string = Column(String)
    steps = Column(JSONEncodedDict)
    results = Column(JSONEncodedDict)
    result = Column(JSONEncodedDict)
    dataframes = Column(JSONEncodedDict)
    calc_data = Column(JSONEncodedDict)
    
    trace = relationship("Trace", back_populates="state")

    def to_dict(self):
        return {
            "id": self.id,
            "plan_string": self.plan_string,
            "steps": self.steps,
            "results": self.results,
            "result": self.result,
            "dataframes": self.dataframes,
            "calc_data": self.calc_data
        }

# Pydantic models for request validation
class SessionCreate(BaseModel):
    user_id: str

class QNACreate(BaseModel):
    user_id: str
    session_id: str
    question: str
    trace_id: Optional[str] = None

class QNAUpdate(BaseModel):
    answer: Optional[str] = None
    answer_timestamp: Optional[datetime] = None
    trace_id: Optional[str] = None

class TraceCreate(BaseModel):
    trace_type: str
    node_type: Optional[str] = None
    model: Optional[str] = None
    duration_ms: Optional[float] = None
    token_usage: Optional[int] = None

class FeedbackCreate(BaseModel):
    score: float
    comment: Optional[str] = None

class LangfuseDB:
    def __init__(self, db_type: DbType = DbType.SQLITE):
        self.engine = create_engine(
            "sqlite:///./langfuse.db" if db_type == DbType.SQLITE 
            else "postgresql://user:password@localhost/langfuse"
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        
    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

def create_langfuse_app(db_type: DbType = DbType.SQLITE) -> FastAPI:
    app = FastAPI()
    db = LangfuseDB(db_type)
    db.create_tables()

    @app.post("/api/session")
    async def create_session(
        session_data: SessionCreate, 
        db: Session = Depends(db.get_db)
    ):
        """Create a new session"""
        try:
            session = Session(
                id=str(uuid.uuid4()),
                user_id=session_data.user_id,
                status='active'
            )
            db.add(session)
            db.commit()
            return {"status": "success", "session_id": session.id}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @app.patch("/api/session/{session_id}")
    async def update_session(
        session_id: str,
        status: str,
        db: Session = Depends(db.get_db)
    ):
        """Update session status and end timestamp"""
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session.status = status
            if status in ['completed', 'error']:
                session.end_timestamp = datetime.utcnow()
            
            db.commit()
            return {"status": "success"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/qna")
    async def create_qna(
        qna_data: QNACreate,
        db: Session = Depends(db.get_db)
    ):
        """Create a new QNA entry"""
        try:
            qna = QNA(
                id=str(uuid.uuid4()),
                user_id=qna_data.user_id,
                session_id=qna_data.session_id,
                question=qna_data.question,
                trace_id=qna_data.trace_id
            )
            db.add(qna)
            db.commit()
            return {"status": "success", "qna_id": qna.id}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @app.patch("/api/qna/{qna_id}")
    async def update_qna(
        qna_id: str,
        qna_data: QNAUpdate,
        db: Session = Depends(db.get_db)
    ):
        """Update QNA with answer and/or trace_id"""
        try:
            qna = db.query(QNA).filter(QNA.id == qna_id).first()
            if not qna:
                raise HTTPException(status_code=404, detail="QNA not found")
            
            if qna_data.answer is not None:
                qna.answer = qna_data.answer
            if qna_data.answer_timestamp is not None:
                qna.answer_timestamp = qna_data.answer_timestamp
            if qna_data.trace_id is not None:
                qna.trace_id = qna_data.trace_id
            
            db.commit()
            return {"status": "success"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/trace")
    async def create_trace(
        trace_data: Dict[str, Any],
        db: Session = Depends(db.get_db)
    ):
        """Create a new trace with state data"""
        try:
            print(f"Creating trace with data: {trace_data}")
            trace = Trace(
                id=trace_data['id'],
                timestamp=datetime.utcnow(),
                trace_type=trace_data['trace_type'],
                node_type=trace_data.get('node_type'),
                model=trace_data.get('model'),
                duration_ms=trace_data.get('duration_ms'),
                token_usage=trace_data.get('token_usage')
            )
            db.add(trace)
            
            # Create state if meta_data is provided
            meta_data = trace_data.get('meta_data', {})
            if meta_data:
                print(f"Creating state with meta_data: {meta_data}")
                state = State(
                    id=str(uuid.uuid4()),
                    trace_id=trace.id,
                    plan_string=meta_data.get('plan_string'),
                    steps=meta_data.get('steps'),
                    results=meta_data.get('results'),
                    result=meta_data.get('result'),
                    dataframes=meta_data.get('dataframes'),
                    calc_data=meta_data.get('calc_data')
                )
                db.add(state)
            
            db.commit()
            print(f"Trace created successfully with id: {trace.id}")
            return {"status": "success", "trace_id": trace.id}
        except Exception as e:
            db.rollback()
            print(f"Error creating trace: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/trace/{trace_id}")
    async def get_trace(trace_id: str, db: Session = Depends(db.get_db)):
        """Get trace and its associated state"""
        trace = db.query(Trace).filter(Trace.id == trace_id).first()
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace.to_dict()

    @app.post("/api/trace/{trace_id}/feedback")
    async def add_feedback(
        trace_id: str,
        feedback_data: FeedbackCreate,
        db: Session = Depends(db.get_db)
    ):
        """Add feedback to a trace"""
        try:
            trace = db.query(Trace).filter(Trace.id == trace_id).first()
            if not trace:
                raise HTTPException(status_code=404, detail="Trace not found")
            
            trace.user_feedback = feedback_data.score
            trace.feedback_comment = feedback_data.comment
            db.commit()
            return {"status": "success"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/session/{session_id}/qnas")
    async def get_session_qnas(session_id: str, db: Session = Depends(db.get_db)):
        """Get all QNAs for a session"""
        qnas = db.query(QNA).filter(QNA.session_id == session_id).all()
        return [{
            "id": qna.id,
            "question": qna.question,
            "answer": qna.answer,
            "trace_id": qna.trace_id,
            "question_timestamp": qna.question_timestamp.isoformat() if qna.question_timestamp else None,
            "answer_timestamp": qna.answer_timestamp.isoformat() if qna.answer_timestamp else None
        } for qna in qnas]

    return app

if __name__ == "__main__":
    import uvicorn
    
    app = create_langfuse_app(DbType.SQLITE)
    uvicorn.run(app, host="0.0.0.0", port=8001)
    
    # Production mode with PostgreSQL
    # app = create_langfuse_app(DbType.POSTGRES)
    # uvicorn.run(app, host="0.0.0.0", port=8001)