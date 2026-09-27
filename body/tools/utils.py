"""Utility functions for system operations."""
import os
import sys
import json
import datetime
import subprocess
import concurrent.futures
import time
import re
import ast

def log_message(msg):
    """Log a message to standard output."""
    print(f"[UTIL] {msg}")

def write_json(path, data):
    """Write data to a JSON file."""
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        log_message(f"Written to {path}")
    except Exception as e:
        log_message(f"Error writing {path}: {e}")

def read_json(path):
    """Read and parse a JSON file."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        log_message(f"Read from {path}")
        return data
    except Exception as e:
        log_message(f"Error reading {path}: {e}")
        return None

# [PARCHE-FIXES-V1:utils_lock]
import contextlib

@contextlib.contextmanager
def file_lock(lock_path):
    """Lock de exclusión simple basado en un archivo .lock (fcntl en Unix).
    Evita condiciones de carrera al leer/escribir estado compartido
    (ej. memory/knowledge.json) si en el futuro hay ejecución concurrente."""
    lock_path = str(lock_path) + ".lock"
    fh = open(lock_path, "a+")
    try:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except ImportError:
            pass  # Plataforma sin fcntl (Windows): degradar sin lock
        yield
    finally:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_UN)
        except ImportError:
            pass
        fh.close()
