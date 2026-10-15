"""Entry point for Hugging Face Spaces (and `python app.py` locally)."""
import os

from clara.studio import build_demo, launch_kwargs

demo = build_demo()

if __name__ == "__main__":
    kwargs = launch_kwargs()
    if os.environ.get("CLARA_SHARE") == "1":   # temporary public link, e.g. when running in Colab
        kwargs["share"] = True
    demo.queue().launch(**kwargs)
