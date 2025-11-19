## 🐧 Raspberry Pi Setup (GuidedVision Client)

This guide explains how to run **GuidedVision on the Raspberry Pi** and connect it to the VLM server running on your laptop.

> ✅ Important:
> - The **laptop** (server) and **Raspberry Pi** (client) must be on the **same network / Wi‑Fi (same subnet)**.
> - You must use the **correct IP address of the Pi** for SSH.
> - You must use the **correct IP address of the laptop** in `config.yaml` as `server_url`.

---

### 1️⃣ Find the Raspberry Pi IP from your laptop

On your **laptop**, open a terminal / PowerShell.

First, make sure you’re on the **same Wi‑Fi** as the Raspberry Pi.

List devices on the network:

**Windows (PowerShell):**
```powershell
arp -a
```

**macOS / Linux:**
```bash
arp -a
```

Look for an entry that looks like:

```text
? (10.43.110.57) at xx:xx:xx:xx:xx:xx
```

Here, `10.43.110.57` is an example of the **Raspberry Pi IP address**.

---

### 2️⃣ SSH into the Raspberry Pi

From your **laptop**:

```bash
ssh <USERNAME>@<PI_IP>
```

Example:

```bash
ssh joud@10.43.110.57
```

Enter the Raspberry Pi password when prompted.

If this fails with `connection timed out` or `connection refused`, check that:

- The **IP is correct**.
- Both laptop and Pi are on the **same subnet/network**.
- SSH is enabled on the Pi:

```bash
sudo systemctl status ssh
```

If SSH is not active:

```bash
sudo systemctl enable --now ssh
```

---

### 3️⃣ Go to the Guided_Vision project on the Pi

Once logged into the Pi:

```bash
cd ~/Guided_Vision
cd client_pi
```

(Adjust the path if you cloned the repo somewhere else.)

---

### 4️⃣ Create and activate a virtual environment (first time)

Create venv:

```bash
python3 -m venv .venv
```

If you get an error about `venv`, install it:

```bash
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
```

Activate venv:

```bash
source .venv/bin/activate
```

You should now see `(.venv)` at the beginning of your prompt.

---

### 5️⃣ Install client dependencies (first time)

With venv active and still inside `client_pi`:

```bash
pip install --upgrade pip
pip install -r requirements_pi.txt
```

If `opencv-python` fails to build on the Pi, install it via apt:

```bash
sudo apt update
sudo apt install -y python3-opencv
```

---

### 6️⃣ Configure the server URL (laptop IP) in `config.yaml`

On the Pi, edit the config file:

```bash
nano config.yaml
```

Set `server_url` to your **laptop’s IP**, not `127.0.0.1`:

```yaml
server_url: "http://<LAPTOP_IP>:8000"
```

Example:

```yaml
server_url: "http://10.43.110.49:8000"
```

Keep the other options as needed (camera index, frame interval, etc.).

Save and exit Nano:

- `Ctrl + O`, Enter
- `Ctrl + X`

> 🔁 Reminder:
> - The **Pi** sends frames to `server_url`.
> - Your **laptop** must be running the FastAPI server on that address and port:
>   ```bash
>   cd server
>   uvicorn main:app --host 0.0.0.0 --port 8000
>   ```

---

### 7️⃣ Run the GuidedVision client on the Raspberry Pi

Every time you want to start GuidedVision on the Pi:

1. From your **laptop**, SSH into the Pi (if not already connected):

   ```bash
   ssh <USERNAME>@<PI_IP>
   ```

2. On the Pi:

   ```bash
   cd ~/Guided_Vision/client_pi
   source .venv/bin/activate
   python3 pi_client.py
   ```

You should see logs similar to:

```text
[GuidedVision] pi_client.main() starting... (Camera Module 3 version)
[GuidedVision] Config loaded: {...}
[GuidedVision] Capturing frame from rpicam-jpeg...
[GuidedVision] Caption: 'The image shows a person holding a knife in front of you' (danger=True)
[GuidedVision] SPEAK: knife to your front
```

If `danger=True`, the Raspberry Pi’s audio output (Speaker pHAT or other speaker) will speak the warning.  
If `danger=False`, it prints the caption only (no audio).

---

### 8️⃣ Stop and shut down the Raspberry Pi safely

To stop the client, press:

```text
Ctrl + C
```

To shut down the Raspberry Pi from SSH:

```bash
sudo shutdown -h now
```

Wait until the LEDs stop blinking, then unplug power if needed.
