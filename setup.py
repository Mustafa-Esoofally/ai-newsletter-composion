import subprocess
import sys

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"✅ Successfully executed: {command}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing {command}: {e}")
        sys.exit(1)

def main():
    print("🚀 Setting up Composio integrations...")
    
    # List of integrations to add
    integrations = [
        "gmail",
        "tavily"
    ]
    
    for integration in integrations:
        print(f"\n📦 Adding {integration} integration...")
        run_command(f"composio add {integration}")
    
    print("\n✨ Setup complete! All integrations have been added.")

if __name__ == "__main__":
    main()
