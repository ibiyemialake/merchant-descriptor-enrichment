# Merchant Descriptor Enrichment

Turning card-statement text like `SQ *JOES COFFEE TORONTO ON` into "Joes Coffee, Toronto,
ON, Restaurants & Cafes", and measuring how well rules and an LLM each do it.

## Why I built it

Card statements are hard to read. A charge shows up as `PAYPAL *NETFLIX.COM 4029357733 CA`
or `LCBO/RAO #217 LONDON ON`, and when people don't recognise a charge, they call their bank
or dispute it. Those calls and chargebacks cost banks real money, which is why services like
Mastercard's Ethoca exist to show cleaner merchant names in banking apps.

I wanted to find out how far hand-written rules get, where an LLM earns its cost, and to
measure the difference rather than trust a few good-looking examples.

## What it does

Two extractors take a raw descriptor and return five fields: merchant, payment processor,
city, province and spending category. One uses regular expressions, keyword lists and a
small brand alias table. The other calls Claude with a JSON schema, so every reply has the
right fields and the category comes from a fixed list.

I tuned both on 40 hand-labelled descriptors, then scored them on 52 they'd never seen.
Every miss goes to `errors.csv`:

| Method | Development set | Held-out set |
|---|---|---|
| Rules | 100% | 13% |
| LLM (Claude Haiku 5.5) | 88% | 90% |

*Share of descriptors with all five fields correct.*

The rules looked perfect on their tuning data and fell apart on new data: unlisted cities,
merchants without a category keyword, typos like `DOLLARMA`. The LLM held up, and most of its
misses are naming judgement calls ("Telus Mobility" vs. "Telus").

The part I'm proudest of is the MCP server. It gives an AI assistant three tools: clean one
descriptor, clean a batch, and report measured accuracy, so Claude can tell you how far to
trust its answer.

## Tech stack

- Python 3.11 and pandas for the evaluation.
- The Anthropic Python SDK with structured outputs. Limiting processor and category to fixed
  lists fixed a real bug, where the model returned the raw prefix "SP \*" instead of "Shopify".
- The MCP Python SDK, with a smoke test that calls the server over stdio.

## What's next

- Let the MCP server use the LLM. Right now it only runs the rules, which the held-out
  results show is the weaker option.
- Try a hybrid: rules for processor and province, the LLM for merchant and category.
- Measure how often the LLM's answers change between runs.
- Get a second person to label the held-out set.

## Run it

You'll need Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/evaluate.py                          # rules on the development set
.venv/bin/python src/evaluate.py --data data/holdout.csv  # rules on the held-out set

export ANTHROPIC_API_KEY=your-key
.venv/bin/python src/evaluate.py --llm --data data/holdout.csv   # add the LLM
```

I call the venv's Python directly because on macOS a `python` alias can override an
activated venv, which shows up as `No module named 'pandas'`. On Windows, use
`.venv\Scripts\python`.

## Use it from Claude

Check the server works (this starts it and calls each tool):

```bash
.venv/bin/python src/test_mcp_server.py
```

Add it to Claude Code:

```bash
claude mcp add merchant-descriptors -- /full/path/to/.venv/bin/python /full/path/to/src/mcp_server.py
```

Or to Claude Desktop, in `claude_desktop_config.json`:

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

Then ask: *"Clean up these charges: SQ \*JOES COFFEE TORONTO ON, PAYPAL \*SPOTIFY 4029357733 CA."*

## License

MIT. See [LICENSE](LICENSE).
