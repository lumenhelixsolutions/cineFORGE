import re, sys

with open('backend/app.py', 'r') as f:
    content = f.read()

if 'from fastapi.middleware.cors import CORSMiddleware' not in content:
    content = content.replace(
        'from fastapi import ',
        'from fastapi.middleware.cors import CORSMiddleware\nfrom fastapi import '
    )

content = re.sub(
    r'app\.add_middleware\(\s*CORSMiddleware,[^)]+\)\s*\n*',
    '',
    content,
    flags=re.DOTALL
)

cors_block = '''app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

''' 

pattern = r'(app\s*=\s*FastAPI\s*\([^)]*\)\n)'
if re.search(pattern, content):
    content = re.sub(pattern, r'\1' + cors_block, content, count=1)
else:
    print("ERROR: Could not find app = FastAPI()")
    sys.exit(1)

with open('backend/app.py', 'w') as f:
    f.write(content)

print("backend/app.py patched successfully")
