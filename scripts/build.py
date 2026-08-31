from ga4_platform.config import Settings
from ga4_platform.pipeline import build
from ga4_platform.quality import run

if __name__ == "__main__":
    settings=Settings.load()
    print(build(settings))
    print(run(settings))

