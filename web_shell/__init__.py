from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List

router = APIRouter()

ROOT = Path(__file__).resolve().parents[1]


def _resolve_within_root(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if not str(p).startswith(str(ROOT)):
        raise HTTPException(status_code=400, detail='Invalid path')
    return p


@router.get('/api/webshell/list')
def list_files(path: str = '') -> List[dict]:
    base = _resolve_within_root(path) if path else ROOT
    if not base.exists():
        raise HTTPException(status_code=404, detail='Not found')
    items = []
    for p in sorted(base.iterdir()):
        items.append({
            'name': p.name,
            'path': str(p.relative_to(ROOT)),
            'is_dir': p.is_dir()
        })
    return items


@router.get('/api/webshell/read')
def read_file(path: str):
    f = _resolve_within_root(path)
    if not f.exists() or f.is_dir():
        raise HTTPException(status_code=400, detail='Invalid file')
    try:
        return {'content': f.read_text(encoding='utf-8')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/api/webshell/save')
def save_file(path: str, content: str):
    f = _resolve_within_root(path)
    try:
        f.write_text(content, encoding='utf-8')
        return {'ok': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
