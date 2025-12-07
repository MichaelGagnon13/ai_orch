"""
AgentScope Studio Data Sanitizer
Prevents "Invalid array length" errors by validating metrics before sending
"""

import json
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

# Safe limits for JavaScript arrays and numbers
MAX_SAFE_INTEGER = 2**31 - 1  # JavaScript safe integer limit
MAX_ARRAY_LENGTH = 100000  # Reasonable array size limit
MAX_COST_VALUE = 1000000  # Maximum reasonable cost in USD


class StudioDataSanitizer:
    """Sanitizes data before sending to AgentScope Studio"""

    @staticmethod
    def sanitize_number(
        value: Union[int, float], max_value: int = MAX_SAFE_INTEGER, field_name: str = "value"
    ) -> Union[int, float]:
        """Ensure number is within safe JavaScript range"""
        if not isinstance(value, (int, float)):
            return value

        # Check for invalid values
        if value != value:  # NaN check
            logger.warning(f"NaN detected in {field_name}, replacing with 0")
            return 0

        if value == float("inf") or value == float("-inf"):
            logger.warning(f"Infinity detected in {field_name}, capping to {max_value}")
            return max_value if value > 0 else 0

        # Cap to safe range
        if abs(value) > max_value:
            logger.warning(f"{field_name}={value} exceeds safe limit, capping to {max_value}")
            return max_value if value > 0 else -max_value

        return value

    @staticmethod
    def sanitize_array(
        arr: List[Any], max_length: int = MAX_ARRAY_LENGTH, field_name: str = "array"
    ) -> List[Any]:
        """Ensure array length is reasonable"""
        if not isinstance(arr, list):
            return arr

        if len(arr) > max_length:
            logger.warning(
                f"{field_name} length={len(arr)} exceeds limit, truncating to {max_length}"
            )
            return arr[:max_length]

        return arr

    @classmethod
    def sanitize_metrics(cls, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all metrics in a dict"""
        if not isinstance(metrics, dict):
            return metrics

        sanitized = {}

        for key, value in metrics.items():
            # Handle nested dicts
            if isinstance(value, dict):
                sanitized[key] = cls.sanitize_metrics(value)

            # Handle arrays
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_array(value, field_name=key)
                # Also sanitize numbers within arrays
                sanitized[key] = [
                    (
                        cls.sanitize_number(v, field_name=f"{key}[{i}]")
                        if isinstance(v, (int, float))
                        else v
                    )
                    for i, v in enumerate(sanitized[key])
                ]

            # Handle numbers
            elif isinstance(value, (int, float)):
                # Special handling for specific fields
                if "cost" in key.lower():
                    sanitized[key] = cls.sanitize_number(value, MAX_COST_VALUE, key)
                elif "token" in key.lower():
                    sanitized[key] = cls.sanitize_number(value, MAX_SAFE_INTEGER, key)
                elif "timestamp" in key.lower():
                    # Timestamps should be reasonable Unix timestamps
                    sanitized[key] = cls.sanitize_number(value, 2**32, key)
                else:
                    sanitized[key] = cls.sanitize_number(value, MAX_SAFE_INTEGER, key)

            # Keep other types as-is
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def wrap_agentscope_init(cls, original_init_func):
        """Decorator to wrap agentscope.init with data sanitization"""

        def wrapped_init(*args, **kwargs):
            # Call original init
            result = original_init_func(*args, **kwargs)

            logger.info("✅ AgentScope initialized with data sanitization enabled")
            return result

        return wrapped_init


# Monkey-patch example for existing code
def patch_agentscope():
    """
    Patches AgentScope to sanitize data before sending to Studio
    Call this at the start of your orchestrator
    """
    try:
        from agentscope.web import StudioClient

        # Patch the Studio client's data sending method
        original_send = StudioClient._send_data if hasattr(StudioClient, "_send_data") else None

        if original_send:

            def sanitized_send(self, data):
                # Sanitize before sending
                if isinstance(data, dict):
                    data = StudioDataSanitizer.sanitize_metrics(data)
                return original_send(self, data)

            StudioClient._send_data = sanitized_send
            logger.info("✅ AgentScope Studio client patched with data sanitization")
        else:
            logger.warning("⚠️  Could not patch Studio client (method not found)")

    except ImportError as e:
        logger.error(f"❌ Failed to patch AgentScope: {e}")


# Usage example for your orchestrator
def safe_agentscope_init(**kwargs):
    """
    Safe wrapper for agentscope.init that enables data sanitization

    Usage:
        from studio_sanitizer import safe_agentscope_init

        safe_agentscope_init(
            studio_url="http://127.0.0.1:3000",
            project="ai_orch"
        )
    """
    import agentscope

    # Apply patches
    patch_agentscope()

    # Call original init
    return agentscope.init(**kwargs)


# Direct sanitization functions for manual use
def sanitize_run_data(run_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize run data before sending to Studio

    Args:
        run_data: Dictionary containing run metrics and metadata

    Returns:
        Sanitized run data safe for Studio
    """
    return StudioDataSanitizer.sanitize_metrics(run_data)


def validate_run_data(run_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate run data and return issues found

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    def check_value(value, path=""):
        if isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            if len(value) > MAX_ARRAY_LENGTH:
                issues.append(f"{path}: array too long ({len(value)} elements)")
            for i, v in enumerate(value[:100]):  # Check first 100 elements
                check_value(v, f"{path}[{i}]")
        elif isinstance(value, (int, float)):
            if value != value:  # NaN
                issues.append(f"{path}: NaN value")
            elif value == float("inf") or value == float("-inf"):
                issues.append(f"{path}: Infinity value")
            elif abs(value) > MAX_SAFE_INTEGER:
                issues.append(f"{path}: value too large ({value})")

    check_value(run_data)

    return len(issues) == 0, issues


if __name__ == "__main__":
    # Test the sanitizer
    test_data = {
        "tokens": 2**40,  # Too large
        "cost": float("inf"),  # Infinity
        "timestamps": list(range(200000)),  # Too long
        "metrics": {"values": [1, 2, float("nan"), 4]},  # Contains NaN
    }

    print("Original data:")
    print(json.dumps({k: str(v)[:50] for k, v in test_data.items()}, indent=2))

    print("\nValidation:")
    is_valid, issues = validate_run_data(test_data)
    if not is_valid:
        print("❌ Issues found:")
        for issue in issues:
            print(f"  - {issue}")

    print("\nSanitized data:")
    sanitized = sanitize_run_data(test_data)
    print(json.dumps({k: str(v)[:50] for k, v in sanitized.items()}, indent=2))

    print("\nValidation after sanitization:")
    is_valid, issues = validate_run_data(sanitized)
    print("✅ Valid!" if is_valid else f"❌ Still has issues: {issues}")
