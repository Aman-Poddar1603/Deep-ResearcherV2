from dotenv import load_dotenv
from pathlib import Path
from main.src.utils.DRLogger import DRLogger
from main.src.utils.versionManagement import getAppVersion


logger: DRLogger = DRLogger()

DIR = Path(__file__).parent

class Secrets:
    def __init__(self):

        try:
            logger.log(
                "info",
                "Trying to Reachout the secrets!",
                "system",
                [""],
                "none",
                app_version=getAppVersion(),
            )
            env_pth = DIR / "env" / ".env"
            if not env_pth.exists():
                raise FileNotFoundError(f"The environment file not exist in this path: {env_pth}")
        except Exception as e:
            print (e)
