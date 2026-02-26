import unsloth
from unsloth import FastVisionModel
from unsloth import is_bf16_supported
from unsloth.trainer import UnslothVisionDataCollator
import argparse
import os
from huggingface_hub import login
import torch
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

login(os.getenv("HF_TOKEN"))

def prepare_dataset():
    train_dataset = load_dataset("ikram98ai/compliance_verification",split='train')
    test_dataset = load_dataset("ikram98ai/compliance_verification", split='test')

    system_prompt = """You are a licensing compliance expert specifically for university and Greek organization apparel.
    Your task is to evaluate designs against the established licensing guidelines of these specific organizations. Determine
    if a design meets all requirements or violates any rules, assuming proper licensing permissions are already in place.
    For each evaluation, you must respond in a strict two-line format: first indicating 'Compliance Status: Compliant' or
    'Compliance Status: Non-compliant', followed by 'Violation Reason:' with either 'None' for compliant designs or a brief
    explanation for non-compliant designs. Never elaborate beyond this format. Base your evaluation solely on actual violations
    present in the image, not hypothetical concerns."""

    instruction = """Review this apparel design for compliance with licensing rules. Provide compliance status and violation reason, if any."""
  

    def convert_to_conversation(sample):
        conversation = [
            { "role": "user",
            "content" : [
                {"type" : "text",  "text"  : system_prompt + "\n\n" + instruction},
                ] + [{"type" : "image", "image" : img_url} for img_url in sample["image_urls"]]
            },
            { "role" : "assistant",
            "content" : [
                {"type" : "text",  "text"  : f"Compliance Status: {sample['compliance_status']}\nViolation Reason: {sample['violation_reason']}"} ]
            },
        ]
        return { "messages" : conversation }


    converted_train_dataset = [convert_to_conversation(sample) for sample in train_dataset]
    converted_test_dataset = [convert_to_conversation(sample) for sample in test_dataset]
    return converted_train_dataset, converted_test_dataset



def train(train_data, test_data,
          per_device_train_batch_size = 4,
          gradient_accumulation_steps = 4,
          max_steps = 30,
          num_train_epochs = None):
    

    model, tokenizer = FastVisionModel.from_pretrained(
        "unsloth/Qwen2.5-VL-7B-Instruct-bnb-4bit",
        load_in_4bit = True, # Use 4bit to reduce memory use. False for 16bit LoRA.
        use_gradient_checkpointing = "unsloth", # True or "unsloth" for long context
    )


    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers     = True, # False if not finetuning vision layers
        finetune_language_layers   = True, # False if not finetuning language layers
        finetune_attention_modules = True, # False if not finetuning attention layers
        finetune_mlp_modules       = True, # False if not finetuning MLP layers

        r = 32,           # The larger, the higher the accuracy, but might overfit
        lora_alpha = 32,  # Recommended alpha == r at least
        lora_dropout = 0.05,
        bias = "none",
        random_state = 3407,
        use_rslora = False,  # We support rank stabilized LoRA
        loftq_config = None, # And LoftQ
        # target_modules = "all-linear", # Optional now! Can specify a list if needed
    )

    ### Train the model

    FastVisionModel.for_training(model) # Enable for training!

    # Build config, prefer max_steps if set, otherwise use num_train_epochs
    config_kwargs = {
        'per_device_train_batch_size': per_device_train_batch_size,
        'per_device_eval_batch_size': per_device_train_batch_size,
        'gradient_accumulation_steps': gradient_accumulation_steps,
        'warmup_steps': 50,
        'learning_rate': 2e-4,
        'fp16': not is_bf16_supported(),
        'bf16': is_bf16_supported(),
        'logging_steps': 20,
        'eval_steps':20,
        'eval_strategy':'steps',
        'optim': 'adamw_8bit',
        'weight_decay': 0.01,
        'lr_scheduler_type': 'linear',
        'seed': 3407,
        'output_dir': 'outputs',
        'report_to': 'none',
        'remove_unused_columns': False,
        'dataset_text_field': '',
        'dataset_kwargs': {'skip_prepare_dataset': True},
        'dataset_num_proc': 4,
        'max_seq_length': 2048,
    }
    if num_train_epochs is not None:
        config_kwargs['num_train_epochs'] = num_train_epochs
    else:
        config_kwargs['max_steps'] = max_steps

    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        data_collator = UnslothVisionDataCollator(model, tokenizer), # Must use!
        train_dataset = train_data,
        eval_dataset = test_data[:per_device_train_batch_size * 20],
        args= SFTConfig(**config_kwargs),
    )

    trainer.train()
    
    return model, tokenizer

def main(args):

    train_data, test_data = prepare_dataset()

    model, tokenizer = train(
        train_data,
        test_data,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        max_steps=args.max_steps,
        num_train_epochs=args.epochs
    )

    # Push results
    model.push_to_hub("ikram98ai/compliance_verification_2epoch_lora_adapter", token=os.getenv('HF_TOKEN'))
    tokenizer.push_to_hub("ikram98ai/compliance_verification_2epoch_lora_adapter", token=os.getenv('HF_TOKEN'))
    model.push_to_hub_merged("ikram98ai/compliance_verification_lora_model", tokenizer, token=os.getenv('HF_TOKEN'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune compliance verification model")
    parser.add_argument("--batch_size", type=int, default=4,
                        help="Per-device train batch size")
    parser.add_argument("--grad_accum", type=int, default=4,
                        help="Gradient accumulation steps")
    parser.add_argument("--max_steps", type=int, default=30,
                        help="Maximum training steps")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of training epochs")
    args = parser.parse_args()
    main(args)