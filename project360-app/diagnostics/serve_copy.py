"""Run diagnostics against copies; never write the working project data."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import ingest, intelligence, main, rag, updates, comparison, executive_pdf, ai_extraction

HERE = Path(__file__).resolve().parent
STATE = HERE / 'sandbox' / 'current-state-fixes'
STATE.mkdir(exist_ok=True)
original_corpus = ingest.DEFAULT_CORPUS
original_processed = ingest.PROCESSED
snapshot = {}
for base in (original_corpus, ROOT / 'data'):
    for path in base.rglob('*'):
        if path.is_file():
            snapshot[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
(HERE / 'original-hashes.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
for source, destination in ((original_corpus, STATE / 'corpus'), (ROOT / 'data', STATE / 'data')):
    shutil.copytree(source, destination, dirs_exist_ok=True)
for module in (ingest, intelligence, main, rag, comparison, executive_pdf, ai_extraction):
    if hasattr(module, 'PROCESSED'):
        module.PROCESSED = STATE / 'data' / 'processed'
    if hasattr(module, 'DEFAULT_CORPUS'):
        module.DEFAULT_CORPUS = STATE / 'corpus'
updates.STORE = STATE / 'data' / 'updates'
comparison.STORE = STATE / 'data' / 'comparison'
def excluded(*args, **kwargs):
    raise RuntimeError('LLM calls excluded from diagnostics')
main.answer_question = excluded
main.enrich = excluded
rag._external_reasoning_answer = excluded

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(main.app, host='127.0.0.1', port=8010)
