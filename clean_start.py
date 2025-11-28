import os
import glob

def clean_restart():
    print("🧹 Cleaning cache files...")
    
    # Remove Python cache files
    cache_files = glob.glob('**/*.pyc', recursive=True) + glob.glob('**/__pycache__', recursive=True)
    for file in cache_files:
        if os.path.isfile(file):
            os.remove(file)
            print(f"✅ Removed {file}")
        elif os.path.isdir(file):
            import shutil
            shutil.rmtree(file)
            print(f"✅ Removed {file}/")
    
    print("✅ Cache cleaned!")
    print("🚀 Now run: python app.py")

if __name__ == '__main__':
    clean_restart()