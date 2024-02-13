import os
import torch
from PIL import Image
os.putenv('HF_HUB_DISABLE_SYMLINKS_WARNING', 'true')
from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image

from utils import image_fit, repo_key


class DiffusersHandler:
    def __init__(self, cache_dir="cache", max_models=1, use_cuda=True, use_float16=True, hf_key=None):
        self.err_info = None
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        self.max_models = max_models
        if use_cuda and torch.cuda.is_available():
            self.device = "cuda"
            props = torch.cuda.get_device_properties('cuda')
            version = torch.cuda_version
            self.device_opts = {
                'type': "cuda",
                'name': props.name,
                'capability': f"{props.major}.{props.minor}",
                'memory_MB': props.total_memory,
                'multi_processor_count': props.multi_processor_count,
                'driver': version
            }
        else:
            self.device = "cpu"
            self.device_opts = {'type': "cpu"}

        self.use_float16 = use_float16
        self.hf_key = hf_key
        self.pipelines = {}
        self.curr = None
        self.rng = torch.Generator(self.device)

    def load_pipeline(self, repo_name: str, connect: bool = True):
        self.err_info = None
        key = repo_key(repo_name)
        if key in self.pipelines:
            self.curr = self.pipelines.pop(key)
            self.pipelines[key] = self.curr
            return

        if len(self.pipelines) == self.max_models:
            del self.pipelines[list(self.pipelines)[0]]
        torch_dtype, variant = (torch.float16, "fp16") if self.use_float16 else ("auto", None)
        token = self.hf_key if connect else None
        try:
            txt2img = AutoPipelineForText2Image.from_pretrained(
                repo_name, cache_dir=self.cache_dir, local_files_only=not connect, token=token,
                torch_dtype=torch_dtype, variant=variant)
        except Exception as error:
            if variant is None:
                raise error
            else:
                variant = None
            txt2img = AutoPipelineForText2Image.from_pretrained(
                repo_name, cache_dir=self.cache_dir, local_files_only=not connect, token=token,
                torch_dtype=torch_dtype)

        txt2img.to(self.device)
        default_size = txt2img.unet.config.sample_size * txt2img.vae_scale_factor

        model = {
            'repo': repo_name,
            'variant': variant or "default",
            'dtype': str(torch_dtype),
            'device': self.device_opts,
            'default_image_size': default_size
        }
        self.curr = {'model': model, 'txt2img': txt2img}
        self.pipelines[key] = self.curr

    def disable_nsfw_check(self):
        self.err_info = None
        if (
                self.curr and hasattr(self.curr['txt2img'], 'safety_checker') and
                self.curr['txt2img'].safety_checker is not None
        ):
            if 'safety_checker' not in self.curr:
                self.curr['safety_checker'] = self.curr['txt2img'].safety_checker
            self.curr['txt2img'].safety_checker = None
            if 'img2img' in self.curr:
                self.curr['img2img'].safety_checker = None

    def enable_nsfw_check(self):
        self.err_info = None
        if 'safety_checker' in self.curr:
            self.curr['txt2img'].safety_checker = self.curr['safety_checker']
            if 'img2img' in self.curr:
                self.curr['img2img'].safety_checker = self.curr['safety_checker']

    def run(self,
            prompt: str, negative_prompt: str = "", guidance_scale: float = 7.5,
            image_file: str = None, strength: float = 0.8, width: int = None, height: int = None,
            num_inference_steps: int = 50, number: int = 1, seed: int = None,
            block_nsfw: bool = True) -> list[tuple]:
        self.err_info = None
        if self.curr is None:
            raise AssertionError("Model not loaded")
        params = {
            'model': self.curr['model'],
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'guidance_scale': guidance_scale,
            'num_inference_steps': num_inference_steps,
            'num_images_per_prompt': number,
            'image_index': 0
        }

        try:
            width = width or self.curr['model']['default_image_size']
            height = height or self.curr['model']['default_image_size']
            width = max(round(width / 32) * 32, 32)
            height = max(round(height / 32) * 32, 32)

            if seed is not None:
                self.rng.manual_seed(seed)
                params['seed'] = seed

            if block_nsfw:
                self.enable_nsfw_check()
            else:
                self.disable_nsfw_check()
            if not image_file:
                params['width'], params['height'] = width, height
                result = self.curr['txt2img'](
                    prompt=prompt, negative_prompt=negative_prompt, guidance_scale=guidance_scale,
                    width=width, height=height,
                    num_images_per_prompt=number,
                    num_inference_steps=num_inference_steps, generator=self.rng,
                    return_dict=True)
            else:
                init_image = image_fit(Image.open(image_file), width, height, 32).convert('RGB')
                params['init_image'] = image_file
                params['strength'] = strength
                params['width'], params['height'] = init_image.size

                if 'img2img' not in self.curr:
                    self.curr['img2img'] = AutoPipelineForImage2Image.from_pipe(self.curr['txt2img'])
                result = self.curr['img2img'](
                    prompt=prompt, negative_prompt=negative_prompt, guidance_scale=guidance_scale,
                    image=init_image, strength=strength,
                    num_images_per_prompt=number,
                    num_inference_steps=num_inference_steps, generator=self.rng,
                    return_dict=True)
        except Exception as error:
            self.err_info = params
            raise error

        output = []
        try:
            flags = result.nsfw_content_detected
            if flags is None:
                raise AttributeError()
        except AttributeError:
            flags = [False] * len(result.images)

        for image, nsfw in zip(result.images, flags):
            if not nsfw:
                output.append((image, params.copy()))
            else:
                output.append((None, params.copy()))
            params['image_index'] += 1

        return output
