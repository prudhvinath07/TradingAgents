"""Output validation layer to detect LLM hallucinations and generation issues.

This module provides validation utilities to detect common LLM output problems:
- Repeated text (generation loops)
- Future date references (temporal confusion)
- Numbers that don't match tool outputs (data hallucination)
"""

import re
from datetime import datetime
from typing import Optional


class OutputValidator:
    """Validates LLM outputs to detect hallucinations and generation issues."""

    def __init__(self, analysis_date: str):
        """Initialize the validator.

        Args:
            analysis_date: The simulation/analysis date in YYYY-MM-DD format
        """
        self.analysis_date = analysis_date
        try:
            self.analysis_datetime = datetime.strptime(analysis_date, "%Y-%m-%d")
        except ValueError:
            self.analysis_datetime = datetime.now()
        self.warnings = []

    def validate(self, output: str, tool_outputs: Optional[dict] = None) -> dict:
        """Run all validations on an LLM output.

        Args:
            output: The LLM-generated text to validate
            tool_outputs: Optional dict of tool names to their outputs for comparison

        Returns:
            dict with 'valid' bool and 'warnings' list
        """
        self.warnings = []

        self._check_repetition(output)
        self._check_future_dates(output)

        if tool_outputs:
            self._check_number_consistency(output, tool_outputs)

        return {"valid": len(self.warnings) == 0, "warnings": self.warnings.copy()}

    def _check_repetition(self, output: str, threshold: int = 3) -> None:
        """Detect repeated text blocks indicating generation loops.

        Args:
            output: Text to check
            threshold: Minimum number of repetitions to flag
        """
        # Split into sentences and look for repeated blocks
        sentences = re.split(r"[.!?]+", output)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        # Count sentence occurrences
        sentence_counts = {}
        for sentence in sentences:
            # Normalize whitespace for comparison
            normalized = " ".join(sentence.split())
            sentence_counts[normalized] = sentence_counts.get(normalized, 0) + 1

        # Check for repeated sentences
        for sentence, count in sentence_counts.items():
            if count >= threshold:
                self.warnings.append(
                    f"REPETITION_DETECTED: Text repeated {count} times: "
                    f"'{sentence[:50]}...'"
                )

        # Check for repeated paragraphs
        paragraphs = output.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 50]

        para_counts = {}
        for para in paragraphs:
            normalized = " ".join(para.split())[:200]  # First 200 chars
            para_counts[normalized] = para_counts.get(normalized, 0) + 1

        for para, count in para_counts.items():
            if count >= threshold:
                self.warnings.append(
                    f"PARAGRAPH_LOOP_DETECTED: Paragraph repeated {count} times"
                )

    def _check_future_dates(self, output: str) -> None:
        """Detect references to dates after the analysis date.

        Args:
            output: Text to check for future date references
        """
        # Common date patterns
        date_patterns = [
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
            r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
            r"\bQ[1-4]\s+\d{4}\b",
            r"\b(FY|fiscal year)\s*\d{4}\b",
        ]

        month_map = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }

        for pattern in date_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                try:
                    # Try to parse the date
                    if isinstance(match, tuple):
                        match = match[0]

                    # Handle "Month Day, Year" format
                    if any(m in match.lower() for m in month_map.keys()):
                        parts = re.findall(r"(\w+)\s+(\d+),?\s*(\d{4})", match)
                        if parts:
                            month_name, day, year = parts[0]
                            month = month_map.get(month_name.lower(), 1)
                            parsed_date = datetime(int(year), month, int(day))

                            if parsed_date > self.analysis_datetime:
                                self.warnings.append(
                                    f"FUTURE_DATE_DETECTED: '{match}' is after analysis date {self.analysis_date}"
                                )

                    # Handle numeric formats
                    elif re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", match):
                        parsed_date = datetime.strptime(
                            match.replace("/", "-"), "%Y-%m-%d"
                        )
                        if parsed_date > self.analysis_datetime:
                            self.warnings.append(
                                f"FUTURE_DATE_DETECTED: '{match}' is after analysis date {self.analysis_date}"
                            )

                    # Handle Q1-Q4 YYYY format
                    elif re.match(r"Q[1-4]\s+\d{4}", match, re.IGNORECASE):
                        year = int(re.findall(r"\d{4}", match)[0])
                        if year > self.analysis_datetime.year:
                            self.warnings.append(
                                f"FUTURE_DATE_DETECTED: '{match}' references a future year"
                            )

                    # Handle FY YYYY format
                    elif re.match(r"(FY|fiscal year)\s*\d{4}", match, re.IGNORECASE):
                        year = int(re.findall(r"\d{4}", match)[0])
                        if year > self.analysis_datetime.year:
                            self.warnings.append(
                                f"FUTURE_DATE_DETECTED: '{match}' references a future fiscal year"
                            )

                except (ValueError, IndexError):
                    # Couldn't parse date, skip
                    continue

    def _check_number_consistency(self, output: str, tool_outputs: dict) -> None:
        """Check if numbers in output match those from tool outputs.

        Args:
            output: LLM-generated text
            tool_outputs: Dict mapping tool names to their string outputs
        """
        # Extract significant numbers from tool outputs
        tool_numbers = set()
        for tool_name, tool_output in tool_outputs.items():
            if tool_output and isinstance(tool_output, str):
                # Find numbers with optional $ and B/M/K suffixes
                numbers = re.findall(
                    r"\$?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*[BMKbmk](?:illion)?)?",
                    tool_output,
                )
                for num in numbers:
                    # Normalize the number
                    normalized = self._normalize_number(num)
                    if (
                        normalized and normalized > 1000
                    ):  # Only track significant numbers
                        tool_numbers.add(normalized)

        if not tool_numbers:
            return

        # Extract numbers from LLM output
        output_numbers = re.findall(
            r"\$?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*[BMKbmk](?:illion)?)?", output
        )

        for num_str in output_numbers:
            normalized = self._normalize_number(num_str)
            if normalized and normalized > 1000:
                # Check if this number is close to any tool number
                is_consistent = any(
                    self._numbers_close(normalized, tool_num)
                    for tool_num in tool_numbers
                )

                if not is_consistent:
                    # This might be a hallucinated number
                    self.warnings.append(
                        f"UNVERIFIED_NUMBER: '{num_str}' not found in tool outputs. "
                        "May be hallucinated."
                    )

    def _normalize_number(self, num_str: str) -> Optional[float]:
        """Convert a number string to a float for comparison.

        Args:
            num_str: String like "$26B", "1,234.56", "50 million"

        Returns:
            Float value or None if parsing fails
        """
        try:
            # Remove $ and commas
            cleaned = num_str.replace("$", "").replace(",", "").strip()

            # Handle B/M/K suffixes
            multiplier = 1
            if re.search(r"[Bb](?:illion)?", cleaned):
                multiplier = 1_000_000_000
                cleaned = re.sub(r"\s*[Bb](?:illion)?", "", cleaned)
            elif re.search(r"[Mm](?:illion)?", cleaned):
                multiplier = 1_000_000
                cleaned = re.sub(r"\s*[Mm](?:illion)?", "", cleaned)
            elif re.search(r"[Kk]", cleaned):
                multiplier = 1_000
                cleaned = re.sub(r"\s*[Kk]", "", cleaned)

            return float(cleaned) * multiplier
        except (ValueError, AttributeError):
            return None

    def _numbers_close(self, a: float, b: float, tolerance: float = 0.1) -> bool:
        """Check if two numbers are within tolerance of each other.

        Args:
            a: First number
            b: Second number
            tolerance: Relative tolerance (default 10%)

        Returns:
            True if numbers are close enough
        """
        if a == 0 or b == 0:
            return a == b
        return abs(a - b) / max(abs(a), abs(b)) <= tolerance


def validate_agent_output(
    output: str, analysis_date: str, tool_outputs: Optional[dict] = None
) -> dict:
    """Convenience function to validate an agent's output.

    Args:
        output: The LLM-generated text
        analysis_date: Simulation date in YYYY-MM-DD format
        tool_outputs: Optional dict of tool outputs for number verification

    Returns:
        Validation result dict with 'valid' and 'warnings' keys
    """
    validator = OutputValidator(analysis_date)
    return validator.validate(output, tool_outputs)
