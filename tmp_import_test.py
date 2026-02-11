import importlib, sys
sys.path.insert(0, 'e:/Backup/pgwiz/spotify_project/ytstreamurl/ytstreamurl-serverless-api3-m-v2')
try:
    mod = importlib.import_module('packages.default.serverless_handler.__main__')
    print('Imported OK')
except Exception as e:
    print('Import failed:', e)
