import requests
from pathlib import Path
import time
import zipfile

SERVER_URL = "http://172.184.108.178:8000"
TOKEN = None

def set_token(token: str):
    global TOKEN
    TOKEN = token


def check_and_start_gpuservers():
    headers = {"x-token": TOKEN}
    try:
        status_resp = requests.get(f"{SERVER_URL}/gpuserver-status", headers=headers)
        status_resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Cannot connect to server at {SERVER_URL}: {e}")
    
    server_status = status_resp.json()["details"]
    if not all(server_status.values()):
        print("Warning: gpuservers not running, starting now...")
        start_resp = requests.get(f"{SERVER_URL}/start-gpuservers", headers=headers)
        start_resp.raise_for_status()
        time.sleep(10)


def generate_msa(input_fasta: str, output_dir: str):
    if TOKEN is None:
        raise ValueError("No token is set. Call set_token(TOKEN) before generate_msa().")
    
    check_and_start_gpuservers()

    input_fasta = Path(input_fasta)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_fasta.open("rb") as f:
        files = {'file': (input_fasta.name, f)}
        headers = {"x-token": TOKEN}
        resp = requests.post(f"{SERVER_URL}/submit", files=files, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"Submission failed: {resp.text}")
    
    task_id = resp.json()["task_id"]
    print(f"Job submitted. Task ID: {task_id}. Polling for result...")

    # Poll task status
    while True:
        status_resp = requests.get(f"{SERVER_URL}/task-status/{task_id}", headers=headers)
        status_data = status_resp.json()

        if status_data["status"] == "complete":
            job_id = status_data["job_id"]
            break

        time.sleep(10)

    print(f"Job complete. Downloading result for Job ID: {job_id}")

    # Download zip
    download_url = f"{SERVER_URL}/download/{job_id}"
    output_zip = output_dir / f"{job_id}.zip"
    with requests.get(download_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(output_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print(f"Downloaded: {output_zip}")

    with zipfile.ZipFile(output_zip, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
        print(f"Unzipped contents to: {output_dir}")

    return