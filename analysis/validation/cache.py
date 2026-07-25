import os
import json
import hashlib
import threading

class TheoryCache:
    def __init__(self, cache_file="data/cache/apfel_predictions_cache.json"):
        self.cache_file = cache_file
        self.lock = threading.Lock()
        self.cache = {}
        self._load_cache()

    def _load_cache(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load cache from {self.cache_file}: {e}")
                self.cache = {}

    def save(self):
        with self.lock:
            try:
                with open(self.cache_file, "w") as f:
                    json.dump(self.cache, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to save cache to {self.cache_file}: {e}")

    def _make_key(self, backend, backend_version, pdf_set, pdf_member, order, x, q2, scales, process, pdf_members=None, scale_members=None):
        # Build key dictionary
        key_dict = {
            "backend": backend,
            "backend_version": backend_version,
            "pdf_set": pdf_set,
            "pdf_member": pdf_member,
            "order": order,
            "x": round(float(x), 10),
            "q2": round(float(q2), 6),
            "scales": scales,
            "process": process,
            "pdf_members": sorted(pdf_members) if pdf_members else [],
            "scale_members": sorted([list(s) for s in scale_members]) if scale_members else []
        }
        key_str = json.dumps(key_dict, sort_keys=True)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

    def get(self, backend, backend_version, pdf_set, pdf_member, order, x, q2, scales, process, pdf_members=None, scale_members=None):
        key = self._make_key(backend, backend_version, pdf_set, pdf_member, order, x, q2, scales, process, pdf_members, scale_members)
        with self.lock:
            return self.cache.get(key)

    def set(self, backend, backend_version, pdf_set, pdf_member, order, x, q2, scales, process, value, pdf_members=None, scale_members=None):
        key = self._make_key(backend, backend_version, pdf_set, pdf_member, order, x, q2, scales, process, pdf_members, scale_members)
        with self.lock:
            self.cache[key] = value
