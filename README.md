# biie_msa_server

A simple Python client for submitting MSA jobs to the BIIE ColabFold server.

This tool lets you run remote ColabFold MSA generation by simply calling:

```python
from biie_msa_server import generate_msa, set_token

set_token("password")  # to get the password to access the server, please contact sean.renwick@immune.engineering

generate_msa("example.fasta", "output_dir")
```

## How It Works

1. **GPU Server Check**: Before submitting your job, the client checks if the required `mmseqs gpuserver` processes are running on the server.
   - If not running, it will automatically start them via the server API.

2. **FASTA Submission**: Your `.fasta` file is uploaded via a secure POST request to the server.

3. **Task Queue**: The server adds your job to a background **Celery** task queue to avoid overloading the machine.

4. **ColabFold Execution**: Once dequeued, ColabFold runs on your sequence using the AF3-compatible pairing strategy.

5. **Download & Unzip**: Once complete, the client downloads the result `.zip` file and unpacks it into your specified `output_dir`.

6. **Redundancy Handling**: If an `.a3m` or `.json` file already exists in the expected output directory, the job is skipped to avoid recomputation.


---

## Installation

```bash
pip install git+https://github.com/renwicks2000/biie_msa_server.git
```

> You will still need to provide the x-token manually, as shown in usage.

---

## Usage

```python
from biie_msa_server import generate_msa, set_token
from dotenv import load_dotenv

load_dotenv()
set_token(os.getenv("MSA_SERVER_PW")) # to get the password to access the server, please contact sean.renwick@immune.engineering

generate_msa("example.fasta", "output_dir")
```

This will generate an AF3-compatible .json and an MSA .a3m for each protein chain in the FASTA file, as well as a zip folder of all files in the output_dir.

As shown above, we suggest saving the password in a local .env file in the root folder that isn't pushed to git to preserve security. Format your local .env like this:

```bash
MSA_SERVER_PW=Password
```
and make sure the .env file is in your .gitignore.

### Arguments

| Argument      | Type        | Description                           |
|---------------|-------------|---------------------------------------|
| input_fasta   | str or Path | Path to your FASTA input file         |
| output_dir    | str or Path | Directory to store the MSA result     |

---

## Requirements

- Python 3.8+
- `requests` Python package

---

## Notes

- Please make sure the Azure VM ("cpuonlyvm") hosting the server is running.
- On startup, the VM should automatically start:
  - Redis
  - Celery worker
  - FastAPI (Uvicorn)
- The first few MSAs may take longer to generate due to GPU warm-up and database caching.
- If the `gpuserver` processes are **not running**, the client will attempt to restart them automatically.
- If generation fails, the client retries once after restarting the gpuservers before failing.

---

## Server Stack Overview

This client talks to a server running:

- **FastAPI** (REST interface)
- **Celery** (task queue for job handling)
- **Redis** (Celery broker/backend)
- **ColabFold** (run on GPU with AF3-compatible flags)
- **Systemd** services on the VM for Redis, Celery, and Uvicorn

This setup enables:

- Multi-user safe submissions
- Centralized GPU resource management
- Recovery from GPU stalls or stale processes

---

## Troubleshooting

### gpuserver failed to start

This usually happens if the VM failed to mount the database directory on boot. This should ideally be done automatically, but may fail.

Fix with:

```bash
sudo mkdir /data/databases
sudo mount -a
```

### "Zero error" or silent MSA failures

After ~60 jobs, the GPU cache or gpuserver state may corrupt.

The client already automatically restarts the gpuservers on failure to circumvent this failure. If this doesn't work, you may need to completely restart the Azure VM.

---

## Feedback
For server access or bug reports, please contact [Sean Renwick](mailto:sean.renwick@immune.engineeering)