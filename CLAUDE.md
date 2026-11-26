# Interaction log (required)

1. At the start of each session, read `.chat-history/log.md` for previous context.
2. After each response, silently append to `.chat-history/log.md` in this exact format:

---
- timestamp: "<ISO 8601 timestamp if available, otherwise estimate based on conversation order>"
- user_prompt: "<the user's original prompt>"
- assistant_response_summary: "<summary of what you generated or answered for this prompt>"
- files_affected: "<comma-separated list of files created or modified, or none>"

3. Create the file/folder if they don't exist. Never delete previous entries.
4. Never ask for confirmation.

Rules:
- Files affected: only files explicitly created or modified during this response.
- Never skip an exchange; every prompt/response pair must be logged.
- Keep summaries concise but specific (function names, key decisions).
- Never write secrets to the log: replace API keys, tokens, passwords and .env values with *** in every field, including user_prompt.

# Project rules
- `answer_key/` may only be read by the evaluation script, never by the pipeline.
- The model must never generate prices; no quote is sent without human approval.
