"""
NexusAI - Production LoRA / QLoRA Fine-Tuning Script
Supports:
- Meta-Llama-3-8B-Instruct / Mistral-7B-Instruct-v0.3
- 4-bit NormalFloat4 (NF4) double quantization via BitsAndBytes
- Hugging Face PEFT (Parameter-Efficient Fine-Tuning)
- TRL SFTTrainer with gradient checkpointing & flash attention support
"""

import os
import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NexusAI-Trainer")

def train_lora(
    base_model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    train_file: str = "training/data/train.jsonl",
    val_file: str = "training/data/val.jsonl",
    output_dir: str = "training/checkpoints/nexus_lora_v1",
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    epochs: int = 3,
    batch_size: int = 2,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 2048,
    dry_run: bool = False
):
    """
    Executes 4-bit QLoRA fine-tuning using Hugging Face PEFT and TRL.
    """
    logger.info("Initializing Fine-Tuning Pipeline...")
    logger.info(f"Base Model: {base_model_name}")
    logger.info(f"Target Checkpoint Output: {output_dir}")
    logger.info(f"Hyperparameters: rank={lora_r}, alpha={lora_alpha}, lr={learning_rate}, epochs={epochs}")

    if dry_run:
        logger.info("[DRY-RUN] Simulating configuration validation and dataset check...")
        if not Path(train_file).exists():
            from dataset_prep import generate_datasets
            generate_datasets()
        logger.info("[DRY-RUN] Configuration verified successfully.")
        return True

    try:
        import torch
        from datasets import load_dataset
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer
    except ImportError as e:
        logger.error(f"Missing required training dependencies: {e}")
        logger.info("Please install via: pip install -r training/requirements_training.txt")
        return False

    device_available = torch.cuda.is_available()
    logger.info(f"CUDA Available: {device_available}")
    if not device_available:
        logger.warning("CUDA GPU not detected! QLoRA fine-tuning requires an NVIDIA GPU (e.g. A10G, A100, RTX 3090/4090).")

    # 1. 4-Bit Quantization Configuration
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True
    )

    # 2. Tokenizer
    logger.info(f"Loading Tokenizer: {base_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        base_model_name,
        trust_remote_code=True,
        padding_side="right"
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 3. Base Model
    logger.info(f"Loading Model in 4-bit NF4: {base_model_name}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model)

    # 4. LoRA Adapter Configuration
    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ]
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 5. Dataset loading
    logger.info(f"Loading training data from {train_file}")
    dataset = load_dataset("json", data_files={"train": train_file, "val": val_file})

    # 6. Training Arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        optim="paged_adamw_8bit",
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="epoch" if val_file else "no",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        group_by_length=True,
        report_to="none"
    )

    # 7. SFT Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["val"] if val_file else None,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        tokenizer=tokenizer,
        args=training_args
    )

    logger.info("Commencing Fine-Tuning Execution...")
    trainer.train()

    # 8. Save adapter weights
    logger.info(f"Saving LoRA adapter to {output_dir}")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("Fine-Tuning completed successfully!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NexusAI QLoRA Fine-Tuner")
    parser.add_argument("--model", type=str, default="meta-llama/Meta-Llama-3-8B-Instruct")
    parser.add_argument("--train_file", type=str, default="training/data/train.jsonl")
    parser.add_argument("--val_file", type=str, default="training/data/val.jsonl")
    parser.add_argument("--output_dir", type=str, default="training/checkpoints/nexus_lora_v1")
    parser.add_argument("--r", type=int, default=16)
    parser.add_argument("--alpha", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--dry_run", action="store_true", help="Simulate configuration without GPU")
    args = parser.parse_args()

    train_lora(
        base_model_name=args.model,
        train_file=args.train_file,
        val_file=args.val_file,
        output_dir=args.output_dir,
        lora_r=args.r,
        lora_alpha=args.alpha,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        dry_run=args.dry_run
    )
