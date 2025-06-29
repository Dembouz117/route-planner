from dotenv import load_dotenv
import os

# Load .env file from multiple possible locations
env_loaded = False
env_paths = [".env", "backend/.env", "../.env"]
def check_envs():
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            print(f"✅ Loaded .env from: {env_path}")
            
            return True

def load_env():
    loaded = check_envs()
    print("🔍 Checking for .env file...")
    if not loaded:
        print("⚠️ No .env file found, using system environment variables")