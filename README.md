# Job Gap Browser Automation Challenge

This repository contains my solution for the Job Gap browser automation challenge. It includes implementations for processing job applications for various applicant profiles.

## Quick Setup with `uv`

Please ensure you have `uv` installed. If not, visit [uv's documentation](https://docs.astral.sh/uv/getting-started/installation/) for installation instructions.

Next, ensure you have python installed. If you do not, run these commands.

Check available python versions:

```bash
uv install python --list
```

Install version of choice:

```bash
uv install python <version>
```

> Ensure the version installed is compatible with the version specified in `.python-version` (3.10.*), or delete `.python-version` and install a version >=3.10.

In the project's base directory, run the following command to set up the project:

```bash
chmod +x scripts/uv-setup.sh && bash scripts/uv-setup.sh '<playwright_browser_deps>'
```

Example:

```bash
chmod +x scripts/uv-setup.sh && bash scripts/uv-setup.sh 'chromium' 'msedge'
```

## Running the Application

I have provided a CLI interface for the application. You can run it using the following command:

In the project's base directory, execute:

```bash
uv run -m cli.main process_job_applications '<application_url>' '<path_to_applicant_data.json>' --agent 'google' --browser-options '<path_to_browser_options.yaml>' --retry '<retry_count>'
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

## Suggestions for Improvement

### Error Handling

Implement more robust error handling to manage network issues, invalid data formats, and other potential exceptions.

### Dynamic form question to applicant data mapping

I tried to implement this partially by generating a schema for the each (google) form question and then using the schema and applicant data to answer the question, but it is still crude. A more sophisticated mapping system could be developed to handle various form structures and applicant data formats.

The mapping system could be implemented using AI to analyze the form structure and applicant data, for better schema generation and mapping. Also, if AI isn't an option, using an indexing system (whoosh or any other library) can help in searching for relevant data in the applicant's profile. Although it may not be as accurate as AI, it can still provide a more structured approach to mapping applicant data to form questions.

### Testing

If more time were given, I would implement unit tests for the important job application logic to ensure reliability and extensibility later on. This would include testing the form processing logic, data validation, and error handling, as well as ensuring that the application can handle various edge cases and unexpected inputs gracefully.
