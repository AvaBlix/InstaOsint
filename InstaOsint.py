#!/usr/bin/env python3
"""
Instagram OSINT Tool - Educational Purpose Only
"""

import os
import json
import requests
import datetime
import re
import time
import random
from typing import Dict, List, Optional
import argparse
import sys
import logging

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class InstagramOSINT:
    def __init__(self):
        """
        Initialize the OSINT tool
        """
        self.session = requests.Session()
        self.base_url = "https://www.instagram.com"
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit_delay = 3
        self.downloaded_files = []
        
        # Try to load credentials from config
        self.username, self.password = self.load_credentials()
        
        # Set base directory to script location
        self.base_dir = SCRIPT_DIR
        print(f"📁 Working directory: {self.base_dir}")
        
        # Create organized folder structure
        self.create_folder_structure()
        
        # Enhanced headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
        })

    def load_credentials(self):
        """Load credentials from config.py"""
        try:
            sys.path.append(SCRIPT_DIR)
            from config import INSTAGRAM_CREDENTIALS
            
            username = INSTAGRAM_CREDENTIALS.get('username')
            password = INSTAGRAM_CREDENTIALS.get('password')
            
            if username and password:
                print("✅ Credentials loaded from config.py")
                return username, password
            else:
                print("⚠️  Config found but credentials are empty")
                return None, None
                
        except ImportError:
            print("❌ config.py not found - using public data only")
            return None, None

    def create_folder_structure(self):
        """Create organized folders in current directory"""
        self.folders = {
            'reports': os.path.join(self.base_dir, 'reports'),
            'downloads': os.path.join(self.base_dir, 'downloads'),
            'data': os.path.join(self.base_dir, 'data'),
            'logs': os.path.join(self.base_dir, 'logs')
        }
        
        for folder_name, folder_path in self.folders.items():
            os.makedirs(folder_path, exist_ok=True)
            print(f"📁 Created: {folder_path}")

    def save_report(self, target_username: str, content: str, report_type: str = "full"):
        """Save report to reports folder"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_username}_{report_type}_{timestamp}.txt"
        filepath = os.path.join(self.folders['reports'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.downloaded_files.append(filepath)
        return filepath

    def save_json_data(self, target_username: str, data: Dict, data_type: str):
        """Save JSON data to data folder"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_username}_{data_type}_{timestamp}.json"
        filepath = os.path.join(self.folders['data'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.downloaded_files.append(filepath)
        return filepath

    def rate_limit(self):
        """Implement rate limiting to avoid detection"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time + random.uniform(0.1, 0.5))
        
        self.last_request_time = time.time()
        self.request_count += 1

    def safe_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with rate limiting and error handling"""
        self.rate_limit()
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            
            if response.status_code == 429:
                print("⏳ Rate limited! Waiting 60 seconds...")
                time.sleep(60)
                return self.safe_request(url, method, **kwargs)
            elif response.status_code == 404:
                print(f"❌ Account not found: {url}")
                return None
            elif response.status_code >= 500:
                print(f"⚠️ Server error {response.status_code}, retrying...")
                time.sleep(10)
                return self.safe_request(url, method, **kwargs)
                
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def get_shared_data(self, target_username: str) -> Optional[Dict]:
        """Extract _sharedData from Instagram page"""
        url = f"{self.base_url}/{target_username}/"
        response = self.safe_request(url)
        if not response:
            return None
            
        pattern = r'window\._sharedData\s*=\s*({.+?});'
        match = re.search(pattern, response.text)
        
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse shared data: {e}")
        return None

    def get_profile_info(self, target_username: str) -> Dict:
        """Get comprehensive profile information and save to file"""
        print(f"🔍 Fetching profile info for {target_username}...")
        
        shared_data = self.get_shared_data(target_username)
        if not shared_data:
            return {'error': 'Failed to fetch profile data'}
        
        try:
            user = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']
            
            profile_info = {
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'biography': user.get('biography'),
                'followers': user.get('edge_followed_by', {}).get('count'),
                'following': user.get('edge_follow', {}).get('count'),
                'posts': user.get('edge_owner_to_timeline_media', {}).get('count'),
                'is_private': user.get('is_private'),
                'is_verified': user.get('is_verified'),
                'profile_pic_url': user.get('profile_pic_url_hd'),
                'external_url': user.get('external_url'),
                'is_business_account': user.get('is_business_account'),
                'category_name': user.get('category_name'),
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            self.save_json_data(target_username, profile_info, "profile")
            print(f"✅ Profile data saved for {target_username}")
            return profile_info
            
        except KeyError as e:
            print(f"❌ Unexpected data structure: {e}")
            return {'error': 'Unexpected data format'}

    def extract_emails_from_bio(self, target_username: str) -> List[str]:
        """Extract email addresses from profile biography"""
        profile = self.get_profile_info(target_username)
        bio = profile.get('biography', '')
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, bio)
        
        if emails:
            email_data = {
                'target': target_username,
                'emails_found': emails,
                'timestamp': datetime.datetime.now().isoformat()
            }
            self.save_json_data(target_username, email_data, "emails")
        
        return list(set(emails))

    def get_recent_posts(self, target_username: str, limit: int = 12) -> List[Dict]:
        """Get recent posts with detailed information and save to file"""
        shared_data = self.get_shared_data(target_username)
        if not shared_data:
            return []
        
        try:
            user = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']
            posts = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
            
            post_data = []
            for post in posts[:limit]:
                node = post.get('node', {})
                caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                caption = caption_edges[0].get('node', {}).get('text', '') if caption_edges else ''
                
                post_info = {
                    'id': node.get('id'),
                    'shortcode': node.get('shortcode'),
                    'timestamp': node.get('taken_at_timestamp'),
                    'is_video': node.get('is_video'),
                    'display_url': node.get('display_url'),
                    'caption': caption,
                    'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                    'likes': node.get('edge_liked_by', {}).get('count', 0),
                    'hashtags': re.findall(r'#\w+', caption),
                    'mentions': re.findall(r'@\w+', caption)
                }
                post_data.append(post_info)
            
            self.save_json_data(target_username, {'posts': post_data}, "posts")
            return post_data
            
        except KeyError as e:
            print(f"❌ Error parsing posts: {e}")
            return []

    def download_media(self, target_username: str, limit: int = 5) -> List[str]:
        """Download profile pictures and recent posts to downloads folder"""
        downloaded = []
        try:
            target_download_dir = os.path.join(self.folders['downloads'], target_username)
            os.makedirs(target_download_dir, exist_ok=True)
            
            profile = self.get_profile_info(target_username)
            
            # Download profile picture
            profile_pic_url = profile.get('profile_pic_url')
            if profile_pic_url:
                response = self.safe_request(profile_pic_url)
                if response and response.status_code == 200:
                    filename = f"{target_download_dir}/profile_picture.jpg"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    print(f"✅ Downloaded: {filename}")
                    downloaded.append(filename)
                    self.downloaded_files.append(filename)
            
            # Download recent posts
            posts = self.get_recent_posts(target_username, limit)
            for i, post in enumerate(posts):
                media_url = post.get('display_url')
                if media_url:
                    response = self.safe_request(media_url)
                    if response and response.status_code == 200:
                        filename = f"{target_download_dir}/post_{i+1}.jpg"
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        print(f"✅ Downloaded: {filename}")
                        downloaded.append(filename)
                        self.downloaded_files.append(filename)
                
                time.sleep(1)
            
            return downloaded
            
        except Exception as e:
            print(f"❌ Download error: {e}")
            return downloaded

    def get_downloaded_files_section(self) -> str:
        """Generate the downloaded files section for report"""
        if not self.downloaded_files:
            return "  ❌ No files downloaded yet"
        
        section = []
        reports = [f for f in self.downloaded_files if '/reports/' in f]
        data_files = [f for f in self.downloaded_files if '/data/' in f]
        downloads = [f for f in self.downloaded_files if '/downloads/' in f]
        
        if reports:
            section.append("  📄 Reports:")
            for file in reports:
                section.append(f"     📎 {file}")
        
        if data_files:
            section.append("  📊 Data Files:")
            for file in data_files:
                section.append(f"     📎 {file}")
        
        if downloads:
            section.append("  🖼️  Media Downloads:")
            for file in downloads:
                section.append(f"     📎 {file}")
        
        section.append(f"\n  📁 Total Files: {len(self.downloaded_files)}")
        
        return "\n".join(section)

    def generate_report(self, target_username: str) -> str:
        """Generate a comprehensive OSINT report and save to file"""
        report_content = []
        report_content.append("=" * 70)
        report_content.append(f"📊 OSINT REPORT FOR: @{target_username}")
        report_content.append(f"🕒 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append(f"📁 Base Directory: {self.base_dir}")
        report_content.append("=" * 70)
        
        # Profile Information
        report_content.append("\n👤 [PROFILE INFORMATION]")
        profile = self.get_profile_info(target_username)
        if 'error' in profile:
            report_content.append(f"  ❌ Error: {profile['error']}")
        else:
            profile_display = {
                'Username': profile.get('username'),
                'Full Name': profile.get('full_name'),
                'Followers': f"{profile.get('followers', 0):,}",
                'Following': f"{profile.get('following', 0):,}",
                'Posts': f"{profile.get('posts', 0):,}",
                'Private': 'Yes' if profile.get('is_private') else 'No',
                'Verified': 'Yes' if profile.get('is_verified') else 'No',
                'Business': 'Yes' if profile.get('is_business_account') else 'No',
                'Category': profile.get('category_name') or 'Personal'
            }
            
            for key, value in profile_display.items():
                report_content.append(f"  {key:<12}: {value}")
            
            if profile.get('biography'):
                report_content.append(f"  Bio: {profile.get('biography')}")
        
        # Email Extraction
        report_content.append("\n📧 [EMAIL EXTRACTION]")
        emails = self.extract_emails_from_bio(target_username)
        if emails:
            for email in emails:
                report_content.append(f"  📩 {email}")
        else:
            report_content.append("  ❌ No emails found in bio")
        
        # Posts Analysis
        report_content.append("\n📷 [RECENT POSTS ANALYSIS]")
        posts = self.get_recent_posts(target_username, 6)
        if posts:
            report_content.append(f"  📊 Analyzed {len(posts)} recent posts")
            total_likes = sum(post.get('likes', 0) for post in posts)
            total_comments = sum(post.get('comments', 0) for post in posts)
            report_content.append(f"  ❤️  Total Likes: {total_likes:,}")
            report_content.append(f"  💬 Total Comments: {total_comments:,}")
            report_content.append(f"  📈 Avg Likes/Post: {total_likes // len(posts) if posts else 0:,}")
        else:
            report_content.append("  ❌ No posts found or account is private")
        
        # Downloaded Files Section
        report_content.append("\n💾 [DOWNLOADED FILES]")
        report_content.append(self.get_downloaded_files_section())
        
        full_report = "\n".join(report_content)
        
        # Save the report to file
        report_path = self.save_report(target_username, full_report, "full_report")
        
        # Add final message
        full_report += f"\n\n✅ Report saved to: {report_path}"
        
        return full_report

def main():
    parser = argparse.ArgumentParser(description='Instagram OSINT Tool - Educational Purpose')
    parser.add_argument('target', help='Target Instagram username')
    parser.add_argument('--download', action='store_true', help='Download profile media')
    parser.add_argument('--report', action='store_true', help='Generate full OSINT report')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🐧 InstaOsint - Linux Instagram OSINT Tool")
    print("📁 GitHub: https://github.com/AvaBlix/InstaOsint")
    print("=" * 60)
    
    tool = InstagramOSINT()
    
    if args.report:
        report = tool.generate_report(args.target)
        print(report)
    elif args.download:
        downloaded = tool.download_media(args.target)
        print(f"\n💾 Download complete!")
        print(f"📁 Files saved in: {tool.folders['downloads']}")
        if downloaded:
            print("📄 Downloaded files:")
            for file in downloaded:
                print(f"   📎 {file}")
    else:
        print(f"🔍 Target: @{args.target}")
        print("💻 Available commands: report, download, exit")
        
        while True:
            try:
                command = input("\n[osint@linux]~$ ").strip().lower()
                
                if command == 'report':
                    report = tool.generate_report(args.target)
                    print(report)
                elif command == 'download':
                    downloaded = tool.download_media(args.target)
                    print(f"💾 Download complete! Files: {len(downloaded)}")
                elif command in ['exit', 'quit']:
                    print("👋 Exiting...")
                    break
                else:
                    print("❌ Unknown command. Available: report, download, exit")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break

if __name__ == "__main__":
    main()
                break

if __name__ == "__main__":
    main()
