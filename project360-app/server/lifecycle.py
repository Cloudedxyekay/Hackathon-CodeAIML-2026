"""Reversible visibility changes; source evidence and ticket facts remain intact."""
import json
from . import ingest


def read_states():
    path = ingest.PROCESSED / 'event_states.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def apply_states(memory):
    states = read_states()
    hidden, active = [], []
    for event in memory['events']:
        state = states.get(event['id'])
        if state:
            hidden.append({**event, 'visibility': state})
        else:
            active.append(event)
    return {**memory, 'events': active, 'hidden_events': hidden}


def change_event(identifier, action):
    if action not in ('archived', 'deleted', 'restore'):
        raise ValueError('Action invalide.')
    with ingest.INGEST_LOCK:
        from .intelligence import get_project_memory
        memory = get_project_memory()
        if identifier not in {e['id'] for e in memory['events'] + memory.get('hidden_events', [])}:
            raise ValueError('Événement introuvable.')
        states = read_states()
        if action == 'restore':
            states.pop(identifier, None)
        else:
            states[identifier] = action
        path = ingest.PROCESSED / 'event_states.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(states), encoding='utf-8')
        temporary.replace(path)
        return {'ok': True}
