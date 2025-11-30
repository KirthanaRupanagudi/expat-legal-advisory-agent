"""
VSCode Python Script Launcher for Expat Legal Advisory Agent

This script provides an interactive command-line interface for running
the agent in VSCode without needing Jupyter notebook.

Usage:
    python run_notebook.py
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_environment():
    """Check and setup environment variables."""
    print("🔧 Environment Setup")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv('GOOGLE_API_KEY'):
        print("\n⚠️  GOOGLE_API_KEY not found in environment")
        print("\nOptions:")
        print("1. Set in .env file (create if doesn't exist)")
        print("2. Set in system environment variables")
        print("3. Enter now (temporary for this session)")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '3':
            from getpass import getpass
            api_key = getpass("Enter Google API Key: ")
            if api_key:
                os.environ['GOOGLE_API_KEY'] = api_key
                print("✅ API key set for this session")
            else:
                print("❌ No API key provided. Agent will not work.")
                return False
        else:
            print("\n📝 Please set GOOGLE_API_KEY and restart the script")
            print("\nFor .env file, create .env in project root with:")
            print("GOOGLE_API_KEY=your_key_here")
            return False
    else:
        print(f"✅ GOOGLE_API_KEY found: {os.getenv('GOOGLE_API_KEY')[:10]}...")
    
    # Set Flask key if not present
    if not os.getenv('FLASK_API_KEY'):
        os.environ['FLASK_API_KEY'] = 'vscode-mode-key-12345'
    
    print("\n" + "=" * 60)
    return True


def check_dependencies():
    """Verify all required packages are installed."""
    print("\n📦 Checking Dependencies")
    print("=" * 60)
    
    required = {
        'flask': 'flask',
        'google.generativeai': 'google-generativeai',
        'PyPDF2': 'PyPDF2',
        'docx': 'python-docx',
        'langdetect': 'langdetect',
        'cryptography': 'cryptography',
        'requests': 'requests'
    }
    
    missing = []
    for import_name, package_name in required.items():
        try:
            __import__(import_name.split('.')[0])
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name}")
            missing.append(package_name)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False
    
    print("\n" + "=" * 60)
    return True


def load_document(filepath):
    """Load and extract text from document."""
    from project.tools.tools import extract_pdf_text, extract_docx_text
    
    if not filepath or not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return None
    
    try:
        filepath_lower = filepath.lower()
        if filepath_lower.endswith('.pdf'):
            print(f"📖 Extracting text from PDF: {os.path.basename(filepath)}")
            text = extract_pdf_text(filepath)
        elif filepath_lower.endswith('.docx'):
            print(f"📖 Extracting text from DOCX: {os.path.basename(filepath)}")
            text = extract_docx_text(filepath)
        elif filepath_lower.endswith('.txt'):
            print(f"📖 Reading text file: {os.path.basename(filepath)}")
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            print(f"❌ Unsupported file type: {filepath}")
            print("   Supported: .pdf, .docx, .txt")
            return None
        
        if text:
            print(f"✅ Extracted {len(text)} characters")
            return text
        else:
            print("⚠️  File extracted but contains no text")
            return None
    
    except Exception as e:
        print(f"❌ Error loading document: {e}")
        return None


def interactive_mode():
    """Run interactive Q&A session."""
    from project.main_agent import run_agent
    
    print("\n" + "=" * 60)
    print("🎤 INTERACTIVE MODE")
    print("=" * 60)
    print("\nCommands:")
    print("  - Type your question to ask the agent")
    print("  - 'load <filepath>' to load a document")
    print("  - 'lang <code>' to change response language (en/es/fr/nl/de)")
    print("  - 'show' to display current settings")
    print("  - 'quit' to exit")
    print("\n" + "=" * 60)
    
    # Settings
    document_text = None
    document_path = None
    preferred_language = 'en'
    
    while True:
        try:
            print("\n" + "-" * 60)
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            # Commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            elif user_input.lower().startswith('load '):
                filepath = user_input[5:].strip().strip('"').strip("'")
                loaded_text = load_document(filepath)
                if loaded_text:
                    document_text = loaded_text
                    document_path = filepath
                    print(f"\n✅ Document loaded: {os.path.basename(filepath)}")
                    print(f"   Preview: {document_text[:200]}...")
                continue
            
            elif user_input.lower().startswith('lang '):
                new_lang = user_input[5:].strip().lower()
                if new_lang in ['en', 'es', 'fr', 'nl', 'de']:
                    preferred_language = new_lang
                    lang_names = {
                        'en': 'English', 'es': 'Spanish', 'fr': 'French',
                        'nl': 'Dutch', 'de': 'German'
                    }
                    print(f"\n✅ Response language: {lang_names[new_lang]}")
                else:
                    print("\n❌ Invalid language. Use: en, es, fr, nl, de")
                continue
            
            elif user_input.lower() == 'show':
                print("\n📊 Current Settings:")
                print(f"   Response Language: {preferred_language}")
                if document_path:
                    print(f"   Loaded Document: {os.path.basename(document_path)}")
                    print(f"   Document Size: {len(document_text)} characters")
                else:
                    print(f"   Loaded Document: None")
                continue
            
            # Process question
            print("\n🤔 Processing...")
            
            result = run_agent(
                user_input=user_input,
                document_content=document_text,
                document_language='auto',
                preferred_language=preferred_language
            )
            
            print("\n" + "=" * 60)
            print(f"📊 Confidence: {result.get('confidence', 0):.0%}")
            print("=" * 60)
            print(f"\n🤖 Agent: {result.get('response', 'No response generated')}")
            print("\n" + "=" * 60)
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Try again or type 'quit' to exit")


def simple_query_mode():
    """Single question mode."""
    from project.main_agent import run_agent
    
    print("\n" + "=" * 60)
    print("💬 SIMPLE QUERY MODE")
    print("=" * 60)
    
    # Get question
    question = input("\nYour question: ").strip()
    if not question:
        print("❌ No question provided")
        return
    
    # Optional document
    print("\nLoad document? (press Enter to skip, or enter file path)")
    filepath = input("Document path: ").strip().strip('"').strip("'")
    
    document_text = None
    if filepath:
        document_text = load_document(filepath)
    
    # Language
    print("\nResponse language (en/es/fr/nl/de) [default: en]: ", end='')
    lang = input().strip().lower() or 'en'
    
    # Process
    print("\n🤔 Processing...\n")
    
    try:
        result = run_agent(
            user_input=question,
            document_content=document_text,
            document_language='auto',
            preferred_language=lang
        )
        
        print("=" * 60)
        print(f"📊 Confidence: {result.get('confidence', 0):.0%}")
        print("=" * 60)
        print(f"\n{result.get('response', 'No response generated')}")
        print("\n" + "=" * 60)
    
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🌍 EXPAT LEGAL ADVISORY AGENT - VSCode Mode")
    print("=" * 60)
    
    # Setup
    if not setup_environment():
        return
    
    if not check_dependencies():
        print("\n❌ Please install missing dependencies and restart")
        return
    
    # Import agent
    try:
        from project.main_agent import run_agent
        print("\n✅ Agent loaded successfully")
    except ImportError as e:
        print(f"\n❌ Failed to import agent: {e}")
        print("   Make sure you're running from the project root directory")
        return
    
    # Mode selection
    print("\n" + "=" * 60)
    print("Select Mode:")
    print("  1. Interactive (continuous Q&A)")
    print("  2. Simple Query (single question)")
    print("=" * 60)
    
    choice = input("\nChoice (1 or 2) [default: 1]: ").strip() or '1'
    
    if choice == '1':
        interactive_mode()
    elif choice == '2':
        simple_query_mode()
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    # Try to load .env if available
    try:
        from dotenv import load_dotenv
        env_path = project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print("✅ Loaded .env file")
    except ImportError:
        pass  # python-dotenv not installed, use system env vars
    
    main()
