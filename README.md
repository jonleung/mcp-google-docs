> Note that this README was AI generated and I asked it to bias it on making it "idiot proof". I have not reviewed it yet lol

# Google Docs MCP Server

This Model Context Protocol (MCP) server provides Claude with the ability to interact with Google Docs directly. With this integration, Claude can create, read, and edit Google Documents, as well as work with comments.

## Features

- Create new Google Docs
- Read document content
- Rewrite document content 
- Create comments on documents
- Read comments from documents
- Reply to comments
- Delete comment replies

## Prerequisites

- Python 3.8 or higher
- A Google Cloud project with the Google Docs API enabled
- OAuth 2.0 credentials for authentication

## Setup Instructions

### Step 1: Install the MCP Server

1. Clone or download this repository
2. Navigate to the repository directory
3. Check your Python version - it should be 3.8 or higher:

```bash
python --version
```

4. If using pyenv and you see an error about versions, set the local Python version:

```bash
# List available Python versions
pyenv versions

# Set local version (replace X.Y.Z with your version)
pyenv local X.Y.Z
```

5. Install the package:

```bash
cd /path/to/mcp-google-docs
pip install -e .
```

6. Verify installation worked (no errors should appear):

```bash
pip list | grep mcp-google-docs
```

### Step 2: Set Up Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the Google Docs API:
   - In your project, go to "APIs & Services" > "Library"
   - Search for "Google Docs API" and enable it
   - Also enable the "Google Drive API" (required for some document operations)

### Step 3: Create OAuth Credentials

1. In your Google Cloud project, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" and select "OAuth client ID"
3. For Application type, select "Desktop app"
4. Give it a name (e.g., "Claude Google Docs MCP")
5. Click "Create"
6. Download the credentials JSON file
7. Save it somewhere secure (you'll need the path to this file later)

### Step 4: Configure the Token Storage

1. Choose a location to store the OAuth token after authentication
2. The first time you run the server, it will prompt you to authenticate in a browser
3. After authentication, the token will be stored in this location

### Step 5: Test the Server

Run the server manually to verify it works:

```bash
# IMPORTANT: Set environment variables 
# Replace with YOUR ACTUAL file paths!
export GOOGLE_CREDS_FILE="/path/to/your/credentials.json"
export GOOGLE_TOKEN_FILE="/path/to/your/token.json"

# Run the server
python -m mcp_server.mcp_server
```

**IMPORTANT TROUBLESHOOTING NOTES:**

1. DO NOT use command-line arguments like `--creds-file-path=...` as they may cause errors with shell interpretation
2. Use environment variables as shown above instead
3. Make sure to use the correct paths to your credentials and token files
4. Be careful with paths that contain spaces or special characters

The first time you run this, a browser window should open. Log in to your Google account and authorize the application. If successful, the server will start running without any error messages.

To confirm the server is running properly, you should see output like:
```
(no visible output - this is normal)
```

If you see error messages, check the paths to your credential and token files.

### Step 6: Configure Claude Desktop

1. Open Claude Desktop
2. Navigate to Settings
3. Locate your Python executable's full path:

```bash
which python
# Example output: /Users/username/.pyenv/shims/python
```

4. Add the following MCP configuration (replace ALL paths with your actual file paths):

```json
{
  "mcp": {
    "servers": {
      "googledocs": {
        "command": "/full/path/to/your/python",
        "args": ["-m", "mcp_server.mcp_server"],
        "env": {
          "GOOGLE_CREDS_FILE": "/path/to/your/credentials.json",
          "GOOGLE_TOKEN_FILE": "/path/to/your/token.json"
        }
      }
    }
  }
}
```

**Important notes about the configuration:**
- For `command`, you MUST use the FULL path to your Python executable - this is critical
- This is typically something like `/Users/username/.pyenv/shims/python` or `/usr/bin/python3`
- Do NOT just use `"python"` as this will cause a "spawn python ENOENT" error
- Make sure ALL file paths are absolute (full) paths, not relative paths
- Copy-paste the exact file paths from your terminal to avoid typos

### Step 7: Restart Claude Desktop

After saving your configuration, restart Claude Desktop to load the MCP server.

## Troubleshooting

### "spawn python ENOENT" Error

This means Claude Desktop can't find your Python executable. Make sure you're using the full path to Python:

```bash
which python
```

Use that full path in your Claude Desktop configuration.

### Authentication Issues

If you see authentication errors:

1. Check that your credentials file is correct
2. Delete the token file and let the server generate a new one
3. Make sure you've enabled the necessary APIs in your Google Cloud project

### "Module not found" Errors

If Python can't find the mcp_server module:

1. Make sure you installed the package with `pip install -e .`
2. Check that your working directory is correct
3. Verify your Python environment has all dependencies installed

### Python Version Issues

If you get errors related to Python version:

1. Check your Python version:
   ```bash
   python --version
   ```

2. If it shows version 3.13 is required but not installed:
   ```
   pyenv: version `3.13' is not installed (set by /path/to/.python-version)
   ```

3. Edit the package requirements to work with your Python version:
   ```bash
   # Open pyproject.toml and change:
   # requires-python = ">=3.13"
   # to:
   # requires-python = ">=3.8" 
   ```

4. Then set your local Python version and reinstall:
   ```bash
   pyenv local 3.X.X  # Your version here
   pip install -e .
   ```

## Security Notes

- Keep your OAuth credentials secure
- Never share your client secret or tokens
- The server requires access to your Google Documents and Drive
- Consider using a dedicated Google account for testing

## Using Claude with Google Docs

Once configured, you can ask Claude to:

- "Create a new Google document"
- "Read the contents of a Google document"
- "Add a comment to my Google document"
- And more!

For existing documents, you'll need to provide the document ID. This is the part of the Google Docs URL that looks like this:

```
https://docs.google.com/document/d/DOCUMENT_ID_IS_HERE/edit
```

For example, if your document URL is:
```
https://docs.google.com/document/d/1abcXYZ123_exampleDocumentId456/edit
```

The document ID is: `1abcXYZ123_exampleDocumentId456`

### Example Commands

Here are some examples of how to interact with Google Docs through Claude:

1. **Creating a new document:**
   ```
   Can you create a new Google Doc titled "Meeting Notes"?
   ```

2. **Reading a document:**
   ```
   Can you read the content of my Google Doc with ID "1abcXYZ123_exampleDocumentId456"?
   ```

3. **Adding content to a document:**
   ```
   Can you rewrite the document with ID "1abcXYZ123_exampleDocumentId456" to include these bullet points: [your content here]
   ```

4. **Working with comments:**
   ```
   Can you read all comments from my Google Doc with ID "1abcXYZ123_exampleDocumentId456"?
   ```

---

## Advanced Configuration

### Environment Variables

Instead of arguments, you can configure the server with environment variables:

- `GOOGLE_CREDS_FILE`: Path to your OAuth credentials JSON file
- `GOOGLE_TOKEN_FILE`: Path to store/retrieve the token

### Command-line Arguments

When running manually, you can use these arguments:

```
--creds-file-path PATH  Path to OAuth credentials file
--token-path PATH       Path to store/retrieve token
```

### Custom Scopes

By default, the server requests these OAuth scopes:
- `https://www.googleapis.com/auth/documents`
- `https://www.googleapis.com/auth/drive`

---

For issues or contributions, please file a GitHub issue or submit a pull request.