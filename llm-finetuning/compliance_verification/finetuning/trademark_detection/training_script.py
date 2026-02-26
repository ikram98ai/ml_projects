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
import evaluate

login(os.getenv("HF_TOKEN"))

clf_metrics = evaluate.combine(["accuracy", "f1", "precision", "recall"])



def prepare_dataset():
    
    train_ds, val_ds, test_ds = load_dataset("ikram98ai/trademark_detection", split=['train', 'val', 'test'])

    system_prompt = """You are an expert in trademark identification for apparel designs. Your task is to analyze images of apparel and determine if they contain licensed trademarks such as Greek organization letters (fraternities/sororities) or collegiate/university marks. Your response must strictly follow this two-line format: first indicating 'Licensed trademarks detected: Yes' or 'Licensed trademarks detected: No', followed by 'Organization:' with either the specific organization/university name(s) identified or 'None' if no trademarks are detected."""

    instruction = """Examine these apparel images and identify if they contain licensed marks or Greek letters. If yes, name the Greek organization or university associated."""
    
    def convert_to_conversation(sample):
        conversation = [
            { "role": "user",
            "content" : [
                {"type" : "text",  "text"  : system_prompt + "\n\n" + instruction},
                ] + [{"type" : "image", "image" : img_url} for img_url in sample["image_urls"]]
            },
            { "role" : "assistant",
            "content" : [
                {"type" : "text",  "text"  : f"Licensed trademarks detected: {sample['trademark_detected']}\nOrganization: {sample['organization']}"} ]
            },
        ]
        return { "messages" : conversation }


    train_dataset = [convert_to_conversation(sample) for sample in train_ds]
    val_dataset = [convert_to_conversation(sample) for sample in val_ds]
    test_dataset = [convert_to_conversation(sample) for sample in test_ds]
    return train_dataset + val_dataset,  test_dataset


def train(train_data, test_data, checkpoint_path,
          per_device_train_batch_size = 4,
          gradient_accumulation_steps = 4,
          max_steps = 30,
          num_train_epochs = None):
    
    model, tokenizer = FastVisionModel.from_pretrained(
        "unsloth/Qwen2.5-VL-7B-Instruct-bnb-4bit",
        load_in_4bit = True, 
        use_gradient_checkpointing = "unsloth",
    )


    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers     = False, # False if not finetuning vision layers
        finetune_language_layers   = True, # False if not finetuning language layers
        finetune_attention_modules = True, # False if not finetuning attention layers
        finetune_mlp_modules       = True, # False if not finetuning MLP layers

        r = 16,           # The larger, the higher the accuracy, but might overfit
        lora_alpha = 16,  # Recommended alpha == r at least
        lora_dropout = 0,
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
        'save_strategy':"steps",
        'save_steps':100,
        'eval_strategy':"steps",
        'eval_steps':100,
        'logging_steps': 10,
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

    training_args = SFTConfig(**config_kwargs)
    
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        data_collator = UnslothVisionDataCollator(model, tokenizer), # Must use!
        train_dataset = train_data,
        eval_dataset = test_data,
        args=training_args,
    )


    trainer.train(resume_from_checkpoint=checkpoint_path)
    
    return model, tokenizer

def main(args):
    checkpoint_path = None
    if args.resume and os.path.exists("outputs/checkpoint-latest"):
        checkpoint_path = "outputs/checkpoint-latest"



    train_data, test_data = prepare_dataset()

    model, tokenizer = train(
        train_data,
        test_data,
        checkpoint_path,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        max_steps=args.max_steps,
        num_train_epochs=args.epochs
    )

    # Push results
    model.push_to_hub("ikram98ai/trademark_detection_lora_adapter", token=os.getenv('HF_TOKEN'))
    tokenizer.push_to_hub("ikram98ai/trademark_detection_lora_adapter", token=os.getenv('HF_TOKEN'))
    model.push_to_hub_merged("ikram98ai/trademark_detection_lora_model", tokenizer, token=os.getenv('HF_TOKEN'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune trademark detection model")
    parser.add_argument("--batch_size", type=int, default=4,
                        help="Per-device train batch size")
    parser.add_argument("--grad_accum", type=int, default=4,
                        help="Gradient accumulation steps")
    parser.add_argument("--max_steps", type=int, default=30,
                        help="Maximum training steps")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of training epochs")
    parser.add_argument("--resume", action="store_true",
                   help="Resume from latest checkpoint")
    
    args = parser.parse_args()
    main(args)
