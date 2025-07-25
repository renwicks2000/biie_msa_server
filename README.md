# biie_msa_server

A simple Python client for submitting MSA jobs to the BIIE ColabFold server.

This tool lets you run remote ColabFold MSA generation by simply calling:

```python
from biie_msa_server import generate_msa, set_token

set_token("password")  # to get the password to access the server, please contact sean.renwick@immune.engineering

generate_msa("example.fasta", "output_dir", token="your-x-token")
```

## How It Works

1. **GPU Server Check**: Before submitting your job, the client checks if the required `mmseqs gpuserver` processes are running on the server.
   - If not running, it will automatically start them via the server API.

2. **FASTA Submission**: Your `.fasta` file is uploaded via a secure POST request to the server.

3. **Task Queue**: The server adds your job to a background **Celery** task queue to avoid overloading the machine.

4. **ColabFold Execution**: Once dequeued, ColabFold runs on your sequence using the AF3-compatible pairing strategy.

5. **Download & Unzip**: Once complete, the client downloads the result `.zip` file and unpacks it into your specified `output_dir`.

---

## Installation

### Option 1: Local Development Install

```bash
git clone https://github.com/YOUR-LAB/biie_msa_server.git
cd biie_msa_server
pip install -e .
```

### Option 2: pip Install (once published to PyPI)
```bash
pip install biie_msa_server
```

> You will still need to provide your personal x-token manually.

---

## Usage

```python
from biie_msa_server import generate_msa

generate_msa("your_input.fasta", "results_dir", token="your-x-token")
```

### Arguments

| Argument      | Type        | Description                           |
|---------------|-------------|---------------------------------------|
| input_fasta   | str or Path | Path to your FASTA input file         |
| output_dir    | str or Path | Directory to store the MSA result     |
| token         | str         | Your personal x-token for the server  |

---

## Requirements

- Python 3.8+
- `requests` Python package

---

## Notes

- If the remote gpuserver processes are **not running**, the client will attempt to start them automatically.
- If the FastAPI server is unreachable, you’ll get a clear error message.
- All output `.a3m` and `.json` files will be extracted from the zip.

---

## Server Stack Overview

On the server side, this client talks to a stack that includes:

- **FastAPI** (REST API)
- **Celery** (task queue)
- **Redis** (Celery broker and backend)
- **ColabFold** (local execution)
- **Systemd services** ensure:
  - Redis starts on boot
  - Celery worker starts on boot
  - FastAPI (via Uvicorn) starts on boot

This architecture allows for:
- Concurrent job handling
- Stable server load
- Automatic recovery and service availability after VM reboot

For more information or to contribute, please contact the maintainer.
