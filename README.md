# Job Gap AI Interview 2

This repository contains Daniel Afolayan's solution for the second interview task in the Job Gap AI series. It includes implementations for processing job applications for various applicant profiles.

## Quick Setup with `uv`

Please ensure you have `uv` installed. If visit [uv's documentation](https://docs.astral.sh/uv/getting-started/installation/) for installation instructions.

Run the following command to set up the project:

```bash
chmod +x scripts/uv-setup.sh && bash scripts/uv-setup.sh
```

## Running the Application

I have provided a CLI interface for the application. You can run it using the following command:

In the base directory of the project, execute:

```bash
uv run -m cli.main process_job_applications '<application_url>' '<path_to_applicant_data.json>' --agent 'google' --browser-options '<path_to_browser_options.yaml' --retry '<retry_count>'
```

For example, using the provided sample data:

```bash
uv run -m cli.main process_job_applications 'https://docs.google.com/forms/d/e/1FAIpQLScqvt7Qu7yOLiJf-foH51Fg3gNxgmvQe6Uerxhtp4x_t9WHug/viewform' 'cli/resources/data.json' --browser-options 'cli/configs/browser-options.yaml' --retry 1
```

Or, run the command with the `--help` flag to see all available options:

```bash
uv run -m cli.main process_job_applications --help
```

## Project Structure Summary

- The `cli` directory contains the command-line interface implementation.
- The `cli\configs` directory contains configuration files for the CLI, such as browser options.
- The `cli\resources` directory contains sample data and other resources used by the CLI.
- The `cli\job_applications.py` file contains the main logic for processing job applications.
- The `cli\main.py` file is the entry point for the CLI application.
- The `scripts` directory contains setup scripts and other utility scripts.
- The `src` directory contains the main application logic that handles the processing of job applications.
- The `src\generics` directory contains generic utility functions and classes that can be reused across different parts of the application.
- The `src\specifics` directory contains specific implementations for the given interview task scenario.
