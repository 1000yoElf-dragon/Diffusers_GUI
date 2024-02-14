import os
from tkinter import N, S, E, W, NW, SW, NE, SE, HORIZONTAL, VERTICAL, RIGHT
from tkinter import ttk, messagebox
from math import sqrt, floor
from diffusers.utils import make_image_grid
from yaml import YAMLError

from widgets.common import HistoryCombo, DasScala, SeedEntry, ChooseDir, ImageBox, Size, CheckBox, InitImageBox
from widgets.promptbox import PromptBox
from diffusershandler import DiffusersHandler
from utils import repo_key, check_bool_opt, file_naming, not_include, SubstituteImage, load_yaml, save_yaml
from filehandlers import image_files


class MainFrame(ttk.Frame):
    def __init__(self, root, config_file):
        super(MainFrame, self).__init__(root, padding="3 3 12 12")

        self.config_file = config_file

        try:
            self.app_config = load_yaml(self.config_file, default_fname="default.yml", default={})
        except Exception as error:
            if messagebox.askokcancel(
                    title="Warning!", message="It seems configuration file is broken. Create default configuration?"
            ):
                try:
                    self.app_config = load_yaml("default.yml", default={})
                    if self.app_config is None:
                        self.app_config = {}
                except (OSError, IOError, YAMLError):
                    self.app_config = {}
            else:
                raise error

        self.diffusers_handler = DiffusersHandler(
            cache_dir=self.app_config.setdefault('cache_dir', "cache"),
            max_models=self.app_config.setdefault('max_models', 1),
            use_cuda=check_bool_opt(self.app_config, 'use_cuda', True),
            use_float16=check_bool_opt(self.app_config, 'use_float16', True),
            hf_key=self.app_config['hf_key'] if 'hf_key' in self.app_config else None
        )

        if 'substitute_image' in self.app_config:
            self.substitute_image = SubstituteImage(self.app_config['substitute_image'])
        else:
            self.substitute_image = SubstituteImage("Icons/nsfw.png")

        self.grid(column=0, row=0, sticky=(N, W, E, S))
        self.columnconfigure(1, weight=1, minsize=550)
        self.rowconfigure(3, weight=1, minsize=150)
        self.rowconfigure(4, weight=1, minsize=150)

        # Model repo
        self.repo = HistoryCombo(
            self, "Model repository: ", width=80,
            history=self.app_config.setdefault('repo_history', []),
            is_eq_func=lambda s1, s2: repo_key(s1) == repo_key(s2)
        )
        self.repo.grid(column=1, row=1, sticky=E+W, padx=5, pady=5)

        # Checkbuttons
        checkbuttons = {
            'nsfw': ("NSFW protection", True),
            'connect': ("Connect to HuggingFace", True)
        }
        self.checkbox = CheckBox(self, checkbuttons)
        self.checkbox.grid(column=1, row=2, sticky=W, padx=5, pady=5)

        # Prompt
        self.prompt = PromptBox(self, "Prompt", width=80, height=5,
                                negative=False, adprompt_path=self.app_config.setdefault('adprompt_path', "adprompt"),
                                adprompt_history=self.app_config.setdefault('adprompt_history', []))
        self.prompt.grid(column=1, row=3, sticky=E+W+N+S, padx=5, pady=5)
        self.prompt.add_history()
        self.neg_prompt = PromptBox(self, "Negative prompt", width=80, height=5,
                                    negative=True, adprompt_path=self.app_config['adprompt_path'],
                                    adprompt_history=self.app_config.setdefault('neg_adprompt_history', []))
        self.neg_prompt.grid(column=1, row=4, sticky=E+W+N+S, padx=5, pady=5)
        self.prompt.add_history()

        # Guidance scale
        self.guidance = DasScala(self, "Guidance scale",
                                 from_=0., to=20., step=0.1, init=7.5, tickinterval=1.0,
                                 length=450, width=15, orient=HORIZONTAL)
        self.guidance.grid(column=1, row=5, sticky=E+W, padx=5, pady=5)

        # Initial image....
        self.init_img = InitImageBox(
            self, "Initial image", width=20, history=self.app_config.setdefault('init_image_history', []),
            default_image_file="Icons/noimage_gray.png"
        )
        self.init_img.grid(column=1, row=6, rowspan=2, sticky=E+W, padx=5, pady=5)

        # Seed
        self.seed = SeedEntry(self, "Random generator seed")
        self.seed.grid(column=2, row=1, rowspan=2, sticky=(W, E), padx=5, pady=5)

        # Inference steps
        self.steps = DasScala(self, "Inference steps",
                              from_=1, to=200, step=1, init=50, tickinterval=25,
                              length=450, width=15, orient=VERTICAL, entry_pos=N)
        self.steps.grid(column=2, row=3, rowspan=4, sticky=N+S, padx=5, pady=5)

        # Run button
        self.run_button = ttk.Button(self, text="Run", command=lambda *args: self.run())
        self.run_button.grid(column=2, row=7, padx=5, pady=5)

        # Output
        self.output = ImageBox(self, width=640, height=640, default_image_file="Icons/noimage_gray.png")
        self.output.grid(column=3, row=1, columnspan=2, rowspan=5, sticky=S, padx=5, pady=5)

        # Image size
        self.imsize = Size(self, "Image size", (32, 4096), step=32, defaul=(512, 512))
        self.imsize.grid(column=3, row=6, sticky=SW, padx=5, pady=5)

        # File name prefix
        validate_fname = not_include('\\/:*?»<>|')
        def validate_prefix(val): return val.endswith("?.png") and validate_fname(val.removesuffix("?.png").rstrip("?"))
        self.prefix = HistoryCombo(
            self, "Filename prefix: ", width=40,
            history=self.app_config.setdefault('filename_prefix_history', []),
            validator=validate_prefix
        )
        if not self.app_config['filename_prefix_history']:
            self.prefix.set("ai_painting_????.png")
        self.prefix.entry.config(justify=RIGHT)
        self.prefix.grid(column=4, row=6, sticky=SE, padx=5, pady=5)

        # Output dir
        self.outdir = ChooseDir(self, "Save path: ", width=80, history=self.app_config.setdefault('outdir_history', []))
        if not self.app_config['outdir_history']:
            self.outdir.set(os.path.abspath("ai_images"))
        self.outdir.grid(column=3, row=7, columnspan=2, sticky=W+E, padx=5, pady=5)

        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)
        self.prompt.focus()

    def run(self):
        stage = "Runtime"
        try:
            stage = "Output directory"
            folder = self.outdir.get()
            os.makedirs(folder, exist_ok=True)
            template_fname_raw = self.prefix.get()
            fnames = file_naming(folder, template_fname_raw, '?')
            self.outdir.add_history()
            self.prefix.add_history()

            stage = "Get prompts"
            prompt_txt = self.prompt.get().strip()
            if prompt_txt:
                self.prompt.add_history()
            neg_prompt_txt = self.neg_prompt.get().strip()
            if neg_prompt_txt:
                self.neg_prompt.add_history()

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
            self.repo.add_history()

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
            for image, properties in result:
                actual_size = (properties['width'], properties['height'])
                if image is not None:
                    fname = next(fnames)
                    to_show.append(image)
                    image_files.save(fname, image)
                    save_yaml(fname + ".prm", properties)
                else:
                    to_show.append(self.substitute_image.subst(*actual_size))

            stage = "Show image"
            if to_show:
                length = len(to_show)
                rows = floor(sqrt(length))
                cols = (length - 1) // rows + 1
                im_grid = make_image_grid(to_show, rows, cols)
                self.output.set(im_grid)
            if actual_size:
                self.imsize.set(actual_size)
        except Exception as error:
            info = self.diffusers_handler.err_info
            messagebox.showerror(
                title=stage + " ERROR",
                message=f"{type(error).__name__} ERROR:\n\n{str(error)}" +
                        (f"\n\n{str(info)}" if info else "")
            )
        save_yaml(self.config_file, self.app_config)
