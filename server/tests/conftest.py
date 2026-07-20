import os
import sys
import tempfile
from pathlib import Path

# il backend vive in server/ — importabile come `app`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# config di test PRIMA dell'import di app (legge l'env a import-time)
os.environ.setdefault("NEXUS_BRIDGE_TOKEN", "test-token")
os.environ.setdefault("NEXUS_COOKIE_SECURE", "false")
os.environ.setdefault(
    "NEXUS_DB_PATH",
    os.path.join(tempfile.mkdtemp(prefix="nexus-test-"), "nexus_test.db"),
)
