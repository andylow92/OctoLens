import requests
from datetime import datetime, timedelta
import pandas as pd
import os
import logging
import time
import argparse
from typing import Dict, List, Optional
from requests.exceptions import HTTPError, RequestException

def setup_argparse() -> argparse.ArgumentParser:
    """
    Set up command-line argument parsing.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(description='Collect GitHub repository metrics')
    parser.add_argument('--format', 
                       choices=['csv', 'json', 'both'],
                       default='csv',
                       help='Output format (csv, json, or both)')
    parser.add_argument('--log-level',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Set the logging level')
    parser.add_argument('--output-dir',
                       default='.',
                       help='Directory to store output files')
    return parser

# Configure logging with dynamic log level
def setup_logging(log_level: str, output_dir: str) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level (str): Desired logging level
        output_dir (str): Directory for log files
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    log_file = os.path.join(output_dir, f'github_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
logger = logging.getLogger('github_metrics')

class RateLimitError(Exception):
    """Custom exception for rate limit errors"""
    def __init__(self, reset_time: int):
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded. Resets at {datetime.fromtimestamp(reset_time)}")

class GitHubMetricsCollector:
    def __init__(self, token: str, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize the collector with your GitHub personal access token.
        
        Args:
            token (str): GitHub personal access token
            max_retries (int): Maximum number of retries for rate-limited requests
            retry_delay (int): Base delay between retries in seconds
        """
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Make a request to the GitHub API with rate limit handling and retries.
        
        Args:
            url (str): The API endpoint URL
            method (str): HTTP method (default: 'GET')
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            requests.Response: The API response
            
        Raises:
            RateLimitError: If rate limit is exceeded and max retries are exhausted
            HTTPError: For other HTTP errors
            RequestException: For network/connection errors
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                response = requests.request(method, url, headers=self.headers, **kwargs)
                
                # Log remaining rate limit
                remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
                reset_time = response.headers.get('X-RateLimit-Reset', 'N/A')
                logger.debug(f"Rate limit remaining: {remaining}, Reset time: {reset_time}")
                
                # Handle rate limit error
                if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                    reset_time = int(response.headers['X-RateLimit-Reset'])
                    wait_time = reset_time - time.time()
                    
                    if wait_time > 0 and retries < self.max_retries:
                        wait_time = min(wait_time + 1, 3600)  # Cap wait time at 1 hour
                        logger.warning(f"Rate limit hit. Waiting {wait_time:.0f} seconds. Retry {retries + 1}/{self.max_retries}")
                        time.sleep(wait_time)
                        retries += 1
                        continue
                    else:
                        raise RateLimitError(reset_time)
                
                # Handle other errors
                response.raise_for_status()
                return response
                
            except RequestException as e:
                if retries < self.max_retries:
                    wait_time = self.retry_delay * (2 ** retries)  # Exponential backoff
                    logger.warning(f"Request failed: {e}. Retrying in {wait_time} seconds. Retry {retries + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logger.error(f"Request failed after {self.max_retries} retries: {e}")
                    raise
                    
        raise Exception("Maximum retries exceeded")

    def get_repo_basic_metrics(self, owner: str, repo: str) -> Dict:
        """
        Get basic repository metrics like stars, forks, and watchers.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            Dict: Repository metrics
        """
        url = f'{self.base_url}/repos/{owner}/{repo}'
        response = self._make_request(url)
        data = response.json()
        
        return {
            'stars': data['stargazers_count'],
            'forks': data['forks_count'],
            'watchers': data['subscribers_count'],
            'open_issues': data['open_issues_count'],
            'last_updated': data['updated_at']
        }

    def get_traffic_data(self, owner: str, repo: str) -> Dict:
        """
        Get repository traffic data for the last 14 days.
        Note: Requires push access to the repository.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            Dict: Traffic metrics including views and unique visitors
        """
        views_url = f'{self.base_url}/repos/{owner}/{repo}/traffic/views'
        clones_url = f'{self.base_url}/repos/{owner}/{repo}/traffic/clones'
        
        try:
            views_response = self._make_request(views_url)
            views_data = views_response.json()
        except HTTPError as e:
            logger.warning(f"Could not fetch view data: {e}")
            views_data = {'count': 0, 'uniques': 0}
            
        try:
            clones_response = self._make_request(clones_url)
            clones_data = clones_response.json()
        except HTTPError as e:
            logger.warning(f"Could not fetch clone data: {e}")
            clones_data = {'count': 0, 'uniques': 0}
        
        return {
            'total_views': views_data.get('count', 0),
            'unique_visitors': views_data.get('uniques', 0),
            'total_clones': clones_data.get('count', 0),
            'unique_cloners': clones_data.get('uniques', 0)
        }

    def get_fork_details(self, owner: str, repo: str) -> List[Dict]:
        """
        Get detailed information about repository forks.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            List[Dict]: List of fork details
        """
        url = f'{self.base_url}/repos/{owner}/{repo}/forks'
        response = self._make_request(url)
        forks = response.json()
        
        return [{
            'owner': fork['owner']['login'],
            'created_at': fork['created_at'],
            'last_updated': fork['updated_at'],
            'stars': fork['stargazers_count']
        } for fork in forks]

    def collect_all_metrics(self, owner: str, repo: str) -> Dict:
        """
        Collect all available metrics for a repository.
        
        Args:
            owner (str): Repository owner
            repo (str): Repository name
            
        Returns:
            Dict: All repository metrics combined
        """
        logger.info(f"Collecting all metrics for {owner}/{repo}")
        
        try:
            basic_metrics = self.get_repo_basic_metrics(owner, repo)
            traffic_data = self.get_traffic_data(owner, repo)
            fork_data = self.get_fork_details(owner, repo)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'repository': f'{owner}/{repo}',
                **basic_metrics,
                **traffic_data,
                'fork_count': len(fork_data),
                'fork_details': fork_data
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            raise

    @staticmethod
    def _generate_filename(base_name: str, format: str) -> str:
        """
        Generate a filename with timestamp.
        
        Args:
            base_name (str): Base name for the file
            format (str): File format (e.g., 'csv', 'json')
            
        Returns:
            str: Filename with timestamp
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_{timestamp}.{format}"

    @staticmethod
    def export_data(data: Dict, output_dir: str, base_name: str, format: str = 'csv') -> None:
        """
        Export data to a file in the specified format.
        
        Args:
            data (Dict): Data to export
            output_dir (str): Directory for output files
            base_name (str): Base name for output file (timestamp will be added)
            format (str): Export format ('csv' or 'json')
        """
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate filename with timestamp
        filename = os.path.join(
            output_dir,
            GitHubMetricsCollector._generate_filename(base_name, format)
        )
        
        logger.info(f"Exporting data to {filename}")
        
        try:
            # Create a copy of data for export
            export_data = data.copy()
            
            # Handle nested fork_details for CSV export
            if format.lower() == 'csv':
                export_data['fork_details'] = str(export_data.get('fork_details', []))
            
            df = pd.DataFrame([export_data])
            
            if format.lower() == 'csv':
                df.to_csv(filename, index=False)
            elif format.lower() == 'json':
                # For JSON, keep the original nested structure
                import json
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
            logger.info(f"Data exported successfully to {filename}")
        except Exception as e:
            logger.error(f"Error exporting data: {e}", exc_info=True)
            raise

def main():
    # Parse command-line arguments
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level, args.output_dir)
    logger = logging.getLogger('github_metrics')
    
    # Get environment variables
    token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('GITHUB_OWNER')
    repo = os.getenv('GITHUB_REPO')
    
    # Validate environment variables
    if not token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")
    if not owner:
        raise ValueError("Please set GITHUB_OWNER environment variable")
    if not repo:
        raise ValueError("Please set GITHUB_REPO environment variable")
    
    # Initialize collector
    collector = GitHubMetricsCollector(token)
    
    try:
        # Collect all metrics
        logger.info("Starting metrics collection")
        metrics = collector.collect_all_metrics(owner, repo)
        
        # Export based on specified format
        if args.format in ['csv', 'both']:
            collector.export_data(metrics, args.output_dir, 'github_metrics', 'csv')
        if args.format in ['json', 'both']:
            collector.export_data(metrics, args.output_dir, 'github_metrics', 'json')
        
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded. Resets at {datetime.fromtimestamp(e.reset_time)}")
    except HTTPError as e:
        logger.error(f"HTTP error occurred: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
