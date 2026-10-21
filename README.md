# Merchant Descriptor Enrichment: Rules vs. LLM, with Evaluations and an MCP Server

Card statements show cryptic descriptors like `SQ *JOES COFFEE TORONTO ON` or
`PAYPAL *NETFLIX.COM 4029357733 CA`. Customers don't recognise them, which leads to
confused calls and disputed charges. This project turns raw descriptors into clean
merchant details, and, more importantly, **measures how well each approach works**.

## What it does

- **Gold dataset:** 40 hand-labelled Canadian descriptors with the correct merchant,
  payment processor, city, province, and category.
- **Rules baseline** (`extract_rules.py`): regular expressions and keyword lists.
- **LLM extractor** (`extract_llm.py`): Claude with a structured JSON prompt.
- **Evaluation harness** (`evaluate.py`): field-by-field accuracy, an "all fields correct"
  score, and an `errors.csv` file for error analysis.
- **MCP server** (`mcp_server.py`): exposes the extractor as tools an AI assistant can call,
  so you can ask Claude "what are these charges on my statement?" and it uses your code.

## Results: rules baseline

| Method | Merchant | Processor | City | Province | Category | All fields correct |
|---|---|---|---|---|---|---|
| Rules, first version | 0.575 | 1.0 | 1.0 | 1.0 | 0.9 | 0.475 |
| Rules, after error analysis | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| LLM (Claude Haiku 5.5), first prompt | 0.9 | 0.95 | 1.0 | 1.0 | 0.9 | 0.8 |
| LLM, after one round of error analysis | 0.9 | 1.0 | 1.0 | 1.0 | 0.975 | 0.875 |

With the first prompt, about half of the LLM's 10 errors were debatable labels rather than
real mistakes ("Rogers Wireless" vs. "Rogers", VIA Rail as Transportation vs. Travel). The
clearest real error was reading `SP *` as Square instead of Shopify, which also cost two
category errors. The fix: the prompt lists each processor's prefix, the output schema
limits processor to the five known names, and the prompt says Shopify merchants are online
stores. The remaining 5 errors are all label judgement calls ("Amazon" vs. "Amazon
Marketplace", Walmart as Groceries vs. Retail). Like the tuned rules, the second row was
tuned on this set, so it's optimistic too.

The first version handled the structured parts (processor prefixes, provinces, known
cities) perfectly but struggled with merchant names: `WAL-MART #3104` should become
"Walmart", `OC TRANSPO PRESTO` should drop the "Presto", and `APPLE.COM/BILL` should be
"Apple". Working through `errors.csv` led to these fixes:

- Drop a trailing `CA` country code, payment words (`PRESTO`, `ONLINE PMT`, `BILL PAYMENT`)
  and store codes (`W532`, `STALL 12`, `/RAO`).
- Use the domain as the brand when a descriptor starts with one (`NETFLIX.COM` → Netflix).
- A small alias table for brands no general rule can clean (`WAL-MART`, `AMZN MKTP`, Uber).
- New category keywords, and Shopify as a fallback for "Online Shopping".
- Match category keywords as whole words, so `LA BELLE PROVINCE` isn't tagged as Bell.

**Don't trust the 1.0.** These rules were tuned on the same 40 descriptors they're scored
on, so the second row measures how well they fit this set, not how well they generalise.
On new descriptors they still fail in predictable ways. Cities missing from the list
(`STARBUCKS 01234 KITCHENER ON` gives the merchant "Starbucks Kitchener"), merchants with no
category keyword, and `DISNEYPLUS` instead of "Disney+" all slip through. Every new merchant
needs another rule. That's the gap an LLM can fill. To compare fairly, label a fresh held-out
set (stretch challenge 3) and score both methods on it.

## Run it

Needs Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python src/evaluate.py               # rules baseline, no API key needed

export ANTHROPIC_API_KEY=your-key              # Windows: set ANTHROPIC_API_KEY=your-key
.venv/bin/python src/evaluate.py --llm         # compare rules with the LLM
```

These commands call the virtual environment's Python directly. `source .venv/bin/activate`
works too, unless your shell has `python` aliased to the system Python (common on macOS).
An alias overrides the venv, and you'll see `ModuleNotFoundError: No module named 'pandas'`.

Never commit your API key. `.env` is already in `.gitignore`.

## Use it from Claude with MCP

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) lets AI assistants call
your code as tools. This server offers three:

| Tool | What it does |
|---|---|
| `clean_descriptor` | Cleans one raw descriptor |
| `clean_descriptors` | Cleans a list in one call |
| `evaluation_report` | Reports accuracy on the gold set, so the assistant knows how far to trust results |

**Test it locally** (starts the server and calls each tool over stdio):

```bash
.venv/bin/python src/test_mcp_server.py
```

**Connect it to Claude Code:**

```bash
claude mcp add merchant-descriptors -- /full/path/to/.venv/bin/python /full/path/to/src/mcp_server.py
```

**Or to Claude Desktop**, add this to `claude_desktop_config.json` and restart the app:

```json
{
  "mcpServers": {
    "merchant-descriptors": {
      "command": "/full/path/to/.venv/bin/python",
      "args": ["/full/path/to/src/mcp_server.py"]
    }
  }
}
```

Then try: *"Clean up these charges: SQ \*JOES COFFEE TORONTO ON, PAYPAL \*SPOTIFY 4029357733 CA."*

Point the command at the Python inside your virtual environment, as shown. A bare `python`
may be a different interpreter without the packages installed.

## Stretch challenges

1. **Error analysis.** Read `errors.csv` and group the LLM's mistakes. Are they wrong, or is
   the gold label debatable? Good evaluation means questioning your own labels too.
2. **Hybrid approach.** Use rules for the fields they get right (processor, province) and the
   LLM only for merchant and category. Compare cost, speed, and accuracy.
3. **Grow the test set.** Add 100 more descriptors, including tricky ones (French names,
   abbreviations, typos), and check whether your conclusions still hold.
4. **Consistency check.** Run the LLM three times per descriptor. How often do answers change?
5. **Upgrade the MCP tool.** Add a `mode` option so the tool can use the LLM extractor, and
   return a confidence flag when the rules and the LLM disagree.
6. **Enrich further.** Add a merchant website or logo lookup, the way Mastercard's Ethoca and
   bank apps show clearer transaction details.



## License

MIT. See [LICENSE](LICENSE).
