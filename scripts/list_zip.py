import zipfile
p='temp_serverless_handler_code.py'
try:
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            print(n)
except Exception as e:
    print('ERR', e)
