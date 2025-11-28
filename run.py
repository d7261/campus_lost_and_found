from app import create_app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        from models import db
        db.create_all()
        print("=" * 50)
        print("Campus Lost & Found Application")
        print("Database initialized successfully!")
        print("Visit: http://localhost:5000")
        print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)