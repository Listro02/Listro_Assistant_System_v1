import sys
from pathlib import Path
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tests.test_sqlite_store
import tests.test_vector_store
import tests.test_sliding_window
import tests.test_consolidator
import tests.test_retriever
import tests.test_manager

modules = [
    tests.test_sqlite_store,
    tests.test_vector_store,
    tests.test_sliding_window,
    tests.test_consolidator,
    tests.test_retriever,
    tests.test_manager
]

def run_tests():
    total = 0
    passed = 0
    failed = 0
    
    for mod in modules:
        for name in dir(mod):
            if name.startswith("test_"):
                func = getattr(mod, name)
                if callable(func):
                    total += 1
                    try:
                        # We can't easily mock fixtures without pytest, so we skip tests requiring fixtures
                        if "temp_" in func.__code__.co_varnames:
                            print(f"Skipping {name} (requires fixture)")
                            total -= 1
                            continue
                            
                        # Need to pass tmp_path for test_manager_initialization
                        if name == "test_manager_initialization":
                            import tempfile
                            with tempfile.TemporaryDirectory() as tmp_path:
                                func(Path(tmp_path))
                        else:
                            func()
                        print(f"✅ {name}")
                        passed += 1
                    except Exception as e:
                        print(f"❌ {name}")
                        traceback.print_exc()
                        failed += 1
                        
    print(f"\nTotal: {total}, Passed: {passed}, Failed: {failed}")

if __name__ == "__main__":
    run_tests()
