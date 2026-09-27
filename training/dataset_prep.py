"""
NexusAI - Domain Dataset Generator & Formatter for LoRA Fine-Tuning
Specialization: Enterprise Cloud Architecture, Kubernetes, Distributed Systems & AI DevOps
Supports output in:
- Llama-3 Chat Template format (<|start_header_id|>system/user/assistant<|end_header_id|>)
- ShareGPT multi-turn conversation format
- Alpaca instruction/input/output format
"""

import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any

# System prompt defining the persona and niche expertise
SYSTEM_PROMPT = """You are NexusAI, an elite Enterprise Cloud and AI DevOps Principal Architect.
You possess deep, authoritative expertise in:
1. Distributed systems, high-availability Kubernetes cluster architecture, and service mesh (Istio/Linkerd).
2. Infrastructure as Code (Terraform, OpenTofu, Pulumi, Ansible) and GitOps (ArgoCD, Flux).
3. LLM deployment optimization (vLLM, TensorRT-LLM, Triton Inference Server, QLoRA, DeepSpeed, Ray).
4. Production observability (OpenTelemetry, Prometheus, Grafana, Loki) and SRE incident mitigation.
5. Cloud security compliance (Zero-Trust, IAM least privilege, SOC2, HIPAA, Kubernetes CIS benchmarks).

When answering:
- Provide production-grade, immediately deployable code/manifests with clear comments.
- Quantify engineering trade-offs (latency, compute cost, memory footprint, throughput).
- Emphasize fault tolerance, self-healing architectures, and security best practices."""

