import sys, json
from pathlib import Path
# Ensure project root on sys.path
proj_root = Path(__file__).resolve().parent
sys.path.insert(0, str(proj_root))
# Import main handler
from packages.default.serverless_handler import __main__ as handler


def invoke(path):
    event = {"http": {"path": path, "method": "GET"}}
    try:
        res = handler.main(event, None)
        print(json.dumps({"path": path, "result": res}, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"path": path, "exception": str(e)}))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python local_invoke.py <path>')
        sys.exit(1)
    invoke(sys.argv[1])
