# fix_app.py
import os

# Read the current app.py
with open('app.py', 'r') as f:
    content = f.read()

# Add import if missing
if 'import os' not in content:
    # Find first import and add after it
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            lines.insert(i + 1, 'import os')
            break
    
    content = '\n'.join(lines)

# Add secret key after Flask app creation
if 'app = Flask(__name__)' in content and 'app.secret_key' not in content:
    content = content.replace(
        'app = Flask(__name__)',
        'app = Flask(__name__)\napp.secret_key = os.environ.get(\'SECRET_KEY\') or \'quantum-nexus-mt5-journal-secret-key-2024\''
    )

# Write back
with open('app.py', 'w') as f:
    f.write(content)

print("✅ Secret key added to app.py")