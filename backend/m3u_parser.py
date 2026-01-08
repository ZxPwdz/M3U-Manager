import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ChannelData:
    name: str
    stream_url: str
    tvg_id: Optional[str] = None
    tvg_name: Optional[str] = None
    tvg_logo: Optional[str] = None
    group_title: Optional[str] = None


def parse_m3u(content: str) -> List[ChannelData]:
    """Parse M3U/M3U8 content and extract channel information."""
    channels = []
    lines = content.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and the #EXTM3U header
        if not line or line.upper() == '#EXTM3U':
            i += 1
            continue

        # Look for #EXTINF lines
        if line.startswith('#EXTINF:'):
            extinf_line = line
            stream_url = None

            # Get the stream URL (next non-empty, non-comment line)
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line and not next_line.startswith('#'):
                    stream_url = next_line
                    break
                elif next_line.startswith('#EXTINF:'):
                    # Another EXTINF without URL, skip previous
                    i -= 1
                    break
                i += 1

            if stream_url:
                channel = parse_extinf(extinf_line, stream_url)
                if channel:
                    channels.append(channel)

        i += 1

    return channels


def parse_extinf(extinf_line: str, stream_url: str) -> Optional[ChannelData]:
    """Parse a single #EXTINF line and extract attributes."""
    # Remove #EXTINF: prefix
    content = extinf_line[8:] if extinf_line.startswith('#EXTINF:') else extinf_line

    # Extract attributes using regex
    tvg_id = extract_attribute(content, 'tvg-id')
    tvg_name = extract_attribute(content, 'tvg-name')
    tvg_logo = extract_attribute(content, 'tvg-logo')
    group_title = extract_attribute(content, 'group-title')

    # Extract display name (after the comma)
    name_match = re.search(r',(.+)$', content)
    name = name_match.group(1).strip() if name_match else 'Unknown Channel'

    # Use tvg-name as fallback for name if empty
    if name == 'Unknown Channel' and tvg_name:
        name = tvg_name

    return ChannelData(
        name=name,
        stream_url=stream_url,
        tvg_id=tvg_id,
        tvg_name=tvg_name,
        tvg_logo=tvg_logo,
        group_title=group_title
    )


def extract_attribute(content: str, attr_name: str) -> Optional[str]:
    """Extract an attribute value from EXTINF content."""
    # Match attribute="value" or attribute='value'
    pattern = rf'{attr_name}=["\']([^"\']*)["\']'
    match = re.search(pattern, content, re.IGNORECASE)
    return match.group(1) if match else None


def generate_m3u(channels: List) -> str:
    """Generate M3U content from channel list."""
    lines = ['#EXTM3U']

    for channel in channels:
        # Build EXTINF line
        extinf_parts = ['-1']

        if channel.tvg_id:
            extinf_parts.append(f'tvg-id="{channel.tvg_id}"')
        if channel.tvg_name:
            extinf_parts.append(f'tvg-name="{channel.tvg_name}"')
        if channel.tvg_logo:
            extinf_parts.append(f'tvg-logo="{channel.tvg_logo}"')
        if channel.group_title:
            extinf_parts.append(f'group-title="{channel.group_title}"')

        # Join parts and add channel name
        extinf_line = '#EXTINF:' + ' '.join(extinf_parts) + ',' + channel.name
        lines.append(extinf_line)
        lines.append(channel.stream_url)
        lines.append('')  # Empty line between entries

    return '\n'.join(lines)
