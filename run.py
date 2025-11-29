#!/usr/bin/env python3
"""
Simple script to run the English to Local Languages Translator
"""

import subprocess
import sys
import os

#def install_requirements():
#    """Install required packages"""
#    try:
#        print("Installing required packages...")
#        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
#        print("✅ Requirements installed successfully!")
#    except subprocess.CalledProcessError as e:
#        print(f"❌ Error installing requirements: {e}")
#        sys.exit(1)

def check_csv_files():
    """Check if CSV files exist"""
    # Add your actual CSV filenames here
    possible_files = [
        "english_to_haya_sukuma_nyakyusa 2.csv",
        "english_to_haya_sukuma_nyakyusa.csv"
        #"english_to_haya_sukuma_nyakyusa_3.csv",
        # Add your other uploaded CSV files here
        # "your_second_file.csv",
        # "your_third_file.csv"
    ]
    
    found_files = []
    missing_files = []
    
    print("🔍 Checking for CSV files...")
    
    for file in possible_files:
        if os.path.exists(file):
            found_files.append(file)
            print(f"✅ Found CSV file: {file}")
        else:
            missing_files.append(file)
            print(f"❌ Missing CSV file: {file}")
    
    # Summary
    print(f"\n📊 CSV Files Summary:")
    print(f"✅ Found: {len(found_files)} files")
    print(f"❌ Missing: {len(missing_files)} files")
    
    if found_files:
        print(f"\n📁 Available files:")
        for file in found_files:
            print(f"  - {file}")
        
        if missing_files:
            print(f"\n⚠️  Missing files:")
            for file in missing_files:
                print(f"  - {file}")
            print("Note: The system will work with available files only")
        
        return True
    else:
        print("\n❌ No CSV files found!")
        print("Please ensure at least one of these files exists:")
        for file in possible_files:
            print(f"  - {file}")
        return False

def run_server():
    """Run the FastAPI server"""
    try:
        print("\n🚀 Starting the translator server...")
        print("🌐 Server will be available at: http://localhost:8000")
        print("📋 API documentation: http://localhost:8000/api/docs")
        print("📊 CSV info endpoint: http://localhost:8000/csv-info")
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print("🚀 English to Local Languages Translator")
    print("=" * 50)
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found!")
        sys.exit(1)
    
    # Check if main.py exists
    if not os.path.exists("main.py"):
        print("❌ main.py not found!")
        sys.exit(1)
    
    # Check CSV files (now supports multiple files)
    if not check_csv_files():
        sys.exit(1)
    
    # Install requirements
    # install_requirements()
    
    # Run server
    run_server()

if __name__ == "__main__":
    main()