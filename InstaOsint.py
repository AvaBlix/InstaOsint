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

class InstagramOSINT:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.instagram.com"
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit_delay = 2
        self.downloaded_files = []
        
        # Set base directory
        self.base_dir = os.getcwd()
        print(f"🐧 InstaOsint - Created by AvaBlix")
        print(f"📁 Working directory: {self.base_dir}")
        
        # Create folders
        self.folders = {
            'reports': os.path.join(self.base_dir, 'reports'),
            'downloads': os.path.join(self.base_dir, 'downloads'),
            'data': os.path.join(self.base_dir, 'data')
        }
        
        for folder_path in self.folders.values():
            os.makedirs(folder_path, exist_ok=True)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def rate_limit(self):
        current_time = time.time()
        if current_time - self.last_request_time < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay)
        self.last_request_time = time.time()

    def make_request(self, url: str) -> Optional[requests.Response]:
        self.rate_limit()
        try:
            response = self.session.get(url, timeout=10)
            return response
        except:
            return None

    def get_profile_data(self, username: str) -> Optional[Dict]:
        url = f"{self.base_url}/{username}/"
        response = self.make_request(url)
        
        if not response or response.status_code != 200:
            return None
            
        # Find JSON data in page
        patterns = [
            r'window\._sharedData\s*=\s*({.+?});',
            r'{"config":.*?}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    continue
        return None

    def extract_profile_info(self, username: str) -> Dict:
        data = self.get_profile_data(username)
        if not data:
            return {'error': 'Could not fetch profile data'}
        
        try:
            user = data['entry_data']['ProfilePage'][0]['graphql']['user']
            
            return {
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'biography': user.get('biography'),
                'followers': user.get('edge_followed_by', {}).get('count'),
                'following': user.get('edge_follow', {}).get('count'),
                'posts_count': user.get('edge_owner_to_timeline_media', {}).get('count'),
                'is_private': user.get('is_private'),
                'is_verified': user.get('is_verified'),
                'profile_pic_url': user.get('profile_pic_url_hd'),
                'external_url': user.get('external_url'),
                'is_business': user.get('is_business_account'),
                'category': user.get('category_name'),
            }
        except:
            return {'error': 'Failed to parse profile data'}

    def extract_posts(self, username: str, limit: int = 12) -> List[Dict]:
        data = self.get_profile_data(username)
        if not data:
            return []
        
        try:
            user = data['entry_data']['ProfilePage'][0]['graphql']['user']
            posts = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
            
            post_data = []
            for post in posts[:limit]:
                node = post.get('node', {})
                
                # Get caption
                caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                caption = caption_edges[0].get('node', {}).get('text', '') if caption_edges else ''
                
                post_info = {
                    'id': node.get('id'),
                    'shortcode': node.get('shortcode'),
                    'timestamp': node.get('taken_at_timestamp'),
                    'is_video': node.get('is_video'),
                    'display_url': node.get('display_url'),
                    'video_url': node.get('video_url'),
                    'caption': caption,
                    'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                    'likes': node.get('edge_liked_by', {}).get('count', 0),
                    'dimensions': node.get('dimensions', {}),
                    'hashtags': re.findall(r'#\w+', caption),
                    'mentions': re.findall(r'@\w+', caption),
                    'location': node.get('location')
                }
                post_data.append(post_info)
            
            return post_data
        except:
            return []

    def download_file(self, url: str, filepath: str) -> bool:
        try:
            response = self.make_request(url)
            if response and response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except:
            pass
        return False

    def generate_report(self, username: str) -> str:
        print(f"🔍 Generating report for @{username}...")
        
        profile = self.extract_profile_info(username)
        if 'error' in profile:
            return f"❌ Error: {profile['error']}"
        
        posts = self.extract_posts(username, 6)
        
        report = []
        report.append("=" * 60)
        report.append(f"INSTAOSINT REPORT - @{username}")
        report.append(f"Created by AvaBlix")
        report.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        # Profile Info
        report.append("\n👤 PROFILE INFORMATION")
        report.append(f"Username: {profile.get('username')}")
        report.append(f"Full Name: {profile.get('full_name')}")
        report.append(f"Bio: {profile.get('biography', 'No bio')}")
        report.append(f"Followers: {profile.get('followers', 0):,}")
        report.append(f"Following: {profile.get('following', 0):,}")
        report.append(f"Posts: {profile.get('posts_count', 0):,}")
        report.append(f"Private: {'Yes' if profile.get('is_private') else 'No'}")
        report.append(f"Verified: {'Yes' if profile.get('is_verified') else 'No'}")
        report.append(f"Business: {'Yes' if profile.get('is_business') else 'No'}")
        report.append(f"Category: {profile.get('category', 'N/A')}")
        report.append(f"External URL: {profile.get('external_url', 'None')}")
        
        # Email extraction
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile.get('biography', ''))
        report.append(f"\n📧 EMAILS FOUND: {len(emails)}")
        for email in emails:
            report.append(f"  {email}")
        
        # Posts analysis
        report.append(f"\n📷 RECENT POSTS ANALYSIS")
        report.append(f"Posts analyzed: {len(posts)}")
        if posts:
            total_likes = sum(p.get('likes', 0) for p in posts)
            total_comments = sum(p.get('comments', 0) for p in posts)
            report.append(f"Total likes: {total_likes:,}")
            report.append(f"Total comments: {total_comments:,}")
            report.append(f"Average likes: {total_likes // len(posts):,}")
        
        # Hashtags and mentions
        all_hashtags = []
        all_mentions = []
        for post in posts:
            all_hashtags.extend(post.get('hashtags', []))
            all_mentions.extend(post.get('mentions', []))
        
        report.append(f"\n🏷️ TOP HASHTAGS ({len(set(all_hashtags))} unique)")
        for tag in list(set(all_hashtags))[:10]:
            report.append(f"  {tag}")
        
        report.append(f"\n👥 MENTIONS ({len(set(all_mentions))} unique)")
        for mention in list(set(all_mentions))[:10]:
            report.append(f"  {mention}")
        
        return "\n".join(report)

    def download_all_media(self, username: str) -> List[str]:
        print(f"📥 Starting download for @{username}...")
        
        profile = self.extract_profile_info(username)
        if 'error' in profile:
            print(f"❌ {profile['error']}")
            return []
        
        # Create main folder structure
        main_folder = os.path.join(self.folders['downloads'], username)
        folders = {
            'general': os.path.join(main_folder, 'general'),
            'posts': os.path.join(main_folder, 'posts'), 
            'stories': os.path.join(main_folder, 'stories'),
            'highlights': os.path.join(main_folder, 'highlights')
        }
        
        for folder in folders.values():
            os.makedirs(folder, exist_ok=True)
        
        downloaded_files = []
        
        # 1. Download profile picture
        print("🖼️ Downloading profile picture...")
        profile_pic_url = profile.get('profile_pic_url')
        if profile_pic_url:
            profile_pic_path = os.path.join(folders['general'], 'profile_picture.jpg')
            if self.download_file(profile_pic_url, profile_pic_path):
                downloaded_files.append(profile_pic_path)
                print("✅ Profile picture downloaded")
        
        # 2. Save profile info
        print("📄 Saving profile information...")
        profile_info = [
            "=" * 50,
            f"PROFILE INFO - @{username}",
            f"Created by AvaBlix",
            f"Captured: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 50,
            f"Username: {profile.get('username')}",
            f"Full Name: {profile.get('full_name')}",
            f"Bio: {profile.get('biography', 'No bio')}",
            f"Followers: {profile.get('followers', 0):,}",
            f"Following: {profile.get('following', 0):,}",
            f"Posts: {profile.get('posts_count', 0):,}",
            f"Private: {'Yes' if profile.get('is_private') else 'No'}",
            f"Verified: {'Yes' if profile.get('is_verified') else 'No'}",
            f"Business: {'Yes' if profile.get('is_business') else 'No'}",
            f"Category: {profile.get('category', 'N/A')}",
            f"External URL: {profile.get('external_url', 'None')}",
        ]
        
        profile_info_path = os.path.join(folders['general'], 'profile_info.txt')
        with open(profile_info_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(profile_info))
        downloaded_files.append(profile_info_path)
        
        # 3. Download posts
        print("📷 Downloading posts...")
        posts = self.extract_posts(username, 8)
        
        if posts:
            posts_info = []
            posts_info.append("=" * 50)
            posts_info.append(f"POSTS ANALYSIS - @{username}")
            posts_info.append(f"Total Posts: {len(posts)}")
            posts_info.append("=" * 50)
            
            for i, post in enumerate(posts):
                post_num = i + 1
                posts_info.append(f"\n{'='*30}")
                posts_info.append(f"POST {post_num:02d}")
                posts_info.append(f"{'='*30}")
                
                # Download media
                media_url = post.get('display_url')
                if media_url:
                    ext = 'mp4' if post.get('is_video') else 'jpg'
                    media_path = os.path.join(folders['posts'], f'post_{post_num:02d}.{ext}')
                    
                    if self.download_file(media_url, media_path):
                        downloaded_files.append(media_path)
                        file_size = os.path.getsize(media_path)
                        
                        posts_info.append(f"File: post_{post_num:02d}.{ext}")
                        posts_info.append(f"Size: {file_size / (1024*1024):.2f} MB")
                        posts_info.append(f"Type: {'Video' if post.get('is_video') else 'Image'}")
                        posts_info.append(f"Dimensions: {post.get('dimensions', {}).get('height', 'N/A')}x{post.get('dimensions', {}).get('width', 'N/A')}")
                
                # Post metadata
                posts_info.append(f"ID: {post.get('id', 'N/A')}")
                posts_info.append(f"Shortcode: {post.get('shortcode', 'N/A')}")
                posts_info.append(f"Timestamp: {datetime.datetime.fromtimestamp(post.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S') if post.get('timestamp') else 'N/A'}")
                posts_info.append(f"Likes: {post.get('likes', 0):,}")
                posts_info.append(f"Comments: {post.get('comments', 0):,}")
                posts_info.append(f"Caption: {post.get('caption', 'No caption')}")
                posts_info.append(f"Hashtags: {', '.join(post.get('hashtags', []))}")
                posts_info.append(f"Mentions: {', '.join(post.get('mentions', []))}")
                
                if post.get('location'):
                    posts_info.append(f"Location: {post.get('location', {}).get('name', 'N/A')}")
                
                time.sleep(0.5)
            
            # Save posts analysis
            posts_info_path = os.path.join(folders['posts'], 'posts_analysis.txt')
            with open(posts_info_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(posts_info))
            downloaded_files.append(posts_info_path)
            print(f"✅ Downloaded {len(posts)} posts")
        
        # 4. Create stories info (stories require authentication)
        print("🎬 Creating stories info...")
        stories_info = [
            "=" * 50,
            "STORIES INFORMATION",
            "Note: Stories download requires Instagram authentication",
            "This would contain story media and metadata if available",
            "=" * 50
        ]
        
        stories_info_path = os.path.join(folders['stories'], 'stories_info.txt')
        with open(stories_info_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(stories_info))
        downloaded_files.append(stories_info_path)
        
        # 5. Create highlights info
        print("🌟 Creating highlights info...")
        highlights_info = [
            "=" * 50,
            "HIGHLIGHTS INFORMATION", 
            "Note: Highlights download requires Instagram authentication",
            "This would contain highlight covers and stories if available",
            "=" * 50
        ]
        
        highlights_info_path = os.path.join(folders['highlights'], 'highlights_info.txt')
        with open(highlights_info_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(highlights_info))
        downloaded_files.append(highlights_info_path)
        
        print(f"🎉 Download complete!")
        print(f"📁 Files saved in: {main_folder}")
        print(f"📊 Total files: {len(downloaded_files)}")
        print("👩‍💻 Created by AvaBlix")
        
        return downloaded_files

def main():
    parser = argparse.ArgumentParser(description='Instagram OSINT Tool - Created by AvaBlix')
    parser.add_argument('username', help='Instagram username to analyze')
    parser.add_argument('--report', action='store_true', help='Generate OSINT report')
    parser.add_argument('--download', action='store_true', help='Download all media')
    
    args = parser.parse_args()
    
    tool = InstagramOSINT()
    
    if args.report:
        report = tool.generate_report(args.username)
        print(report)
        
        # Save report to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(tool.folders['reports'], f"{args.username}_report_{timestamp}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n💾 Report saved to: {report_file}")
        
    elif args.download:
        tool.download_all_media(args.username)
    else:
        # Interactive mode
        print(f"\n🔍 Analyzing: @{args.username}")
        print("Commands: report, download, exit")
        
        while True:
            try:
                cmd = input("\n[osint]~$ ").strip().lower()
                
                if cmd == 'report':
                    report = tool.generate_report(args.username)
                    print(report)
                elif cmd == 'download':
                    tool.download_all_media(args.username)
                elif cmd in ['exit', 'quit']:
                    break
                else:
                    print("Commands: report, download, exit")
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    main()
