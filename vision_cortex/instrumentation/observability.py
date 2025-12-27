PROM_REGISTRY = None

def get_inproc_task(name: str):
    def _noop(*a, **k):
        class _Ctx:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx()

    return _noop
