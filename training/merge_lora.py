"""
NexusAI - LoRA Adapter Merger
Merges fine-tuned LoRA weights back into the 16-bit base model
and exports a standalone checkpoint optimized for vLLM and TensorRT-LLM.
"""

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NexusAI-Merger")

def merge_and_export(
    base_model_name: str,
    adapter_dir: str,
    output_dir: str,
    device: str = "cpu"
):
    """Merges LoRA adapter into base model weights."""
    logger.info(f"Base model: {base_model_name}")
    logger.info(f"LoRA adapter: {adapter_dir}")
    logger.info(f"Output merged model: {output_dir}")

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        return False

    logger.info("Loading base model in FP16...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16,
        device_map=device,
        trust_remote_code=True
    )

    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(adapter_dir, trust_remote_code=True)

    logger.info("Applying LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, adapter_dir)

    logger.info("Merging LoRA weights with base model...")
    merged_model = model.merge_and_unload()

    logger.info(f"Saving merged standalone model to {output_dir}...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    logger.info("Successfully exported merged standalone checkpoint ready for vLLM!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge LoRA Adapter to Standalone Model")
    parser.add_argument("--base_model", type=str, default="meta-llama/Meta-Llama-3-8B-Instruct")
    parser.add_argument("--adapter_dir", type=str, default="training/checkpoints/nexus_lora_v1")
    parser.add_argument("--output_dir", type=str, default="models/nexus_cloud_v1_merged")
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    merge_and_export(
        base_model_name=args.base_model,
        adapter_dir=args.adapter_dir,
        output_dir=args.output_dir,
        device=args.device
    )
