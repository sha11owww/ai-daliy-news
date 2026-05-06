import yaml
import os


def load_prompt(name: str, **kwargs) -> str:
    """加载提示词模板并填充变量"""
    path = os.path.join(os.path.dirname(__file__), f"{name}.yaml")
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data["template"].format(**kwargs)
