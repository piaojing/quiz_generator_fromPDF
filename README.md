# 🎓 Quiz Generator AI Agent

Turn any PDF into an interactive multiple-choice quiz using the Claude API.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key
Get your key from https://console.anthropic.com

```bash
# Mac/Linux
export ANTHROPIC_API_KEY=your_key_here

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=your_key_here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your_key_here"
```

---

## Usage

### Basic (5 medium questions)
```bash
python quiz_generator.py my_document.pdf
```

### Custom number of questions
```bash
python quiz_generator.py my_document.pdf --questions 10
```

### Choose difficulty
```bash
python quiz_generator.py my_document.pdf --difficulty hard
```

### All options combined
```bash
python quiz_generator.py my_document.pdf -q 8 -d easy --no-shuffle
```

---

## Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--questions` | `-q` | 5 | Number of questions |
| `--difficulty` | `-d` | medium | easy / medium / hard |
| `--no-shuffle` | — | off | Keep question order |

---

## How It Works

1. **Extract** — Reads text from your PDF using `pypdf`
2. **Generate** — Sends the text to Claude API, which creates multiple-choice questions
3. **Quiz** — Runs an interactive terminal quiz with scoring and answer review

---

## Tips

- Works best with text-based PDFs (textbooks, articles, reports)
- Scanned/image PDFs won't work (no text layer)
- Large PDFs are automatically truncated to ~12,000 words
- Use `hard` difficulty for study/exam prep, `easy` for quick review
