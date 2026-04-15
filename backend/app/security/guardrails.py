import re
from typing import Tuple, Optional

FORBIDDEN_PATTERNS = [
    r"ignore (all )?(previous|above) instructions",
    r"you are now DAN",
    r"jailbreak",
    r"pretend to be",
    r"system:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
]

MAX_INPUT_LENGTH = 4000


class InputGuardrail:
    @staticmethod
    def validate_input(content: str) -> Tuple[bool, Optional[str]]:
        if len(content) > MAX_INPUT_LENGTH:
            return False, f"Input exceeds maximum length of {MAX_INPUT_LENGTH} characters."

        lower_content = content.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, lower_content):
                return False, "Input contains disallowed patterns."

        return True, None