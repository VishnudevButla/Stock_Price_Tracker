from app import app
from models import db, User, StockDetails, SavedList

with app.app_context():

    # Test 1 — create a dummy user
    test_user = User(
        username="testuser",
        email="test@test.com",
        password="dummy_hash"
    )
    db.session.add(test_user)
    db.session.commit()
    print("User created:", test_user)

    # Test 2 — read it back from the database
    fetched = User.query.filter_by(username="testuser").first()
    print("User fetched from DB:", fetched)

    # Test 3 — delete it (cleanup)
    db.session.delete(fetched)
    db.session.commit()
    print("User deleted. DB is clean.")

    print("\nAll tests passed. models.py is working correctly.")
