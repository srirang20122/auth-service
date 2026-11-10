import os
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
