# bl4ckPM

### Quick Start

To get the necessary dependencies, run the following command in cmd:

```
pip install -r requirements.txt
```

To run the application locally, run the following command in cmd:

```
py app.py
```

### Requirements

- The tool uses **Vercel CLI** for automatically deploying generated phishing pages. You can install it by following the instructions at: [Vercel CLI Documentation](https://vercel.com/docs/cli).
- **Cohere API Key** is required for generating bait messages. You need to set it as an environment variable for the tool to pick it up:
  - On **Linux/macOS**:
    ```
    export COHERE_API_KEY="your-secret-key"
    ```
  - On **Windows** (CMD):
    ```
    setx COHERE_API_KEY "your-secret-key"
    ```
  - On **Windows (PowerShell)**:
    ```
    [System.Environment]::SetEnvironmentVariable("COHERE_API_KEY", "your-secret-key", "User")
    ```



