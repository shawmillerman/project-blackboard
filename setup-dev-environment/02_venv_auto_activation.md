Project Blackboard:  Smart Virtual Environment Activation
Overview

This module introduces a universal smart virtual environment (venv) 
auto-activation feature for Project Blackboard.
It ensures your Python environment automatically activates when you enter 
the project folder and deactivates when you leave.

The feature is added directly to your Zsh configuration file (~/.zshrc) 
and applies to any project that includes a .venv folder.
It makes development smoother, safer, and more reproducible,perfect for 
classrooms or multi-project workflows.

Why This Matters

Simplifies onboarding: Students or collaborators don’t need to remember to 
activate the venv manually.

Reduces errors: Prevents system-wide package conflicts and “it works on my 
machine” problems.

Scales automatically: Works for all projects that contain a 
.venv/bin/activate file.

Promotes reproducibility: Ensures every developer runs code in the same 
isolated environment.

Implementation Steps
1. Open .zshrc
nano ~/.zshrc
2. Add the Following Block

Paste this at the bottom of the file:

# --- Universal Smart venv Auto-Activation ---
function chpwd() {
  if [[ -f "$PWD/.venv/bin/activate" ]]; then
    source "$PWD/.venv/bin/activate"
  elif [[ -n "$VIRTUAL_ENV" && ! "$PWD" =~ "$VIRTUAL_ENV" ]]; then
    deactivate 2>/dev/null
  fi
}
# ------------------------------------------------

Save and exit:
Ctrl + O → Enter → Ctrl + X

3. Reload Your Shell
source ~/.zshrc
Verification Steps

Run:

cd ~
cd ~/ProjectBlackboard
cd ~

Expected:

When you enter your project folder → (.venv) appears in your prompt.

When you leave → it disappears automatically.

Troubleshooting

If you see parse error near \n:

Open your .zshrc again with nano ~/.zshrc.

Ensure every if has a matching fi and every { has a matching }.

Project Blackboard – Smart Virtual Environment Activation
Overview

This module introduces a universal smart virtual environment (venv) 
auto-activation feature for Project Blackboard.
It ensures your Python environment automatically activates when you enter 
the project folder and deactivates when you leave.

The feature is added directly to your Zsh configuration file (~/.zshrc) 
and applies to any project that includes a .venv folder.
It makes development smoother, safer, and more reproducible—perfect for 
classrooms or multi-project workflows.

Why This Matters

Simplifies onboarding: Students or collaborators don’t need to remember to 
activate the venv manually.

Reduces errors: Prevents system-wide package conflicts and “it works on my 
machine” problems.

Scales automatically: Works for all projects that contain a 
.venv/bin/activate file.

Promotes reproducibility: Ensures every developer runs code in the same 
isolated environment.

Implementation Steps
1. Open .zshrc
nano ~/.zshrc
2. Add the Following Block

Paste this at the bottom of the file:

# --- Universal Smart venv Auto-Activation ---
function chpwd() {
  if [[ -f "$PWD/.venv/bin/activate" ]]; then
    source "$PWD/.venv/bin/activate"
  elif [[ -n "$VIRTUAL_ENV" && ! "$PWD" =~ "$VIRTUAL_ENV" ]]; then
    deactivate 2>/dev/null
  fi
}
# ------------------------------------------------

Save and exit:
Ctrl + O → Enter → Ctrl + X

3. Reload Your Shell
source ~/.zshrc
Verification Steps

Run:

cd ~
cd ~/ProjectBlackboard
cd ~

Expected:

When you enter your project folder → (.venv) appears in your prompt.

When you leave → it disappears automatically.

Troubleshooting

If you see parse error near \n:

Open your .zshrc again with nano ~/.zshrc.

Ensure every if has a matching fi and every { has a matching }.

Save and reload.

Next Steps

This marks the completion of your environment automation layer.
In the next module, you’ll integrate Supabase and pgvector to give your 
FastAPI app memory and persistent embeddings storage.

Instructor Note

This module is stored in your course repository at:
/setup-dev-environment/02_venv_auto_activation.md
