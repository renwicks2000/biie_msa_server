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
        print("[WARN] gpuservers not running, starting now...")
        print("[INFO] Please note that after starting the server, the first run is typically very slow (~1hr)!")
        print("[INFO] Subsequent submissions typically take 3-4 minutes.")
        start_resp = requests.get(f"{SERVER_URL}/start-gpuservers", headers=headers)
        start_resp.raise_for_status()
        time.sleep(30)

        # Recheck
        status_resp = requests.get(f"{SERVER_URL}/gpuserver-status", headers=headers)
        server_status = status_resp.json()["details"]
        if not all(server_status.values()):
            raise RuntimeError(f"gpuserver failed to start: {server_status}")


def restart_gpuservers():
    headers = {"x-token": TOKEN}
    print("[INFO] Terminating stale gpuserver processes...")
    requests.post(f"{SERVER_URL}/terminate-gpuservers", headers=headers)

    # Wait until all are gone
    timeout = 120
    start_time = time.time()
    while True:
        status_resp = requests.get(f"{SERVER_URL}/gpuserver-status", headers=headers)
        server_status = status_resp.json()["details"]
        if not any(server_status.values()):
            break
        if time.time() - start_time > timeout:
            raise RuntimeError("Timeout: gpuserver processes did not fully terminate.")
        time.sleep(5)

    print("[INFO] Restarting gpuserver processes...")
    resp = requests.get(f"{SERVER_URL}/start-gpuservers", headers=headers)
    resp.raise_for_status()
    print("[INFO] gpuserver processes restarted. Waiting briefly...")
    time.sleep(30)


def submit_job(input_fasta: Path):
    headers = {"x-token": TOKEN}
    with input_fasta.open("rb") as f:
        files = {'file': (input_fasta.name, f)}
        resp = requests.post(f"{SERVER_URL}/submit", files=files, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"Submission failed: {resp.text}")
    return resp.json()["task_id"]


def generate_msa(input_fasta: str, output_dir: str):
    if TOKEN is None:
        raise ValueError("No token is set. Call set_token(TOKEN) before generate_msa().")
    
    check_and_start_gpuservers()

    input_fasta = Path(input_fasta)
    output_dir = Path(output_dir)
    output_folder = output_dir / f"{input_fasta.stem}"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    existing_files = list(output_folder.glob("*.a3m")) + list(output_folder.glob("*.json"))
    if existing_files:
        print(f"[SKIP] MSA already exists for {input_fasta.name}. Skipping generation.")
        return output_folder
    
    headers = {"x-token": TOKEN}
    start_time = time.time()
    task_id = submit_job(input_fasta)
    print(f"Job submitted for {input_fasta.name}. Task ID: {task_id}. Waiting for result...")

    retried = False

    # Poll task status
    while True:
        status_resp = requests.get(f"{SERVER_URL}/task-status/{task_id}", headers=headers)
        status_data = status_resp.json()

        if status_data["status"] == "complete":
            job_id = status_data["job_id"]
            break
        elif status_data["status"] == "failed":
            if not retried:
                print("[WARN] MSA generation failed. Attempting one restart of gpuserver and resubmission...")
                restart_gpuservers()
                print("[INFO] gpuservers have been restarted. Please note that the gpus require some time to warm up and the first MSA run will be slow.")
                task_id = submit_job(input_fasta)
                retried = True
                print(f"[INFO] Job resubmitted. New Task ID: {task_id}")
                continue
            else:
                raise RuntimeError(f"[ERROR] MSA generation failed permanently: {status_data.get('error', 'Unknown error')}")

        time.sleep(10)
    end_time = time.time()
    minutes, seconds = divmod(int(end_time-start_time), 60)
    print(f"Job complete. MSA took {minutes}m {seconds}s.\nDownloading result for Job ID: {job_id}")

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
        zip_ref.extractall(output_folder)
        output_zip.unlink()
        print(f"Unzipped contents to: {output_folder}")

    return output_folder