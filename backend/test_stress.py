import asyncio
import uuid
import sys
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main.src.store.DBManager import (
    main_db_manager,
    chats_db_manager,
    researches_db_manager,
    history_db_manager,
    scrapes_db_manager,
    buckets_db_manager
)
from server import app
from main.src.utils.core.task_schedular import scheduler

now = datetime.now(timezone.utc).isoformat()

# ==========================================
# 1. Foreign Key Verification (Failures)
# ==========================================
print("--- [1] Checking Foreign Keys ---")
# Try to insert a research source without a valid research
fk_test_id = str(uuid.uuid4())
r_fk = researches_db_manager.insert('research_sources', {
    'id': fk_test_id,
    'research_id': 'invalid_research_id_123',
    'source_type': 'test',
    'source_url': 'test'
})
if not r_fk['success']:
    print(f"SUCCESS: FK caught orphaned research_source creation: {r_fk['message']}")
else:
    print("ERROR: FK constraint failed to catch orphaned insert!")
    sys.exit(1)

# ==========================================
# 2. Populating Test Data (Stress Test)
# ==========================================
print("\n--- [2] Populating Test Data ---")
ws_id = str(uuid.uuid4())
tmpl_id = str(uuid.uuid4())
res_id = str(uuid.uuid4())
chat_id = str(uuid.uuid4())

# Data sets containing the keyword 'quantum'
main_db_manager.insert('workspaces', {'id': ws_id, 'name': 'Quantum Physics Labs', 'desc': 'Labs for quantum experiments'})
chats_db_manager.insert('chat_threads', {'thread_id': chat_id, 'thread_title': 'Quantum supremacy discussion', 'created_at': now, 'updated_at': now})
researches_db_manager.insert('research_templates', {'id': tmpl_id, 'title': 'Science template'})
researches_db_manager.insert('researches', {'id': res_id, 'title': 'Quantum Computing Advances', 'desc': 'Researching qubits', 'research_template_id': tmpl_id})
scrapes_db_manager.insert('scrapes', {'id': str(uuid.uuid4()), 'url': 'http://quantum.com', 'title': 'Quantum article', 'content': 'Quantum entanglement is weird', 'created_at': now, 'updated_at': now})
buckets_db_manager.insert('buckets', {'id': 'bkt-1', 'name': 'Q-Assets', 'allowed_file_types': 'pdf', 'created_by': 'system', 'created_at': now})
buckets_db_manager.insert('bucket_items', {'id': str(uuid.uuid4()), 'bucket_id': 'bkt-1', 'file_name': 'quantum_mechanics.pdf', 'file_path': '/path', 'file_format': 'pdf', 'file_size': 100, 'summary': 'A pdf on quantum topics', 'created_by': 'system', 'created_at': now})

print("Data inserted across 6 tables!")

# ==========================================
# 3. FastAPI Client HTTP & Background Test
# ==========================================
print("\n--- [3] API Full Search (AI Mode: OFF) ---")
client = TestClient(app)

async def _start_scheduler(): await scheduler.start()
async def _stop_scheduler(): await scheduler.shutdown()

asyncio.run(_start_scheduler())

response = client.get('/search?q=quantum&ai_mode=false')
if response.status_code != 200:
    print(f"ERROR: API returned {response.status_code} - {response.text}")
    sys.exit(1)

data = response.json()
print(f"Found {data['results']['total_count']} results across types.")
types_found = set([item['type'] for item in data['results']['items']])
print(f"Types matched: {types_found}")

# ==========================================
# 4. FastAPI AI Mode Test
# ==========================================
print("\n--- [4] API Search (AI Mode: ON) ---")
response_ai = client.get('/search?q=quantum&ai_mode=true')
data_ai = response_ai.json()
search_id = data_ai['search_id']
print(f"Immediately returned. AI Status: {data_ai['ai_mode']['status']}")

print("\nWaiting for background tasks (DB saves & AI summary) to finish...")
asyncio.run(_stop_scheduler())

print("\n--- [5] Fetching Final AI Status ---")
ai_res = history_db_manager.fetch_one('searches', {'id': search_id})
if ai_res['success'] and ai_res['data']:
    print(f"Status in DB: {ai_res['data']['status']}")
    print(f"AI Summary Preview: {ai_res['data']['ai_summary']}")
else:
    print("ERROR: Could not fetch search history record.")

print("\n--- [6] Cleanup ---")
main_db_manager.delete('workspaces', {'id': ws_id})
chats_db_manager.delete('chat_threads', {'thread_id': chat_id})
researches_db_manager.delete('researches', {'id': res_id})
researches_db_manager.delete('research_templates', {'id': tmpl_id})
history_db_manager.delete('searches', {'id': data['search_id']})
history_db_manager.delete('searches', {'id': search_id})

print("✔ Stress test completed successfully.")
