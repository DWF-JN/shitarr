# custom_libs/subliminal_patch/providers/subtitlecat.py
from __future__ import absolute_import
import logging
import re

from bs4 import BeautifulSoup
from requests import Session

#from subliminal_patch.providers import Provider
from subliminal.providers import Provider
from subliminal_patch.subtitle import Subtitle
from subliminal.video import Episode, Movie
from subliminal.subtitle import guess_matches
from subliminal import Language

logger = logging.getLogger(__name__)

class SubtitleCatProvider(Provider):
    """SubtitleCat.com provider."""

    languages = {Language.fromietf(l) for l in [
        'ar', 'bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'he',
        'hr', 'hu', 'id', 'it', 'ja', 'ko', 'nl', 'no', 'pl', 'pt', 'pt-BR',
        'ro', 'ru', 'sv', 'th', 'tr', 'uk', 'vi', 'zh', 'zh-CN', 'zh-TW'
    ]}

    video_types = (Episode, Movie)
    server_url = 'https://www.subtitlecat.com/'
    search_url = server_url + 'index.php'

    def __init__(self):
        self.session = Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        })

    def list_subtitles(self, video, languages):
        subtitles = []
        if isinstance(video, Movie):
            query = f"{video.title} {video.year}" if video.year else video.title
        else:
            query = f"{video.series} S{video.season:02d}E{video.episode:02d}"

        params = {'search': query, 'show': '1000'}

        try:
            logger.info(f"SubtitleCat: Searching for {query}")
            r = self.session.get(self.search_url, params=params, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"SubtitleCat: Search failed: {e}")
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all('tr')

        for row in rows:
            link_tag = row.find('a')
            if not link_tag:
                continue
            href = link_tag.get('href')
            if not href or not href.startswith('subs/'):
                continue

            result_title = link_tag.get_text(strip=True)
            result_title = re.sub(r'\s*\(translated from .+?\)', '', result_title).strip()

            if not guess_matches(video, result_title):
                continue

            detail_url = self.server_url + href
            subs = self._parse_detail_page(detail_url, languages, video)
            subtitles.extend(subs)

        return subtitles

    def _parse_detail_page(self, detail_url, languages, video):
        subtitles = []
        try:
            r = self.session.get(detail_url, timeout=10)
            r.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        match = re.search(r'/subs/(\d+)/', detail_url)
        if not match:
            return []

        base_filename = detail_url.split('/')[-1].replace('.html', '')

        lang_links = soup.find_all('a', href=re.compile(r'\.srt$'))
        for link in lang_links:
            href = link.get('href')
            if not href:
                continue
            lang_match = re.search(r'-([a-z]{2,}-?[A-Z]{0,2})\.srt$', href)
            if not lang_match:
                continue
            lang_code = lang_match.group(1).replace('-', '_').lower()
            try:
                lang = Language.fromietf(lang_code)
            except Exception:
                continue
            if lang not in languages:
                continue

            srt_url = self.server_url.rstrip('/') + href
            subtitle = Subtitle(
                language=lang,
                id=srt_url,
                provider='subtitlecat',
                video=video,
                release_info=base_filename
            )
            subtitles.append(subtitle)

        return subtitles

    def download_subtitle(self, subtitle):
        try:
            logger.info(f"SubtitleCat: Downloading {subtitle.id}")
            r = self.session.get(subtitle.id, timeout=10)
            r.raise_for_status()
            subtitle.content = r.content
            return subtitle.content
        except Exception as e:
            logger.error(f"SubtitleCat: Download failed: {e}")
            return None
