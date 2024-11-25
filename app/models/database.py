import datetime, enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, create_engine


db_url = "sqlite:///scrutinpunchor.db"
# password = "S3cUr6Pr0Jects@!!!"
# db_url = f"sqlite+pysqlcipher://:{password}@/scrutin_punchor.db"

engine = create_engine(db_url)

Base = declarative_base()


# logsevents table - possible action that can be performed on a file
class LogEvent(enum.Enum):
    MODIFIED = "modified"
    CREATED = "created"
    DELETED = "deleted"
    MOVED = "moved"


# users table - deal with authentication and user identity, those using scutin_punchor
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key = True)
    name = Column(String(255), nullable = False)
    email = Column(String(120), unique = True, nullable = False)
    pseudo = Column(String(255), unique = True, nullable = False)
    password = Column(String, nullable = False)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    # delay and delay_end_datetime let us deal with exponential backoff stuff
    delay = Column(Integer, default = 0)
    delay_end_datetime = Column(DateTime, default=datetime.datetime.utcnow)

    codes = relationship("Code", backref = "user") # link user to all codes we've sent to him/her performing 2FA auth
    logs = relationship("Log", backref = "user")


# codes table - deal with codes sent to user's mail box for 2-factor authentication
class Code(Base):
    __tablename__ = "codes"
    
    id = Column(Integer, primary_key = True)
    verified = Column(Boolean, default = False) # tell us whether the user perfectly validated the code or not
    secret_key = Column(Integer, nullable = False) # key used to check for correctness of user's provided code
    expired_datetime = Column(DateTime, nullable = False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable = False)


# logs table - register any file system event within a folder scrutin_punchor is monitoring
class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key = True)
    event = Column(Enum(LogEvent))
    source = Column(String(500), nullable = False)
    destination = Column(String(500)) # useful for COPY and MOVE events
    file_type = Column(String(10)) 
    observed_at = Column(DateTime, default=datetime.datetime.utcnow)
    from_sp = Column(Boolean, default = False) # tell us whether the events come from ScrutinPunchor or not
                                               # it helps a lot in GUARDIAN mode preventing duplicates alerts

    user_id = Column(Integer, ForeignKey("users.id"), nullable = False)

    alerts = relationship("Alert", backref = "log")


# alerts table - store data about any potential attack identified by scrutin_punchor
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key = True)
    vuln_name = Column(String(500), nullable = False)
    analysis_result = Column(String(10**10)) # store a summary of analysis done by our 3 detection engines
    identified_at = Column(DateTime, default=datetime.datetime.utcnow)

    log_id = Column(Integer, ForeignKey("logs.id"), nullable = False)


# files table - record file's hash and name
class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key = True)
    name = Column(String(500), nullable = False)
    hash = Column(String(128), unique = True, nullable = False) # format is sha512 one
    deleted = Column(Boolean, default = False)
    saved_at = Column(DateTime, default=datetime.datetime.utcnow) # saved time
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow) # update time


if __name__ == "__main__":
    Base.metadata.create_all(engine)
