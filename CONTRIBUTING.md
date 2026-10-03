# Contributing

Use Python 3.10 or newer. No runtime dependencies are needed.

1. Run `python -m unittest discover -s tests -v` from the repository root.
2. Add regression tests before changing parsing, policies or report shape.
3. Keep RHS values, raw invalid input, filenames and exception strings out of
   reports. Add a unique sentinel test for every new error path.
4. Update the English syntax contract and the Chinese, Russian and German
   getting-started documents when behavior changes.
5. Submit a focused pull request with a problem statement and test results.

Do not submit real `.env` files or credentials. Use fictional examples. Parsing
extensions must explain their relationship to existing dotenv loaders; do not
silently claim compatibility. All contributions must be original or appropriately
licensed and attributed. The project uses the MIT license.
