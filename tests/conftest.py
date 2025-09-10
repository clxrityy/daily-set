import sys
from pathlib import Path
import pytest

# Ensure project root is on sys.path so tests can import the `app` package
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def reset_rate_limiter():
	# Clear in-memory rate limiter between tests to avoid cross-test flakiness
	try:
		import app.main as app_main
		app_main._RATE_LIMIT_STORE.clear()
	except Exception:
		pass
	yield
