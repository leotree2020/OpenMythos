#!/usr/bin/env python3
"""P1-C environment probe (CPU-safe). Reports GPU/CUDA/PyTorch status without training."""
import json
import platform
import sys

def main():
    info = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch_available": False,
        "cuda_available": False,
    }
    try:
        import torch
        info["torch_available"] = True
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["cuda_device_count"] = torch.cuda.device_count()
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
            info["cuda_version"] = torch.version.cuda
    except Exception as e:
        info["torch_error"] = str(e)
    print(json.dumps(info, indent=2))

if __name__ == "__main__":
    main()
