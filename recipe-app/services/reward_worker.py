"""Retry persisted completed tasks independently of the app screen."""
import logging
import threading
from config.database import db_transaction
from services.reward_service import retry_pending
log=logging.getLogger(__name__)


def install(app):
    stop=threading.Event()
    thread=None
    def run():
        while not stop.is_set():
            try:
                retry_pending()
            except Exception:
                log.exception('Pending reward scan failed')
            stop.wait(30)
    @app.on_event('startup')
    def start_worker():
        nonlocal thread
        with db_transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM app_schema_migrations WHERE migration_key='sport_session_v1_2_1_20261014'")
                if not cur.fetchone():
                    raise RuntimeError('請先執行 migrations/sport_session_v1_2_1.sql')
        thread=threading.Thread(target=run,name='task-reward-retry',daemon=True)
        thread.start()
    @app.on_event('shutdown')
    def stop_worker():
        stop.set()
        if thread:
            thread.join(timeout=5)
