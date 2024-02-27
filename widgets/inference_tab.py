import os
import tkinter as tk
from tkinter import N, S, E, W, NW, SW, NE, SE, HORIZONTAL, VERTICAL, RIGHT
from tkinter import ttk, messagebox
from math import sqrt, floor
from diffusers.utils import make_image_grid

import cfg
from widgets.common import HistoryCombo, DasScala, SeedEntry, ChooseDir, ImageBox, Size, CheckBox, InitImageBox
from widgets.promptbox import PromptBox, AdPromptList
from widgets.imagebox import ScalableImage, SaveImage
from diffusershandler import DiffusersHandler
from utils import repo_key, file_naming, not_include, save_yaml
from filehandlers import image_files


class InferenceTab(ttk.Frame):
    def __init__(self, root):
        super(InferenceTab, self).__init__(root, padding="3 3 12 12")

        self.diffusers_handler = DiffusersHandler(
            cache_dir=cfg.config['cache_dir'],
            max_models=cfg.config['max_models'],
            use_cuda=cfg.config['use_cuda'],
            use_float16=cfg.config['use_float16'],
            hf_key=cfg.config['hf_key'] if 'hf_key' in cfg.config else None
        )

        self.grid(column=0, row=0, sticky=(N, W, E, S))
        self.columnconfigure(1, weight=1, minsize=400)
        self.columnconfigure(3, weight=1, minsize=400)
        self.rowconfigure(3, weight=1, minsize=150)
        self.rowconfigure(4, weight=1, minsize=150)

        # Model repo
        self.repo = HistoryCombo(
            self, "Model repository: ", width=80,
            history=cfg.config['repo_history'],
            is_eq_func=lambda s1, s2: repo_key(s1) == repo_key(s2)
        )
        self.repo.grid(column=1, row=1, sticky=E+W, padx=5, pady=5)

        # Image size
        self.imsize = Size(self, "Image size", (32, 4096), step=32, defaul=(512, 512))
        self.imsize.grid(column=1, row=2, sticky=tk.W, padx=5, pady=5)

        # Checkbuttons
        checkbuttons = {
            'nsfw': ("NSFW protection", True),
            'connect': ("Connect to HuggingFace", True),
        }
        self.checkbox = CheckBox(self, checkbuttons, orient=tk.VERTICAL)
        self.checkbox.grid(column=1, row=2, sticky=tk.NE, padx=5, pady=5)

        # Prompt
        self.adprompt_list = AdPromptList(self)
        self.adprompt_list.grid(row=3, column=1, rowspan=2, sticky=N+S+W+E)

        self.prompt = PromptBox(self, "Prompt", width=80, height=5,
                                negative=False, adprompt_path=cfg.config['adprompt_path'],
                                adprompt_history=cfg.config['adprompt_history'],
                                adprompt_list=self.adprompt_list
                                )
        self.prompt.grid(column=1, row=3, sticky=E+W+N+S, padx=5, pady=5)
        self.prompt.update_history()
        self.neg_prompt = PromptBox(self, "Negative prompt", width=80, height=5,
                                    negative=True, adprompt_path=cfg.config['adprompt_path'],
                                    adprompt_history=cfg.config['neg_adprompt_history'],
                                    adprompt_list=self.adprompt_list
                                    )
        self.neg_prompt.grid(column=1, row=4, sticky=E+W+N+S, padx=5, pady=5)
        self.prompt.update_history()

        # Guidance scale
        self.guidance = DasScala(self, "Guidance scale",
                                 from_=0., to=20., step=0.1, init=7.5, tickinterval=1.0,
                                 length=450, width=15, orient=HORIZONTAL)
        self.guidance.grid(column=1, row=5, sticky=E+W, padx=5, pady=5)

        # Initial image....
        self.init_img = InitImageBox(
            self, "Initial image", width=20, history=cfg.config['init_image_history']
        )
        self.init_img.grid(column=3, row=2, rowspan=2, sticky=tk.NE+tk.NW, padx=5, pady=5)

        # Seed
        self.seed = SeedEntry(self, "Random generator seed")
        self.seed.grid(column=2, row=2, sticky=(W, E), padx=5, pady=5)

        # Inference steps
        self.steps = DasScala(self, "Inference steps",
                              from_=1, to=200, step=1, init=50, tickinterval=25,
                              length=450, width=15, orient=VERTICAL, entry_pos=N)
        self.steps.grid(column=2, row=3, rowspan=4, sticky=N+S, padx=5, pady=5)

        # Run button
        self.run_button = ttk.Button(self, text="Run", command=lambda *args: self.run())
        self.run_button.grid(column=2, row=7, padx=5, pady=5)



        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)
        self.prompt.focus()

    def run(self):
        stage = "Runtime"
        try:
            stage = "Get prompts"
            prompt_txt = self.prompt.get().strip()
            if prompt_txt:
                self.prompt.update_history()
            neg_prompt_txt = self.neg_prompt.get().strip()
            if neg_prompt_txt:
                self.neg_prompt.update_history()

            stage = "Get parameters"
            guidance_val = self.guidance.get()
            seed_val = self.seed.get()
            num_steps = self.steps.get()
            width, height = self.imsize.get()
            block_nsfw = self.checkbox['nsfw'].get()
            connect = self.checkbox['connect'].get()
            init_image_file, strength = self.init_img.get()
            self.init_img.add_history()

            stage = "Load repo"
            repo_name = self.repo.get()
            self.diffusers_handler.load_pipeline(repo_name, connect=connect)
            self.repo.update_history()

            stage = "Inference"
            result = self.diffusers_handler.run(
                prompt=prompt_txt, negative_prompt=neg_prompt_txt, guidance_scale=guidance_val,
                image_file=init_image_file, strength=strength,
                width=width, height=height,
                num_inference_steps=num_steps, number=1, seed=seed_val,
                block_nsfw=block_nsfw)

            stage = "Save results"
            to_show = []
            actual_size = None
            for image, params in result:
                if actual_size is None:
                    actual_size = (params['width'], params['height'])
                    self.imsize.set(actual_size)

                if image is not None:
                    SaveImage(tk._default_root, image, params)
                    #to_show.append(image)
                else:
                    to_show.append(cfg.config['nsfw_image'])

            #stage = "Show image"
            #if to_show:
            #    length = len(to_show)
            #    rows = floor(sqrt(length))
            #    cols = (length - 1) // rows + 1
            #   im_grid = make_image_grid(to_show, rows, cols)
            #    self.output.set_image(im_grid)

        except Exception as error:
            info = self.diffusers_handler.err_info
            messagebox.showerror(
                title=stage + " ERROR",
                message=f"{type(error).__name__} ERROR:\n\n{str(error)}" +
                        (f"\n\n{str(info)}" if info else "")
            )
        cfg.save()
