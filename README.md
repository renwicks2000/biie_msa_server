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

set_token("password")  # to get the password to access the server, please contact sean.renwick@immune.engineering

generate_msa("example.fasta", "output_dir")
```

This will generate an AF3-compatible .json and an MSA .a3m for each protein chain in the fasta, as well as a zip folder of all files in the output_dir. To use the generate_msa() function, you only need to set the password once.

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

- Please make sure the "cpuonlyvm" on Azure is running. This is the host of the server. Upon startup, all necessary services should automatically be triggered, making it possible to generate MSAs.
- The first few MSAs may take longer to generate as the GPU needs to be primed with the database indices before running.
- If the remote gpuserver processes are **not running**, the client will attempt to start them automatically.
- If the FastAPI server is unreachable, you’ll get a clear error message.
- All output `.a3m` and `.json` files will be extracted from the zip into the output_dir.

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

---
## Troubleshooting
There are some known errors with the server, and some haven't been fixed yet. Here are some temporary fixes in the meantime.

### gpuserver failed to start
This is likely because the VM failed to automatically mount the database to /mnt/databases. To fix, please run this on the VM running the server:
```bash
sudo mkdir /data/databases
sudo mount -a
```

### Zero error
After ~40 MSA generations, the server begins to fail on all MSA generations. This is likely due to a cache issue, or an issue with how jobs are stored in the queue that isn't getting cleaned up properly.