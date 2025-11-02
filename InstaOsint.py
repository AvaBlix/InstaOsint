#!/usr/bin/env python3
"""
InstaOsint - Instagram OSINT Tool
Created by AvaBlix
Educational Purpose Only
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
        Created by AvaBlix
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
                    'mentions': re.findall(r'@\w+', caption),
                    'dimensions': node.get('dimensions', {})
                }
                post_data.append(post_info)
            
            self.save_json_data(target_username, {'posts': post_data}, "posts")
            return post_data
            
        except KeyError as e:
            print(f"❌ Error parsing posts: {e}")
            return []

    def get_stories(self, target_username: str) -> List[Dict]:
        """Try to get stories data"""
        try:
            url = f"{self.base_url}/stories/{target_username}/"
            response = self.safe_request(url)
            
            if response and response.status_code == 200:
                story_pattern = r'"story":{"items":\[(.*?)\]'
                match = re.search(story_pattern, response.text)
                if match:
                    try:
                        stories_data = json.loads(f'[{match.group(1)}]')
                        stories = []
                        for item in stories_data:
                            story_info = {
                                'id': item.get('id'),
                                'url': item.get('image_versions2', {}).get('candidates', [{}])[0].get('url'),
                                'is_video': item.get('media_type') == 2,
                                'timestamp': item.get('taken_at'),
                                'expiring_at': item.get('expiring_at')
                            }
                            if story_info['url']:
                                stories.append(story_info)
                        return stories
                    except:
                        pass
            return []
        except Exception as e:
            print(f"⚠️  Could not fetch stories: {e}")
            return []

    def get_hashtags_used(self, target_username: str, limit: int = 50) -> List[str]:
        """Extract hashtags from recent posts"""
        posts = self.get_recent_posts(target_username, limit)
        hashtags = []
        for post in posts:
            hashtags.extend(post.get('hashtags', []))
        return list(set(hashtags))

    def get_mentions_used(self, target_username: str, limit: int = 50) -> List[str]:
        """Extract mentions from recent posts"""
        posts = self.get_recent_posts(target_username, limit)
        mentions = []
        for post in posts:
            mentions.extend(post.get('mentions', []))
        return list(set(mentions))

    def download_media(self, target_username: str, limit: int = 20) -> List[str]:
        """Download everything from Instagram profile with perfect organization"""
        downloaded = []
        try:
            # Main profile folder
            target_download_dir = os.path.join(self.folders['downloads'], target_username)
            os.makedirs(target_download_dir, exist_ok=True)
            
            print(f"📥 Starting comprehensive download for @{target_username}...")
            print("Created by AvaBlix")
            
            # Get profile info first
            profile = self.get_profile_info(target_username)
            if 'error' in profile:
                print(f"❌ Cannot download: {profile['error']}")
                return downloaded
            
            # Create all subfolders
            folders = {
                'general': os.path.join(target_download_dir, 'general'),
                'posts': os.path.join(target_download_dir, 'posts'),
                'stories': os.path.join(target_download_dir, 'stories'),
                'highlights': os.path.join(target_download_dir, 'highlights')
            }
            
            for folder_name, folder_path in folders.items():
                os.makedirs(folder_path, exist_ok=True)
            
            # 1. GENERAL FOLDER - Profile info and basic data
            print("\n📁 Saving general profile information...")
            
            # Profile picture
            profile_pic_url = profile.get('profile_pic_url_hd') or profile.get('profile_pic_url')
            if profile_pic_url:
                response = self.safe_request(profile_pic_url)
                if response and response.status_code == 200:
                    filename = f"{folders['general']}/profile_picture.jpg"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    downloaded.append(filename)
                    self.downloaded_files.append(filename)
                    print(f"✅ Profile picture saved")
            
            # General info text file
            general_info = []
            general_info.append("=" * 60)
            general_info.append(f"INSTAGRAM PROFILE - @{target_username}")
            general_info.append(f"Created by AvaBlix")
            general_info.append(f"Captured: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            general_info.append("=" * 60)
            
            general_info.append("\n👤 BASIC INFORMATION:")
            general_info.append(f"Username: {profile.get('username')}")
            general_info.append(f"Full Name: {profile.get('full_name')}")
            general_info.append(f"Bio: {profile.get('biography', 'No biography')}")
            general_info.append(f"External URL: {profile.get('external_url', 'None')}")
            general_info.append(f"Category: {profile.get('category_name', 'Personal')}")
            
            general_info.append("\n📊 STATISTICS:")
            general_info.append(f"Followers: {profile.get('followers', 0):,}")
            general_info.append(f"Following: {profile.get('following', 0):,}")
            general_info.append(f"Total Posts: {profile.get('posts', 0):,}")
            
            general_info.append("\n🔐 ACCOUNT STATUS:")
            general_info.append(f"Private Account: {'Yes' if profile.get('is_private') else 'No'}")
            general_info.append(f"Verified: {'Yes' if profile.get('is_verified') else 'No'}")
            general_info.append(f"Business Account: {'Yes' if profile.get('is_business_account') else 'No'}")
            
            # Save general info
            general_filename = f"{folders['general']}/profile_info.txt"
            with open(general_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(general_info))
            downloaded.append(general_filename)
            self.downloaded_files.append(general_filename)
            
            # 2. POSTS FOLDER - All posts with detailed metadata
            print("\n📷 Downloading posts with complete metadata...")
            posts = self.get_recent_posts(target_username, limit)
            
            if posts:
                posts_info = []
                posts_info.append("=" * 60)
                posts_info.append(f"POSTS ANALYSIS - @{target_username}")
                posts_info.append(f"Created by AvaBlix")
                posts_info.append(f"Total Posts Analyzed: {len(posts)}")
                posts_info.append(f"Capture Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                posts_info.append("=" * 60)
                
                for i, post in enumerate(posts):
                    post_number = i + 1
                    posts_info.append(f"\n{'='*40}")
                    posts_info.append(f"POST {post_number:02d}")
                    posts_info.append(f"{'='*40}")
                    
                    # Download post media
                    media_url = post.get('display_url')
                    if media_url:
                        response = self.safe_request(media_url)
                        if response and response.status_code == 200:
                            ext = 'mp4' if post.get('is_video') else 'jpg'
                            filename = f"{folders['posts']}/post_{post_number:02d}.{ext}"
                            with open(filename, 'wb') as f:
                                f.write(response.content)
                            
                            # Get file info
                            file_size = os.path.getsize(filename)
                            file_size_mb = file_size / (1024 * 1024)
                            
                            downloaded.append(filename)
                            self.downloaded_files.append(filename)
                            
                            # Add to posts info
                            posts_info.append(f"File: post_{post_number:02d}.{ext}")
                            posts_info.append(f"Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
                            posts_info.append(f"Type: {'Video' if post.get('is_video') else 'Image'}")
                            posts_info.append(f"Dimensions: {post.get('dimensions', {}).get('height', 'N/A')}x{post.get('dimensions', {}).get('width', 'N/A')}")
                    
                    # Post metadata
                    posts_info.append(f"Post ID: {post.get('id', 'N/A')}")
                    posts_info.append(f"Shortcode: {post.get('shortcode', 'N/A')}")
                    posts_info.append(f"Timestamp: {datetime.datetime.fromtimestamp(post.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S') if post.get('timestamp') else 'N/A'}")
                    posts_info.append(f"Likes: {post.get('likes', 0):,}")
                    posts_info.append(f"Comments: {post.get('comments', 0):,}")
                    
                    # Caption and content analysis
                    caption = post.get('caption', '')
                    posts_info.append(f"Caption: {caption}")
                    posts_info.append(f"Caption Length: {len(caption)} characters")
                    
                    # Hashtags
                    hashtags = post.get('hashtags', [])
                    posts_info.append(f"Hashtags ({len(hashtags)}): {', '.join(hashtags) if hashtags else 'None'}")
                    
                    # Mentions
                    mentions = post.get('mentions', [])
                    posts_info.append(f"Mentions ({len(mentions)}): {', '.join(mentions) if mentions else 'None'}")
                    
                    # Engagement metrics
                    engagement_rate = (post.get('likes', 0) + post.get('comments', 0)) / max(profile.get('followers', 1), 1) * 100
                    posts_info.append(f"Engagement Rate: {engagement_rate:.4f}%")
                    
                    time.sleep(0.5)
                
                # Save posts info file
                posts_filename = f"{folders['posts']}/posts_analysis.txt"
                with open(posts_filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(posts_info))
                downloaded.append(posts_filename)
                self.downloaded_files.append(posts_filename)
                print(f"✅ Downloaded {len(posts)} posts with complete metadata")
            
            # 3. STORIES FOLDER - Stories with metadata
            print("\n🎬 Checking for stories...")
            stories = self.get_stories(target_username)
            
            if stories:
                stories_info = []
                stories_info.append("=" * 60)
                stories_info.append(f"STORIES ANALYSIS - @{target_username}")
                stories_info.append(f"Created by AvaBlix")
                stories_info.append(f"Total Stories: {len(stories)}")
                stories_info.append(f"Capture Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                stories_info.append("=" * 60)
                
                for i, story in enumerate(stories):
                    story_number = i + 1
                    stories_info.append(f"\n{'='*30}")
                    stories_info.append(f"STORY {story_number:02d}")
                    stories_info.append(f"{'='*30}")
                    
                    # Download story
                    story_url = story.get('url')
                    if story_url:
                        response = self.safe_request(story_url)
                        if response and response.status_code == 200:
                            ext = 'mp4' if story.get('is_video') else 'jpg'
                            filename = f"{folders['stories']}/story_{story_number:02d}.{ext}"
                            with open(filename, 'wb') as f:
                                f.write(response.content)
                            
                            file_size = os.path.getsize(filename)
                            file_size_mb = file_size / (1024 * 1024)
                            
                            downloaded.append(filename)
                            self.downloaded_files.append(filename)
                            
                            stories_info.append(f"File: story_{story_number:02d}.{ext}")
                            stories_info.append(f"Size: {file_size_mb:.2f} MB")
                            stories_info.append(f"Type: {'Video' if story.get('is_video') else 'Image'}")
                    
                    # Story metadata
                    stories_info.append(f"Story ID: {story.get('id', 'N/A')}")
                    stories_info.append(f"Timestamp: {datetime.datetime.fromtimestamp(story.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S') if story.get('timestamp') else 'N/A'}")
                    stories_info.append(f"Expires at: {datetime.datetime.fromtimestamp(story.get('expiring_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if story.get('expiring_at') else 'N/A'}")
                    
                    time.sleep(0.5)
                
                # Save stories info
                stories_filename = f"{folders['stories']}/stories_analysis.txt"
                with open(stories_filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(stories_info))
                downloaded.append(stories_filename)
                self.downloaded_files.append(stories_filename)
                print(f"✅ Downloaded {len(stories)} stories")
            else:
                print("ℹ️  No stories available")
            
            # 4. HIGHLIGHTS FOLDER - Highlights info
            print("\n🌟 Checking for highlights...")
            highlights_info = []
            highlights_info.append("=" * 60)
            highlights_info.append(f"HIGHLIGHTS INFO - @{target_username}")
            highlights_info.append(f"Created by AvaBlix")
            highlights_info.append(f"Note: Highlights require authentication to download")
            highlights_info.append(f"Capture Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            highlights_info.append("=" * 60)
            highlights_info.append("\nHighlights data requires Instagram authentication.")
            highlights_info.append("This section would contain highlight cover images, titles,")
            highlights_info.append("and story IDs if authentication was available.")
            
            highlights_filename = f"{folders['highlights']}/highlights_info.txt"
            with open(highlights_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(highlights_info))
            downloaded.append(highlights_filename)
            self.downloaded_files.append(highlights_filename)
            
            # Final summary
            print(f"\n🎉 Download complete!")
            print(f"📁 Organized in: {target_download_dir}")
            print(f"📊 Total files downloaded: {len(downloaded)}")
            print(f"📷 Posts: {len(posts) if posts else 0}")
            print(f"🎬 Stories: {len(stories) if stories else 0}")
            print("Tool created by AvaBlix")
            
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
        report_content.append(f"👩‍💻 Created by: AvaBlix")
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
        full_report += f"\n👩‍💻 Tool created by AvaBlix"
        
        return full_report

def main():
    parser = argparse.ArgumentParser(description='Instagram OSINT Tool - Created by AvaBlix')
    parser.add_argument('target', help='Target Instagram username')
    parser.add_argument('--download', action='store_true', help='Download profile media')
    parser.add_argument('--report', action='store_true', help='Generate full OSINT report')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🐧 InstaOsint - Linux Instagram OSINT Tool")
    print("👩‍💻 Created by AvaBlix")
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
        print("👩‍💻 Created by AvaBlix")
        
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
                    print("👩‍💻 Tool created by AvaBlix")
                    break
                else:
                    print("❌ Unknown command. Available: report, download, exit")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                print("👩‍💻 Tool created by AvaBlix")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
