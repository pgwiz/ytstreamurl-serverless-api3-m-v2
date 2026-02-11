import sys
sys.path.insert(0, 'e:/Backup/pgwiz/spotify_project/ytstreamurl/ytstreamurl-serverless-api3-m-v2')
from packages.default.serverless_handler import serverless_handler_local as sh
print('PY_IMPORT_ERROR:', getattr(sh, 'PY_IMPORT_ERROR', None))
res = sh.extract_youtube_stream('kffacxfA7G4')
print('RESULT:', res)
