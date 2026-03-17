"""
Code execution evaluator using subprocess sandboxing.
In production, this should use Docker containers.
"""
import subprocess
import tempfile
import os
import re
from typing import Optional


class CodeExecutionEvaluator:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def evaluate(self, code: str, test_code: Optional[str] = None, language: str = "python") -> dict:
        """Execute code and optionally run tests."""
        full_code = code
        if test_code:
            full_code = f"{code}\n\n{test_code}"

        if language == "python":
            return self._run_python(full_code)
        else:
            return {"code_passed": False, "error": f"Language {language} not supported"}

    def evaluate_completion(self, provider, sample: dict) -> dict:
        """Given a coding sample, generate code and test it."""
        prompt_code = sample.get("prompt", "")
        test_code = sample.get("test", "")
        entry_point = sample.get("entry_point", "")

        prompt = f"""Complete the following Python function. Write ONLY the function body, properly indented.

{prompt_code}"""

        result = provider.complete(prompt)
        generated = result["output"]

        # Extract code block if wrapped in markdown
        code_match = re.search(r'```python\n(.*?)```', generated, re.DOTALL)
        if code_match:
            generated = code_match.group(1)

        # If the model returned the full function, use it
        if "def " in generated:
            full_code = generated
        else:
            full_code = f"{prompt_code}{generated}"

        exec_result = self.evaluate(full_code, test_code)

        return {
            "output": generated,
            "scores": {"code_pass@1": 1.0 if exec_result["code_passed"] else 0.0},
            "metadata": {
                "execution_time_ms": exec_result.get("execution_time_ms", 0),
                "error": exec_result.get("error", ""),
            },
            **result,
        }

    def _run_python(self, code: str) -> dict:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            import time
            start = time.time()
            proc = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed_ms = (time.time() - start) * 1000

            passed = proc.returncode == 0
            return {
                "code_passed": passed,
                "stdout": proc.stdout[:1000],
                "stderr": proc.stderr[:500] if not passed else "",
                "execution_time_ms": elapsed_ms,
                "error": proc.stderr[:200] if not passed else None,
            }
        except subprocess.TimeoutExpired:
            return {"code_passed": False, "error": "Timeout", "execution_time_ms": self.timeout * 1000}
        except Exception as e:
            return {"code_passed": False, "error": str(e), "execution_time_ms": 0}
        finally:
            os.unlink(tmp_path)
