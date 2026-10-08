from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# JWT 密钥,生产环境应通过环境变量覆盖
SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

DATABASE_URL = f"sqlite:///{BASE_DIR / 'db' / 'app.db'}"

UPLOAD_DIR = BASE_DIR / "uploads"
AUDIO_DIR = UPLOAD_DIR / "audio"
IMAGE_DIR = UPLOAD_DIR / "images"
