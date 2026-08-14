import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, DECIMAL, BIGINT, JSON, Date, BigInteger, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(30), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_user_identity_provider_subject"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(30), nullable=False)
    provider_subject = Column(String(255), nullable=False)
    email = Column(String(150), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(Text, nullable=False)
    user_agent = Column(Text)
    ip_address = Column(String(100))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    revoked_at = Column(DateTime)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = Column(String(200))
    phone = Column(String(20))
    gst_number = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(CHAR(36), ForeignKey("conversations.id", ondelete="CASCADE"))
    role = Column(String(20), nullable=False) # user, assistant
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text") # text, image, voice
    
    meta_data = Column(JSON)  # ✅ FIXED (renamed)

    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"))
    amount = Column(DECIMAL(15, 2), nullable=False)
    quantity = Column(DECIMAL(15, 3))
    category = Column(String(50))
    type = Column(String(20)) # income, expense
    gst_amount = Column(DECIMAL(15, 2))
    description = Column(Text)
    date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())

class UserDocument(Base):
    __tablename__ = "user_documents"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(CHAR(36), ForeignKey("conversations.id", ondelete="SET NULL"))
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(100))
    file_size = Column(BigInteger)
    category = Column(String(50))
    file_path = Column(Text, nullable=False)
    extracted_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36))
    action = Column(String(100))
    details = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class GSTDocument(Base):
    __tablename__ = "gst_documents"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255))
    content = Column(Text)
    source = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

class EmbeddingMetadata(Base):
    __tablename__ = "embeddings_metadata"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey("gst_documents.id", ondelete="CASCADE"))
    chunk_text = Column(Text)
    embedding_vector = Column(Text) # Storing as text for simplicity as per user prompt
    created_at = Column(DateTime, server_default=func.now())
