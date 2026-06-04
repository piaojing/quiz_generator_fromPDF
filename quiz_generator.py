#!/usr/bin/env python3
"""
Quiz Generator AI Agent
Extracts text from a PDF and generates an interactive multiple-choice quiz using Claude API.
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("❌ Missing dependency: anthropic")
    print("   Run: pip install anthropic")
    sys.exit(1)

try:
    from pypdf import PdfReader
except ImportError:
    print("❌ Missing dependency: pypdf")
    print("   Run: pip install pypdf")
    sys.exit(1)


# ── Colours for terminal output ──────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"


def cprint(color, text):
    print(f"{color}{text}{C.RESET}")


# ── PDF text extraction ───────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using pypdf."""
    path = Path(pdf_path)
    if not path.exists():
        print(f"{C.RED}❌ File not found: {pdf_path}{C.RESET}")
        sys.exit(1)
    if path.suffix.lower() != ".pdf":
        print(f"{C.RED}❌ File must be a PDF: {pdf_path}{C.RESET}")
        sys.exit(1)

    cprint(C.CYAN, f"\n📄 Reading PDF: {path.name}")
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    cprint(C.DIM, f"   {total_pages} page(s) found")

    text = ""
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        text += page_text + "\n"
        # Simple progress indicator
        print(f"   Extracting page {i+1}/{total_pages}...", end="\r")

    print()  # newline after progress

    if not text.strip():
        print(f"{C.RED}❌ No text could be extracted. The PDF may be scanned/image-based.{C.RESET}")
        sys.exit(1)

    cprint(C.GREEN, f"✅ Extracted {len(text):,} characters of text")
    return text


# ── Quiz generation via Claude ────────────────────────────────────────────────
def generate_quiz(text: str, num_questions: int, difficulty: str) -> list[dict]:
    """Call Claude API to generate a multiple-choice quiz from the extracted text."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"{C.RED}❌ ANTHROPIC_API_KEY environment variable not set.{C.RESET}")
        print("   Export it with: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate to ~12,000 words to stay within reasonable token limits
    words = text.split()
    if len(words) > 12000:
        text = " ".join(words[:12000])
        cprint(C.YELLOW, f"⚠️  Text truncated to 12,000 words for token efficiency")

    system_prompt = """You are a quiz generation assistant. When given a passage of text,
you generate clear, accurate multiple-choice quiz questions based strictly on the content provided.
Always respond with valid JSON only — no preamble, no markdown, no explanation outside the JSON."""

    user_prompt = f"""Generate {num_questions} multiple-choice quiz questions from the text below.
Difficulty level: {difficulty}

Rules:
- Each question must have exactly 4 options (A, B, C, D)
- Only one option should be correct
- Base all questions strictly on the provided text
- For {difficulty} difficulty: {"use direct factual recall" if difficulty == "easy" else "test understanding and inference" if difficulty == "medium" else "require deep analysis and synthesis"}

Respond ONLY with a JSON array in this exact format:
[
  {{
    "question": "Question text here?",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "answer": "A",
    "explanation": "Brief explanation of why this is correct"
  }}
]

TEXT:
{text}"""

    cprint(C.CYAN, f"\n🤖 Generating {num_questions} {difficulty} questions with Claude...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"{C.RED}❌ Failed to parse quiz JSON from Claude: {e}{C.RESET}")
        print(f"{C.DIM}Raw response:\n{raw[:500]}{C.RESET}")
        sys.exit(1)

    cprint(C.GREEN, f"✅ {len(questions)} questions generated!")
    return questions


# ── Interactive quiz session ──────────────────────────────────────────────────
def run_quiz(questions: list[dict], shuffle: bool = True):
    """Run the interactive quiz in the terminal."""
    if shuffle:
        random.shuffle(questions)

    total = len(questions)
    score = 0
    wrong_answers = []

    cprint(C.BOLD, f"\n{'='*55}")
    cprint(C.BOLD, f"  📝 QUIZ — {total} Questions")
    cprint(C.BOLD, f"{'='*55}")
    print("  Type A, B, C, or D to answer. Type Q to quit.\n")

    for i, q in enumerate(questions, 1):
        cprint(C.BOLD, f"\nQ{i}/{total}: {q['question']}")
        for letter, option in q["options"].items():
            print(f"  {letter}) {option}")

        # Get answer input
        while True:
            try:
                raw = input(f"\n  {C.CYAN}Your answer:{C.RESET} ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 Quiz interrupted.")
                print_results(score, i - 1, wrong_answers)
                return

            if raw == "Q":
                print("\n👋 Quiz quit early.")
                print_results(score, i - 1, wrong_answers)
                return
            if raw in ("A", "B", "C", "D"):
                break
            print("  ⚠️  Please enter A, B, C, or D")

        correct = q["answer"].upper()
        if raw == correct:
            cprint(C.GREEN, f"  ✅ Correct!")
            score += 1
        else:
            cprint(C.RED, f"  ❌ Wrong! The correct answer is {correct}: {q['options'][correct]}")
            wrong_answers.append({"question": q["question"], "your_answer": raw,
                                   "correct": correct, "explanation": q.get("explanation", "")})

        if q.get("explanation"):
            cprint(C.DIM, f"  💡 {q['explanation']}")

    print_results(score, total, wrong_answers)


def print_results(score: int, total: int, wrong: list[dict]):
    """Print the final score and review of wrong answers."""
    if total == 0:
        return

    pct = (score / total) * 100
    cprint(C.BOLD, f"\n{'='*55}")
    cprint(C.BOLD, "  📊 RESULTS")
    cprint(C.BOLD, f"{'='*55}")
    print(f"  Score: {score}/{total}  ({pct:.0f}%)")

    if pct == 100:
        cprint(C.GREEN, "  🏆 Perfect score! Outstanding!")
    elif pct >= 80:
        cprint(C.GREEN, "  🎉 Great job!")
    elif pct >= 60:
        cprint(C.YELLOW, "  👍 Good effort — review the missed questions below.")
    else:
        cprint(C.RED, "  📚 Keep studying — you'll get there!")

    if wrong:
        cprint(C.BOLD, f"\n  Review ({len(wrong)} missed):")
        for i, item in enumerate(wrong, 1):
            print(f"\n  {i}. {item['question']}")
            print(f"     Your answer : {item['your_answer']}")
            print(f"     Correct      : {item['correct']}")
            if item["explanation"]:
                cprint(C.DIM, f"     Explanation  : {item['explanation']}")

    print()


# ── CLI entry point ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="🎓 Quiz Generator — Turn any PDF into an interactive quiz",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quiz_generator.py document.pdf
  python quiz_generator.py document.pdf --questions 10 --difficulty hard
  python quiz_generator.py document.pdf -q 5 -d easy --no-shuffle
        """
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("-q", "--questions", type=int, default=5,
                        help="Number of questions to generate (default: 5)")
    parser.add_argument("-d", "--difficulty", choices=["easy", "medium", "hard"],
                        default="medium", help="Quiz difficulty (default: medium)")
    parser.add_argument("--no-shuffle", action="store_true",
                        help="Don't shuffle question order")

    args = parser.parse_args()

    cprint(C.BOLD, "\n🎓 Quiz Generator AI Agent")
    cprint(C.DIM,  "   Powered by Claude\n")

    # Step 1: Extract PDF text
    text = extract_text_from_pdf(args.pdf)

    # Step 2: Generate quiz via Claude
    questions = generate_quiz(text, args.questions, args.difficulty)

    # Step 3: Run interactive quiz
    run_quiz(questions, shuffle=not args.no_shuffle)


if __name__ == "__main__":
    main()
