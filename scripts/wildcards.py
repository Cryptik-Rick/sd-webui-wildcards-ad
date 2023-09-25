import os
import random
import sys
from pprint import pprint
import re

from modules import scripts, script_callbacks, shared

warned_about_files = {}
wildcard_dir = scripts.basedir()
d_replacements = {}


class WildcardsScript(scripts.Script):
    def title(self):
        return "Simple wildcards"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def replace_wildcard(self, text, gen, d_replacements):
        if " " in text or len(text) == 0:
            return text

        replacement_file = os.path.join(wildcard_dir, "wildcards", f"{text}.txt")
        if os.path.exists(replacement_file):
            with open(replacement_file, encoding="utf8") as f:
                ret = gen.choice(f.read().splitlines())
                d_replacements[text] = ret
                return ret
        else:
            if replacement_file not in warned_about_files:
                print(f"File {replacement_file} not found for the __{text}__ wildcard.", file=sys.stderr)
                warned_about_files[replacement_file] = 1

        return text

    def process(self, p, *args, **kwargs):
        if(not hasattr(shared, "d_replacements") or getattr(p,"_ad_idx",-1) == -1):
            shared.d_replacements = {}
        original_prompt = p.all_prompts[0]
        dict_rep = shared.d_replacements
        gen = random.Random()
        i = getattr(p, "_ad_idx", -1) # Image id from after detailer

        if(not hasattr(shared, "d_replacements") or getattr(p,"_ad_idx",-1) == -1):
            shared.d_replacements = {}

        #TODO: Add support for negatives
        if getattr(p, "_disable_adetailer", False):
            # ADetailer inpainting or not enabled.
            if(i != -1):
                if(p._ad_idx > len(dict_rep)):
                    prompt_dict = dict_rep[p._ad_idx % len(dict_rep)]
                else:
                    prompt_dict = dict_rep[p._ad_idx]
                
                for (text, ret) in prompt_dict.items():
                    p.prompt = p.prompt.replace(f"[__{text}__]", ret)
                
                #Check if there still are string to replace...
                pattern = r'\[__([^]]*)__\]'
                errstate = False
                for match in re.finditer(pattern, p.prompt):
                    print("Found a fixed wildcard in after detailer prompt that couldn't be replaced. Replacing it with a random one: ", match.group(0))
                    errstate = True
                
                if(errstate):
                    p.prompt = re.sub(pattern, r'__\1__', p.prompt)
                
                print("Final prompt: ", p.prompt)

                p.prompt = "".join(self.replace_wildcard(chunk, gen, {}) for chunk in p.prompt.split("__"))

                # Setting different prompts to the new generated one
                p.all_prompts[0] = p.prompt
                if(hasattr(p.script_args, "ad_prompt")):
                    p.script_args.ad_prompt = p.prompt
        elif(i == -1):
            # AD initial pass or disabled
            for pct in range(len(p.all_prompts)):
                if not pct in dict_rep:
                    dict_rep[pct] = {}
                prompt = p.all_prompts[pct]

                prompt = "".join(self.replace_wildcard(chunk, gen, dict_rep[pct]) for chunk in prompt.split("__"))
                p.all_prompts[pct] = prompt

        if original_prompt != p.all_prompts[0]:
            p.extra_generation_params["Wildcard prompt"] = original_prompt

        shared.d_replacements = dict_rep


def on_ui_settings():
    shared.opts.add_option("wildcards_same_seed", shared.OptionInfo(False, "Use same seed for all images", section=("wildcards", "Wildcards")))


script_callbacks.on_ui_settings(on_ui_settings)
