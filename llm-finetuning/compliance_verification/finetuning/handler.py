from unsloth import FastVisionModel
from typing import  Dict, List, Any
import requests
from PIL import Image as PILImage
from io import BytesIO

def load_image_from_url(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        return PILImage.open(BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"Error loading image from {url}: {str(e)}")
        return None


system_prompt = """You are an expert in trademark identification for apparel designs. Your task is to analyze images of apparel and determine 
if they contain licensed trademarks such as Greek organization letters (fraternities/sororities) or collegiate/university marks. Your response 
must strictly follow this two-line format: first indicating 'Licensed trademarks detected: Yes' or 'Licensed trademarks detected: No', followed 
by 'Organization:' with either the specific organization/university name(s) identified or 'None' if no trademarks are detected."""

instruction = """Examine these apparel images and identify if they contain licensed marks or Greek letters. If yes, name the Greek organization or university associated."""

class EndpointHandler():
    def __init__(self, path="johnhmeyer123/trademark_detection_lora_model"):
        print("Model Path:: ", path)
        model, tokenizer = FastVisionModel.from_pretrained(
            model_name = path, 
            load_in_4bit = True, 
        )

        FastVisionModel.for_inference(model) # Enable for inference!

        self.model = model
        self.tokenizer = tokenizer


    def __call__(self, data: Any) -> List[List[Dict[str, float]]]:
        """
        Args:
            data (:obj:):
                includes the input data and the parameters for the inference.            
        """

        print("Data type: ", type(data))
        print("Data: ", data)

        inputs = data.pop("inputs", data)
        image_urls = inputs.pop("image_urls", None)
        parameters = inputs.pop("parameters", None)
        
        if not image_urls:
            raise ValueError("No image URLs provided for processing.")

        if not isinstance(image_urls, list):
            image_urls = [image_urls]

        images =  [load_image_from_url(img_url) for img_url in image_urls[:2]]
        if None in images:
            images.remove(None)

        if len(images) == 0:
            return {"output": "No valid images provided."}
        
        messages = [
            {"role": "user", "content": [{"type": "image"} for _ in images]
            +[
                {"type": "text", "text": system_prompt + '\n\n' + instruction}
            ]}
        ]

        input_text = self.tokenizer.apply_chat_template(messages, add_generation_prompt = True)
        inputs = self.tokenizer(
            images,
            input_text,
            add_special_tokens = False,
            return_tensors = "pt",
        ).to("cuda")

        # pass inputs with all kwargs in data
        if parameters is not None:
            response = self.model.generate(**inputs,  max_new_tokens = 64, use_cache = True, **parameters)
        else:
            response = self.model.generate(**inputs,  max_new_tokens = 64, use_cache = True, temperature = 0.3, min_p = 0.05)
        # postprocess the response

        # print("Model Response:: ", response)

        output = self.tokenizer.decode(response[0]).split("|im_start|>assistant\n")[-1].split("<|im_end")[0]
        
        print("Model Output:: ", output)

        return {"output": str(output) }