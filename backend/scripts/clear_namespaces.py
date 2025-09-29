#!/usr/bin/env python3
"""
Clear Pinecone namespaces script

Usage:
  # Dry run (list namespaces and counts)
  python backend/scripts/clear_namespaces.py

  # Delete all vectors in found namespaces
  python backend/scripts/clear_namespaces.py --delete

This script:
- Reads Pinecone settings from Django settings
- Prints index stats and namespaces
- Saves a JSON snapshot of current stats to ./pinecone_stats_backup.json
- If --delete is provided, attempts to delete all vectors per namespace
  using index.delete(delete_all=True, namespace=ns) with fallbacks.

Be careful: deletion is irreversible. This script is intended for test
indexes and cleanup.
"""
import os
import sys
import json
import time
import argparse
import traceback

# Setup Django settings so we can read env/config
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hellotutor.settings")
try:
    import django
    # Ensure the backend package is on sys.path so Django can import the 'hellotutor' package
    # when this script is run from the repository root.
    script_dir = os.path.dirname(os.path.abspath(__file__))  # backend/scripts
    backend_dir = os.path.abspath(os.path.join(script_dir, ".."))  # backend
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    django.setup()
except Exception as e:
    print("Warning: failed to setup Django. Ensure DJANGO_SETTINGS_MODULE is correct.")

from django.conf import settings
from pinecone import Pinecone


def describe_index(pc, index_name):
    try:
        idx = pc.Index(index_name)
        stats = idx.describe_index_stats()
        return stats
    except Exception as e:
        print(f"Error describing index {index_name}: {e}")
        return None


def save_backup(stats, path="pinecone_stats_backup.json"):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"Saved backup stats to {path}")
    except Exception as e:
        print(f"Failed to save backup: {e}")


def delete_namespace(index, ns):
    """Attempt to delete all vectors in a namespace with safe fallbacks."""
    print(f"Attempting to clear namespace: {ns}")
    try:
        # Preferred direct method if supported
        try:
            index.delete(delete_all=True, namespace=ns)
            print(f" - Success: index.delete(delete_all=True, namespace='{ns}') executed")
            return True
        except TypeError:
            # Some client versions don't accept delete_all argument
            pass
        except Exception as inner:
            # If API rejects delete_all, fallback
            print(f" - Warning: direct delete_all failed: {inner}")

        # Fallback 1: delete by filter for metadata tenant_tag if present
        try:
            filter_expr = {"tenant_tag": {"$exists": True}}
            index.delete(filter=filter_expr, namespace=ns)
            print(f" - Success: index.delete(filter=tenant_tag_exists, namespace='{ns}') executed")
            return True
        except Exception as inner:
            print(f" - Warning: delete by filter failed: {inner}")

        # Fallback 2: attempt to fetch ids by querying with an empty vector (not always supported)
        try:
            # This tries to sample up to 1000 vectors by issuing small queries — may not return everything
            print(" - Attempting to fetch ids via queries as last resort (may be partial)")
            # Query using zeros vector of proper dimension is risky; skip to final failure
            return False
        except Exception as inner:
            print(f" - Fallback fetch failed: {inner}")
            return False

    except Exception as e:
        print(f" - ERROR clearing namespace {ns}: {e}")
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Clear Pinecone namespaces")
    parser.add_argument("--delete", action="store_true", help="Actually delete vectors in found namespaces")
    parser.add_argument("--index", type=str, default=None, help="Override index name (optional)")
    args = parser.parse_args()

    api_key = getattr(settings, "PINECONE_API_KEY", None)
    index_name = args.index or getattr(settings, "PINECONE_INDEX", None)

    if not api_key:
        print("PINECONE_API_KEY not found in Django settings. Set it in your .env or settings.")
        sys.exit(1)
    if not index_name:
        print("PINECONE_INDEX not set in Django settings. Set PINECONE_INDEX in your .env or settings.")
        sys.exit(1)

    pc = Pinecone(api_key=api_key)

    print(f"Using Pinecone index: {index_name}")
    stats = describe_index(pc, index_name)
    if stats is None:
        print("Could not retrieve index stats. Exiting.")
        sys.exit(1)

    # Normalize stats for saving and extract namespace counts robustly
    namespaces = []
    serializable_stats = {"namespaces": {}}

    # Helper to extract vector count from different info shapes
    def _extract_count(info):
        # dict-like
        if isinstance(info, dict):
            return info.get("vector_count") or info.get("total_vector_count") or None
        # object with attributes
        for attr in ("vector_count", "count", "total_vector_count", "total_count"):
            if hasattr(info, attr):
                try:
                    return int(getattr(info, attr))
                except Exception:
                    return None
        # fallback
        return None

    if isinstance(stats, dict):
        ns_map = stats.get("namespaces", {})
        for ns, info in ns_map.items():
            count = _extract_count(info)
            namespaces.append((ns, count))
            serializable_stats["namespaces"][ns] = {"vector_count": count}
    else:
        # Try object-like access (NamespaceSummary or similar)
        ns_map = getattr(stats, "namespaces", None) or {}
        try:
            for ns, info in ns_map.items():
                count = _extract_count(info)
                namespaces.append((ns, count))
                serializable_stats["namespaces"][ns] = {"vector_count": count}
        except Exception:
            # Last resort: set serializable to string
            serializable_stats = {"raw_stats": str(stats)}

    # Save a clean JSON-serializable backup
    save_backup(serializable_stats)

    if not namespaces:
        print("No namespaces found in index (index may be empty).")
    else:
        print("Found namespaces and counts:")
        for ns, count in namespaces:
            print(f" - {ns}: vector_count={count}")

    if not args.delete:
        print("\nDry run complete. No deletion performed. Rerun with --delete to remove data.")
        sys.exit(0)

    # Confirm destructive action
    confirm = input("This will DELETE all vectors in the listed namespaces. Type 'yes' to proceed: ")
    if confirm.strip().lower() != "yes":
        print("Abort: Deletion cancelled by user.")
        sys.exit(0)

    # Perform deletion per-namespace
    index = pc.Index(index_name)
    results = {}
    for ns, count in namespaces:
        ok = delete_namespace(index, ns)
        results[ns] = {"requested_count": count, "deleted": ok}

    print("\nDeletion summary:")
    for ns, info in results.items():
        print(f" - {ns}: requested_count={info['requested_count']} deleted={info['deleted']}")

    # Show final stats
    time.sleep(1)
    final_stats = describe_index(pc, index_name)
    print("\nFinal index stats:")
    print(final_stats)


if __name__ == '__main__':
    main()
