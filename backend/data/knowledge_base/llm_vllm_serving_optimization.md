# Nexus Enterprise vLLM & LLM Serving Optimization Guide

## Architecture of PagedAttention
PagedAttention divides the KV cache into non-contiguous physical memory blocks rather than pre-allocating contiguous memory pools. This eliminates external fragmentation and brings memory waste down from 60-80% to under 4%.

## Key vLLM Flags for Production
- `--gpu-memory-utilization`: Set to `0.90` - `0.92`. Leaving 8-10% headroom prevents Out-Of-Memory (OOM) errors during rapid burst requests and CUDA activation spikes.
- `--max-model-len`: Explicitly cap to required window (e.g. 4096 or 8192) to maximize KV cache blocks available for concurrent requests.
- `--tensor-parallel-size`: Match the number of physical GPUs (e.g., 2 for dual A10G, 4 for 4x A100).
- `--enable-prefix-caching`: Enables automatic KV cache sharing for common system prompts across independent sessions, reducing TTFT (Time To First Token) by up to 80%.

## Quantization Comparison: AWQ vs GPTQ vs FP8
- **AWQ (Activation-aware Weight Quantization)**: Preserves the top 1% salient weights in FP16 while quantizing the rest to 4-bit. Outperforms GPTQ on conversational coherence and instruction following.
- **FP8 (Floating Point 8)**: Native support on NVIDIA Ada Lovelace (RTX 4090, L4, L40) and Hopper (H100). Delivers 2x throughput compared to FP16 with negligible accuracy drop (<0.2% perplexity change).
