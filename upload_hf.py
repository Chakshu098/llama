import os
import argparse
from huggingface_hub import HfApi

def upload(repo_id: str, token: str, local_path: str):
    api = HfApi()
    print(f"[*] Starting upload to {repo_id}...")
    
    # Files to ignore
    ignore_patterns = [
        ".venv/*",
        "dashboard-v3/node_modules/*",
        "**/__pycache__/*",
        ".git/*",
        "*.pyc",
        ".env"
    ]
    
    try:
        api.upload_folder(
            folder_path=local_path,
            repo_id=repo_id,
            repo_type="space",
            token=token,
            ignore_patterns=ignore_patterns
        )
        print("[+] Upload Complete! Check your Space at: https://huggingface.co/spaces/" + repo_id)
    except Exception as e:
        print(f"[!] Error during upload: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Chakshu328/llama-ir", help="HF Repo ID")
    parser.add_argument("--token", required=True, help="HF Access Token")
    args = parser.parse_args()
    
    upload(args.repo, args.token, ".")
