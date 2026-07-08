import os
import sys
import unittest

# Adjust path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import Config
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.models.job import Job
from app.models.document import Document
from app.utils.jwt_helper import generate_access_token, decode_token
from app.routes.video_summary import detect_provider
from app.services.transcript_cleaner import TranscriptCleaner

class VideoSummarizerTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Run database table creation
        print("\n--- 1. Testing DB Tables Creation ---")
        try:
            Base.metadata.create_all(bind=engine)
            print("PostgreSQL tables successfully verified/created.")
        except Exception as e:
            print(f"PostgreSQL connection/creation failed: {e}")
            print("Please ensure your DATABASE_URL in .env is correct and PostgreSQL is running.")
            cls.db_available = False
            return
        cls.db_available = True

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not available")
        self.db = SessionLocal()

    def tearDown(self):
        if self.db_available:
            self.db.close()

    def test_user_creation_and_jwt(self):
        print("\n--- 2. Testing User Creation & JWT ---")
        # Check if test user exists, otherwise create
        email = "verification_test@example.com"
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            self.db.delete(user)
            self.db.commit()
            
        user = User(
            email=email,
            full_name="Verification User",
            role="AppUser"
        )
        user.set_password("password123")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        self.assertIsNotNone(user.id)
        self.assertTrue(user.check_password("password123"))
        
        # Test JWT signing
        token = generate_access_token(user.id, user.role)
        self.assertIsNotNone(token)
        
        # Test JWT decoding
        decoded = decode_token(token)
        self.assertEqual(decoded['user_id'], user.id)
        self.assertEqual(decoded['role'], user.role)
        print("User creation, password validation, and JWT verification passed.")

    def test_provider_detection(self):
        print("\n--- 3. Testing Downloader Provider Detection ---")
        self.assertEqual(detect_provider("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "youtube")
        self.assertEqual(detect_provider("https://youtu.be/dQw4w9WgXcQ"), "youtube")
        self.assertEqual(detect_provider("https://vimeo.com/823924"), "vimeo")
        self.assertEqual(detect_provider("https://drive.google.com/file/d/12345/view"), "google_drive")
        self.assertEqual(detect_provider("https://www.dropbox.com/s/abcdef/video.mp4?dl=0"), "dropbox")
        self.assertEqual(detect_provider("https://1drv.ms/v/s!Abcdef"), "onedrive")
        self.assertEqual(detect_provider("https://example.com/assets/my_video.mp4"), "direct_video")
        
        with self.assertRaises(ValueError):
            detect_provider("https://example.com/some_page")
        print("URL provider detection mappings verified.")

    def test_transcript_cleaning(self):
        print("\n--- 4. Testing Transcript Cleaning Logic ---")
        cleaner = TranscriptCleaner()
        
        # Test filler words removal
        raw_text = "So basically, this is uh like a video text, um you know, ah about programming."
        cleaned = cleaner.clean_text(raw_text)
        self.assertNotIn("uh", cleaned)
        self.assertNotIn("um", cleaned)
        self.assertNotIn("you know", cleaned)
        
        # Test repetition removal
        rep_text = "hello world hello world coding helper coding helper"
        no_rep = cleaner.remove_internal_repetition(rep_text)
        self.assertEqual(no_rep, "hello world coding helper")
        
        # Test short segments merge
        segments = [
            {"start": "00:00:00.000", "end": "00:00:10.000", "start_s": 0.0, "end_s": 10.0, "text": "This is segment one."},
            {"start": "00:00:10.000", "end": "00:00:20.000", "start_s": 10.0, "end_s": 20.0, "text": "And this is segment two."}
        ]
        # Merge with min_paragraph_duration=15.0
        merged = cleaner.merge_segments(segments, min_paragraph_duration=15.0)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['text'], "This is segment one. And this is segment two.")
        print("Transcript text cleaning and segment merging verified.")

if __name__ == '__main__':
    unittest.main()
