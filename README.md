Windows TCL/TK graphical interface for [diffusers](https://github.com/huggingface/diffusers) library  
  
![Picture](Icons/picture.png)  
  
Framework: python, tkinter  
  
Requirements:  
 - python v3.10 or later [Python](https://wiki.python.org/moin/BeginnersGuide/Download)
 - pytorch v2.2 or later (GPU with CUDA recommended) [PyTorch](https://pytorch.org/get-started/locally/))
 - Pillow v10.0 or later [Pillow](https://pillow.readthedocs.io/en/stable/installation.html)
 - diffusers v0.26 or later [Diffusers] (https://huggingface.co/docs/diffusers/v0.26.2/en/quicktour)
   - accelerate 
   - transformers
  
Config: "config.yml"  
```
cache_dir: cache          # Path to HuggingFace cache directory, default 'cache'
max_models: 1             # Maximal number of models in memory, default '1'
use_cuda: true            # 'true' to use GPU if available, default 'true'
use_float16: true         # 'true' to use 'float16' for inference, default 'true'
 ```

![image](https://github.com/1000yoElf-dragon/Diffusers_GUI/assets/79000332/ae020684-cdf8-48d2-92f3-101cd69dea5c)
