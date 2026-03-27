import importlib.util
import logging
import sys
import os
from typing import List

def check_runtime_health():
    """
    Validates that the environment is correctly set up for optimized (ONNX) inference.
    Warns the user if performance degradation is expected.
    """
    warnings = []
    
    # Check for onnxruntime
    if importlib.util.find_spec("onnxruntime") is None:
        warnings.append("[FinGuard Warning] 'onnxruntime' is not installed. Latency will be significantly higher (falling back to PyTorch).")
    
    # Check for optimum
    if importlib.util.find_spec("optimum") is None:
        warnings.append("[FinGuard Warning] 'optimum' is not installed. 'llm-guard' cannot use ONNX optimizations.")
        
    if warnings:
        print("\n" + "!" * 50)
        for w in warnings:
            print(w)
        print("Fix: pip install onnxruntime optimum")
        print("!" * 50 + "\n")
        return False
    
    return True

def download_models():
    """
    Triggers the download and caching of all ONNX models required by built-in policies.
    This ensures that subsequent FinGuard initializations are near-instant.
    """
    from .config import PolicyConfig
    from .router import get_input_scanners, get_output_scanners
    
    print("[FinGuard] Pre-fetching ONNX models for built-in policies...")
    
    # Standard policies to pre-cache
    policies = ["default", "fast_lane", "retail_banking", "wealth_advisor", "high_security"]
    
    for p_name in policies:
        print(f"  -> Processing policy: {p_name}")
        try:
            policy = PolicyConfig.load(p_name)
            # Trigger input scanners (downloads ONNX injection/topics if enabled)
            get_input_scanners(policy.risk_level, policy)
            # Trigger output scanners
            get_output_scanners(policy.risk_level, policy)
        except Exception as e:
            print(f"  [Error] Failed to pre-fetch for {p_name}: {e}")
            
    print("[FinGuard] All models cached successfully.")

def get_device():
    """Returns the best available device for inference."""
    # We prioritize CPU-ONNX for stability as per project goals, 
    # but provide hooks for future GPU support.
    return "cpu"
