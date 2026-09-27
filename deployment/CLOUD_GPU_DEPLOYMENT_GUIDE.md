# NexusAI Cloud GPU & Infrastructure Deployment Guide

This guide details how to deploy NexusAI on production cloud GPU instances (RunPod, Lambda Labs, AWS EC2, or Hugging Face Spaces).

---

## 1. RunPod Deployment (Recommended for Cost & Simplicity)

### Step 1: Launch GPU Pod
1. In the RunPod console, select **Secure Cloud** or **Community Cloud**.
2. Select an instance with an **NVIDIA RTX 4090 (24GB)** or **NVIDIA A10G / A40 / A100**.
3. Choose the template: `RunPod PyTorch 2.2.0 (CUDA 12.1)`.
4. Ensure volume disk size is set to at least **50 GB**.
5. Expose HTTP ports `8000` (FastAPI) and `3000` (Frontend).

### Step 2: Clone & Launch Model Fine-Tuning or Serving
```bash
git clone https://github.com/your-username/nexus-ai-chatbot.git
cd nexus-ai-chatbot

# 1. Prepare dataset & run QLoRA fine-tuning
pip install -r training/requirements_training.txt
python training/dataset_prep.py
python training/train_lora.py --epochs 3 --batch_size 2 --r 16

# 2. Merge LoRA adapter for vLLM
python training/merge_lora.py \
  --base_model meta-llama/Meta-Llama-3-8B-Instruct \
  --adapter_dir training/checkpoints/nexus_lora_v1 \
  --output_dir /workspace/models/nexus_cloud_v1_merged

# 3. Launch high-throughput vLLM engine
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model /workspace/models/nexus_cloud_v1_merged \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096 \
  --port 8001 &
```

### Step 3: Run NexusAI Application Stack
```bash
# In backend:
cd backend
pip install -r requirements.txt
export INFERENCE_MODE="vllm"
export LLM_API_BASE="http://localhost:8001/v1"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# In frontend:
cd ../frontend
npm ci
npm run build
npm run preview -- --host 0.0.0.0 --port 3000
```

---

## 2. Lambda Labs Deployment

1. Launch a `1x A10 (24GB)` or `1x A100 (40GB)` instance.
2. SSH into your instance:
   ```bash
   ssh ubuntu@<LAMBDA_IP>
   ```
3. Run the automated Docker Compose stack with GPU profile:
   ```bash
   git clone https://github.com/your-username/nexus-ai-chatbot.git
   cd nexus-ai-chatbot/deployment
   docker compose --profile gpu up -d
   ```

---

## 3. AWS EC2 GPU Deployment (g5.2xlarge with NVIDIA A10G)

### Prerequisites:
- AMI: **Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.2 (Ubuntu 22.04)**
- Instance Type: `g5.2xlarge` (1x A10G 24GB VRAM, 8 vCPUs, 32GB RAM)
- EBS Volume: 120GB gp3 (3000 IOPS, 125 MB/s)
- Security Group: Allow TCP `80`, `443`, `8000`, `3000`, `22`.

### Initialization Script (User Data):
```bash
#!/bin/bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

---

## 4. Hugging Face Spaces Deployment

For lightweight or serverless deployment on Hugging Face Spaces:
1. Create a new Space with the **Docker SDK**.
2. Select **T4-medium** or **A10G-small** GPU hardware.
3. Push the `backend/Dockerfile` and project contents.
4. Set secret environment variables in Space Settings:
   - `INFERENCE_MODE`: `openai` or `vllm`
   - `LLM_API_KEY`: your API token
   - `SECRET_KEY`: random 64-character JWT string
