OctoLens

A Python tool to collect and export GitHub repository metrics—including stars, forks, watchers, traffic data, and more.
OctoLens helps you gather insights into repository activity and export the results to CSV or JSON for further analysis, now with an improved CLI and dynamic logging configuration.
Features

    Basic Repository Metrics: Stars, forks, watchers, open issues, last update time
    Traffic Insights: Views, unique visitors, clones, and unique cloners (requires push access)
    Fork Details: Detailed information about repository forks (limited to first page by default—consider pagination if necessary)
    Flexible CLI: Choose output formats (csv, json, or both) and specify log level & output directory
    Robust Error Handling: Automatic retries on failures, rate limit detection, and exponential backoff
    Logging: Dynamically configurable logging level (DEBUG/INFO/WARNING/ERROR) and timestamped log files

Requirements

    Python 3.7+
    A GitHub Personal Access Token with appropriate permissions (read repository data, and push access for traffic)
    Dependencies:
        requests
        pandas
        argparse
        (Optional) pytest or other frameworks if you plan to add tests

Installation
 ##Clone or Download this repository:
```
git clone https://github.com/YOUR_USERNAME/OctoLens.git
cd OctoLens
```
## Create and activate a virtual environment (optional but recommended):
```
python -m venv venv
```
```
source venv/bin/activate  # On Linux/Mac
```
```
venv\Scripts\activate     # On Windows
```

Install dependencies:
```
    pip install -r requirements.txt
```

Usage
Environment Variables

OctoLens expects three environment variables for authentication and identification of the repository:
```
    GITHUB_TOKEN: Your GitHub personal access token.
    GITHUB_OWNER: The owner (username or organization) of the repository.
    GITHUB_REPO: The name of the repository.
```
## For example:
```
export GITHUB_TOKEN=ghp_12345abcdef...
export GITHUB_OWNER=my-org
export GITHUB_REPO=my-repo
```
## Command-Line Arguments

## Run the script with:

```
python github_metrics.py [--format FORMAT] [--log-level LEVEL] [--output-dir DIRECTORY]
```
    --format: Output format for metrics.
        Valid values: csv, json, both.
        Defaults to csv.
    --log-level: Logging verbosity.
        Valid values: DEBUG, INFO, WARNING, ERROR.
        Defaults to INFO.
    --output-dir: Directory where exported files and logs will be saved.
        Defaults to . (current directory).

##Examples
### Example 1: Default CSV Export
```
# Set environment variables
export GITHUB_TOKEN=ghp_12345abcdef...
export GITHUB_OWNER=my-org
export GITHUB_REPO=my-repo
```
```
# Run the script (CSV only, INFO-level logs to current dir)
python github_metrics.py
```

### Example 2: Export Both CSV & JSON, DEBUG-Level Logs

```
# Set environment variables
export GITHUB_TOKEN='your_token'
export GITHUB_OWNER='owner'
export GITHUB_REPO='repo'
```

# with options
```
python github_metrics.py --format json --output-dir ./metrics --log-level DEBUG
```

This will:

    Collect all metrics (basic repo details, traffic data, and fork details).
    Write logs at DEBUG level to a file in /path/to/export (plus console output).
    Generate two files with timestamped filenames:
        /path/to/export/github_metrics_YYYYMMDD_HHMMSS.csv
        /path/to/export/github_metrics_YYYYMMDD_HHMMSS.json

Log Files

A log file is created each time you run the script, stored in the directory specified by --output-dir. By default, this is the current directory. The file name pattern is:

github_metrics_YYYYMMDD_HHMMSS.log

It includes detailed debugging information, which can be invaluable for troubleshooting.
Contributing

    Fork the repository
    Create your feature branch: git checkout -b feature/my-new-feature
    Commit your changes: git commit -am 'Add some feature'
    Push to the branch: git push origin feature/my-new-feature
    Create a pull request

License

This project is licensed under the MIT License. Feel free to use, modify, and distribute it as you see fit.