# Curated high-impact domain samples demonstrating architecture, code, and tool reasoning
DOMAIN_SAMPLES: List[Dict[str, Any]] = [
    {
        "instruction": "How do you calculate the exact GPU VRAM requirement for serving a Llama-3-8B model with vLLM at 16-bit vs 4-bit quantization with a 4096 context window and concurrency of 16?",
        "input": "",
        "output": """To calculate the exact GPU VRAM requirement for serving Llama-3-8B in vLLM, we calculate the sum of Model Weights VRAM, KV Cache VRAM, and Runtime Activation Overhead:

### 1. Model Weights Memory:
- **16-bit (bfloat16/float16)**:
  $$M_{\\text{weights}} = 8.03 \\times 10^9 \\text{ params} \\times 2 \\text{ bytes} \\approx 16.06 \\text{ GB}$$
- **4-bit (AWQ / GPTQ / bitsandbytes)**:
  $$M_{\\text{weights}} = 8.03 \\times 10^9 \\text{ params} \\times 0.5 \\text{ bytes} + \\text{layer overhead} \\approx 4.6 - 5.1 \\text{ GB}$$

### 2. KV Cache Memory (per concurrent request):
Llama-3-8B uses Grouped-Query Attention (GQA):
- Number of layers ($L$) = 32
- Key-Value heads ($H_{kv}$) = 8
- Head dimension ($d_h$) = 128
- Context length ($S$) = 4,096 tokens
- Data precision = 2 bytes (FP16/BF16)

$$\\text{KV Size per Token} = 2 \\times L \\times H_{kv} \\times d_h \\times 2 \\text{ bytes}$$
$$= 2 \\times 32 \\times 8 \\times 128 \\times 2 = 131,072 \\text{ bytes} \\approx 0.125 \\text{ MB per token}$$

For 4,096 tokens:
$$\\text{KV Cache per Stream} = 4,096 \\times 0.125 \\text{ MB} = 512 \\text{ MB (0.5 GB)}$$

For concurrency of 16:
$$M_{\\text{KV}} = 16 \\times 0.5 \\text{ GB} = 8.0 \\text{ GB}$$

### 3. vLLM Activation & PagedAttention Overhead:
- PyTorch CUDA Context & vLLM buffers: $\\sim 1.5 - 2.0 \\text{ GB}$.

### Total VRAM Summary:
- **16-bit BF16**: $16.06 + 8.0 + 2.0 = \\mathbf{26.06\\text{ GB}}$ $\\rightarrow$ Requires an **A10G (24GB is borderline, 32GB V100/40GB A100 recommended)**.
- **4-bit AWQ**: $5.1 + 8.0 + 2.0 = \\mathbf{15.1\\text{ GB}}$ $\\rightarrow$ Fits comfortably on a single **RTX 3090 / RTX 4090 / A10G (24GB)** with room for higher concurrency.

vLLM command for 4-bit serving:
```bash
python -m vllm.entrypoints.openai.api_server \\
    --model meta-llama/Meta-Llama-3-8B-Instruct \\
    --quantization awq \\
    --max-model-len 4096 \\
    --gpu-memory-utilization 0.90 \\
    --tensor-parallel-size 1
```"""
    },
    {
        "instruction": "Write a zero-downtime, production-ready Kubernetes Deployment manifest for an LLM inference service with rolling updates, HPA based on custom Prometheus metrics, and security hardening.",
        "input": "",
        "output": """Here is an enterprise-grade Kubernetes manifest implementing zero-downtime rolling deployment, non-root security context, pod disruption budget, and horizontal pod autoscaling.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-inference-service
  namespace: ai-production
  labels:
    app.kubernetes.io/name: llm-inference
    app.kubernetes.io/part-of: nexus-platform
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Guarantees zero downtime during rolling deployments
  selector:
    matchLabels:
      app: llm-inference
  template:
    metadata:
      labels:
        app: llm-inference
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values: ["llm-inference"]
                topologyKey: "kubernetes.io/hostname"
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: inference-engine
          image: vllm/vllm-openai:v0.4.2
          imagePullPolicy: IfNotPresent
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          args:
            - "--model=meta-llama/Meta-Llama-3-8B-Instruct"
            - "--gpu-memory-utilization=0.92"
            - "--max-model-len=4096"
            - "--port=8000"
          ports:
            - containerPort: 8000
              name: http
          resources:
            limits:
              nvidia.com/gpu: "1"
              memory: 32Gi
              cpu: "8"
            requests:
              nvidia.com/gpu: "1"
              memory: 24Gi
              cpu: "4"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 45
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 60
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 4
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: llm-inference-pdb
  namespace: ai-production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: llm-inference
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: llm-inference-hpa
  namespace: ai-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-inference-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
    - type: External
      external:
        metric:
          name: vllm_num_requests_waiting
        target:
          type: Value
          averageValue: "5"
```"""
    },
    {
        "instruction": "Explain how to implement fine-grained LoRA adaptation using HuggingFace PEFT without causing catastrophic forgetting, and outline the exact hyperparameter selections.",
        "input": "",
        "output": """To avoid catastrophic forgetting while performing Low-Rank Adaptation (LoRA) on foundational LLMs like Llama-3-8B or Mistral-7B, adhere to these architectural principles:

### 1. Target Projections (Target Modules):
Many early scripts only adapted `q_proj` and `v_proj`. Modern research (Hu et al. & QLoRA paper) proves that adapting **all linear layers** yields the highest domain retention while preventing distortion of foundational capabilities:
- Attention layers: `["q_proj", "k_proj", "v_proj", "o_proj"]`
- MLP/FFN layers: `["gate_proj", "up_proj", "down_proj"]`

### 2. Hyperparameter Configuration:
- **Rank ($r$)**: `16` or `32`. Rank 16 offers optimal expressiveness for domain adaptation without parameter bloat.
- **LoRA Alpha ($\\alpha$)**: Set to **$2 \\times r$** (e.g., $r=16, \\alpha=32$). This maintains the gradient scaling ratio $\\frac{\\alpha}{r} = 2.0$.
- **LoRA Dropout**: `0.05` to prevent overfitting on specialized jargon.
- **Learning Rate**: `2e-4` for 4-bit QLoRA, or `5e-5` for 16-bit LoRA. Use a **Cosine Annealing** schedule with 3% warmup steps.
- **Weight Decay**: `0.01` to regularize linear adapter adapters.

### 3. Mitigating Catastrophic Forgetting:
1. **Instruction Replay Ratio**: Mix **15-20% general conversational/reasoning data** (e.g. OpenHermes or UltraChat) into your niche domain dataset.
2. **Loss Masking**: Mask user prompts in the loss calculation (`DataCollatorForCompletionOnlyLM`) so gradients are calculated exclusively on domain-accurate assistant responses.
3. **NEFTune (Noisy Embeddings)**: Add uniform noise to the embedding layer with `neftune_noise_alpha=5` during SFT to dramatically boost generalization."""
    },
    {
        "instruction": "Provide a complete Terraform module to provision an Amazon EKS cluster with managed GPU node groups (g5.2xlarge with A10G) and NVIDIA GPU operator pre-installed.",
        "input": "",
        "output": """Here is the complete Terraform module using modern AWS provider and EKS module:

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.45"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
  }
}

variable "cluster_name" {
  type    = string
  default = "nexus-ai-cluster"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.8"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"

  cluster_endpoint_public_access  = true
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    # System node group for monitoring, ingress, and core controllers
    system_nodes = {
      instance_types = ["m6i.xlarge"]
      min_size       = 2
      max_size       = 4
      desired_size   = 2
      labels = {
        role = "system"
      }
    }

    # GPU Worker group for vLLM & LLM inference workloads
    gpu_inference_nodes = {
      instance_types = ["g5.2xlarge"] # 1x NVIDIA A10G (24GB VRAM), 8 vCPU, 32GB RAM
      ami_type       = "AL2_x86_64_GPU"
      min_size       = 1
      max_size       = 5
      desired_size   = 2

      taints = {
        gpu = {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }

      labels = {
        "accelerator" = "nvidia-a10g"
        "workload"    = "inference"
      }

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 150 # Large disk for container images & model weights
            volume_type           = "gp3"
            iops                  = 3000
            throughput            = 125
            delete_on_termination = true
          }
        }
      }
    }
  }
}

# Install NVIDIA GPU Operator via Helm
resource "helm_release" "nvidia_gpu_operator" {
  name             = "gpu-operator"
  repository       = "https://helm.ngc.nvidia.com/nvidia"
  chart            = "gpu-operator"
  version          = "v23.9.2"
  namespace        = "gpu-operator"
  create_namespace = true

  set {
    name  = "operator.defaultRuntime"
    value = "containerd"
  }
  set {
    name  = "toolkit.enabled"
    value = "true"
  }

  depends_on = [module.eks]
}
```"""
    },
    {
        "instruction": "How do you configure an ArgoCD Application to deploy a multi-stage microservice using Helm and Kustomize overlays?",
        "input": "",
        "output": """To deploy with ArgoCD using Helm for base templating combined with Kustomize overlays for environment-specific patches (dev, staging, prod), use ArgoCD's native **Helm + Kustomize integration** via `argocd.argoproj.io/v1alpha1 Application`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nexus-ai-production
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: 'https://github.com/organization/nexus-gitops.git'
    targetRevision: main
    path: environments/production
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: ai-production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PruneLast=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Directory Structure inside GitOps repository:
```
environments/
└── production/
    ├── kustomization.yaml
    └── patch-replicas.yaml
```

### `environments/production/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

helmCharts:
  - name: llm-service
    repo: https://charts.nexus.io
    version: 1.4.0
    releaseName: nexus-llm
    namespace: ai-production
    valuesFile: values-prod.yaml

patchesStrategicMerge:
  - patch-replicas.yaml
```"""
    }
]

