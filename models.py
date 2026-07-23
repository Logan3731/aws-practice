from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    records = relationship("Record", back_populates="owner")


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String, index=True)
    weight = Column(Float)
    height = Column(Float)
    systolic = Column(Integer)
    diastolic = Column(Integer)
    blood_sugar = Column(Integer)
    steps = Column(Integer, default=0)
    sleep_hours = Column(Float, default=0.0)
    memo = Column(String, default="")

    owner = relationship("User", back_populates="records")