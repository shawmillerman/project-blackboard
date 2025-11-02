**Project Blackboard, 03 Python Path Verification and Repair
Overview**

You need one Python, per project, in a clean virtual environment. If your shell aliases or Homebrew path hijack that, you get the classic “externally-managed-environment” error or the wrong interpreter in your venv. This module gives you a fast, repeatable checklist to verify the active Python, repair paths, rebuild the venv with the correct interpreter, and validate .env loading.

This is student facing and instructor friendly. It includes exact bash you can paste, one section at a time.

What you will do
* Verify which Python and pip your shell actually runs.
* Remove hijacking aliases, then reload your shell.
* Rebuild your project’s .venv using the explicit Homebrew Python path.
* Reinstall packages inside the venv, not system wide.
* Validate .env variables load correctly.
* Optional, enable smart auto activation, covered in 02_venv_auto_activation.md.

0) Quick facts for macOS with Homebrew

Intel macs usually install to /usr/local/....

Apple Silicon macs usually install to /opt/homebrew/....

Your Homebrew Python 3.14 binary path is typically:

Intel: /usr/local/opt/python@3.14/bin/python3.14

Apple Silicon: /opt/homebrew/opt/python@3.14/bin/python3.14

If in doubt, ask Homebrew:

brew --prefix python@3.14

Append /bin/python3.14 to that prefix.

1) Sanity checks, what is active right now

Paste and run these one by one:

# Where am I
pwd

# Show current PATH
echo $PATH

# Do I have lingering aliases
alias python
alias pip

# Which binaries are being used
which -a python python3 pip pip3

# Show versions, helps confirm what we are actually calling
python3 -V  || true
python -V   || true
pip3 -V     || true
pip -V      || true

Interpretation

If alias python or alias pip prints something, your shell is overriding the venv. We will remove those next.

If which python points inside .venv/.../bin/python, good. If it points to /usr/local/opt/python@3.14/... or /opt/homebrew/opt/... while your venv is active, your aliases or PATH are wrong.

2) Remove any global aliases for python and pip

Only do this if alias python or alias pip printed a value.

# Open your zsh config
nano ~/.zshrc

# In Nano: look for any lines like:
* alias python=...
* alias pip=...
* Delete those lines. Save and exit: Ctrl + O, Enter, Ctrl + X

# Reload shell config
source ~/.zshrc

# Confirm they are gone (should print nothing or an error)
alias python
alias pip
3) Rebuild your project venv with the correct interpreter

Replace the Python path below with the one from brew --prefix python@3.14 if needed.

# Go to your project
cd ~/ProjectBlackboard

# Nuke any old venv to avoid path contamination
rm -rf .venv

# Create a new venv with explicit Homebrew Python 3.14
/usr/local/opt/python@3.14/bin/python3.14 -m venv .venv

# Activate it
source .venv/bin/activate

# Confirm the venv-owned interpreter is active
which python
python -c "import sys; print(sys.executable)"

Expected

which python shows: /Users/<you>/ProjectBlackboard/.venv/bin/python

The sys.executable line shows the same path.

4) Install packages inside the venv
pip install --upgrade pip
pip install openai fastapi uvicorn pydantic python-dotenv pypdf tiktoken

If you ever see “externally-managed-environment”, you are not inside the venv. Reactivate the venv and rerun.

5) Validate .env loads and dimensions are set
# Confirm python-dotenv is present
pip list | grep python-dotenv || pip list | grep dotenv

# Print the model and dimensions from your .env
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('EMBED_MODEL'), os.getenv('EMBED_DIM'))"

Expected

text-embedding-3-small 1536

or whatever values you set. If you are using HNSW in Postgres, remember that index dimension limits can be 2,000, so set EMBED_DIM=1536 or below.

6) Optional, re-check pip points at the venv
which pip
pip -V

Expected path under .venv/bin/pip. If not, reactivate:

source .venv/bin/activate
7) Optional, enable smart auto activation

This lives in the companion file 02_venv_auto_activation.md. In short, it auto activates when you cd into any folder that contains .venv/bin/activate, and deactivates when you leave. Use that guide to add the chpwd() function to ~/.zshrc.

Troubleshooting, fast fixes

A) “externally-managed-environment” when pip installing
You are not in the venv. Fix:

cd ~/ProjectBlackboard
source .venv/bin/activate
pip install <package>

B) Venv created with the wrong interpreter
You created the venv without the explicit Homebrew path.

cd ~/ProjectBlackboard
rm -rf .venv
/usr/local/opt/python@3.14/bin/python3.14 -m venv .venv
source .venv/bin/activate
python -c "import sys; print(sys.executable)"

C) Aliases still hijack python or pip
Remove them and reload:

sed -i '' '/alias python/d' ~/.zshrc
sed -i '' '/alias pip/d' ~/.zshrc
source ~/.zshrc

D) Unsure where Homebrew put Python

brew --prefix python@3.14
ls -l $(brew --prefix python@3.14)/bin/

E) Apple Silicon vs Intel path mismatch

Intel: /usr/local/opt/python@3.14/bin/python3.14

Apple Silicon: /opt/homebrew/opt/python@3.14/bin/python3.14

F) .env not loading
Ensure the file exists at project root and contains:

OPENAI_API_KEY=sk-...
EMBED_MODEL=text-embedding-3-small
EMBED_DIM=1536

Then:

python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('EMBED_MODEL'), os.getenv('EMBED_DIM'))"
Verification, copy and run block

Run this, one section at a time, no comment lines.

cd ~/ProjectBlackboard
rm -rf .venv
/usr/local/opt/python@3.14/bin/python3.14 -m venv .venv
source .venv/bin/activate
which python
python -c "import sys; print(sys.executable)"
pip install --upgrade pip
pip install openai fastapi uvicorn pydantic python-dotenv pypdf tiktoken
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('EMBED_MODEL'), os.getenv('EMBED_DIM'))"

# Expected

which python and sys.executable both point inside .venv.

The final line prints your embedding model and dimension, for example: text-embedding-3-small 1536.

Next, suggested assignment hook

Have students add a short markdown file to their repo:

feedback_environment_setup.md

150–250 words on what worked, what failed, the fix, and one screenshot of a passing verification command. Commit and push.

Instructor Note

This module belongs at:
/setup-dev-environment/03_python_path_verification.md
