from flask import Flask, render_template
from app.routes.admin import admin_bp
from app.routes.api import api_bp
from app.routes.webhooks import webhooks_bp
from app.models.license import License
from app.models.user import User
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(webhooks_bp)

@app.route('/')
def index():
    return render_template('public/activate.html')

if __name__ == '__main__':
    # Initialize database
    License.init_db()
    User.init_db()
    
    # Create default admin user
    admin = User.get_by_username('admin')
    if not admin:
        admin = User(username='admin', password_hash='admin123', is_admin=True)
        admin.save()
    
    app.run(debug=True, port=5000)