def format_llama3_chat(system_prompt: str, instruction: str, input_text: str, output_text: str) -> str:
    """Format into standard Llama-3 instruction chat template."""
    user_content = f"{instruction}\n\nContext:\n{input_text}" if input_text else instruction
    formatted = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{system_prompt.strip()}<|eot_id|>\n"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_content.strip()}<|eot_id|>\n"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{output_text.strip()}<|eot_id|>"
    )
    return formatted

def generate_datasets(output_dir: str = "training/data", val_ratio: float = 0.2):
    """Generates train and validation sets in JSONL format."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    formatted_samples = []
    for sample in DOMAIN_SAMPLES:
        llama3_text = format_llama3_chat(
            SYSTEM_PROMPT,
            sample["instruction"],
            sample["input"],
            sample["output"]
        )
        formatted_samples.append({
            "instruction": sample["instruction"],
            "input": sample["input"],
            "output": sample["output"],
            "system": SYSTEM_PROMPT,
            "text": llama3_text
        })
        
    # Split into train and validation
    val_count = max(1, int(len(formatted_samples) * val_ratio))
    val_set = formatted_samples[:val_count]
    train_set = formatted_samples[val_count:]
    if not train_set:
        train_set = formatted_samples
        
    train_file = out_path / "train.jsonl"
    val_file = out_path / "val.jsonl"
    
    with open(train_file, "w", encoding="utf-8") as f:
        for item in train_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(val_file, "w", encoding="utf-8") as f:
        for item in val_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"Successfully generated datasets:")
    print(f"  - Training samples:   {len(train_set)} -> {train_file}")
    print(f"  - Validation samples: {len(val_set)} -> {val_file}")
    return train_file, val_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare SFT Dataset for LoRA Fine-Tuning")
    parser.add_argument("--output_dir", type=str, default="training/data", help="Output directory")
    parser.add_argument("--val_ratio", type=float, default=0.2, help="Validation split ratio")
    args = parser.parse_args()
    
    generate_datasets(args.output_dir, args.val_ratio)
