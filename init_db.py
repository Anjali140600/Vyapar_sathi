from app.core.database import engine, Base
from app.models.schema import User, UserSession, UserProfile, Conversation, Message, Transaction, UserDocument, SystemLog, GSTDocument, EmbeddingMetadata

def init_db():
    print("Creating tables in MySQL...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
