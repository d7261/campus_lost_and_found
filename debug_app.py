try:
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from models import db
        db.create_all()
        print("✅ Database created successfully!")
        
        # Test if we can query users
        from models import User
        users = User.query.all()
        print(f"✅ Found {len(users)} users in database")
        
        print("🎉 Application is ready!")
        print("🌐 Visit: http://localhost:5000")
        
    app.run(debug=True)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("🔧 Debugging information:")
    import traceback
    traceback.print_exc()