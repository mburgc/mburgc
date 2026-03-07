#!/usr/bin/env python3
"""
GitHub Metrics Dashboard - Global User Metrics Visualization
Shows aggregated metrics across ALL user repositories (profile-wide, not repo-specific).

Fetches real data from GitHub API for comprehensive profile metrics.
"""

import base64
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

# Install dependencies
try:
    import requests
except ImportError:
    print("Installing requests library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing Pillow library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw


# GitHub username and token configuration
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "mburgc")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def fetch_github_profile_metrics() -> Dict[str, int]:
    """
    Fetch REAL GitHub profile metrics using GitHub API.
    Returns aggregated metrics across ALL user repositories.
    """
    print("\n[SEARCH] Fetching real GitHub profile metrics...")

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Metrics-Dashboard",
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    base_url = "https://api.github.com"

    # Get authenticated user or public user data
    user_url = f"{base_url}/users/{GITHUB_USERNAME}"

    try:
        # Fetch user profile
        user_resp = requests.get(user_url, headers=headers, timeout=10)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        # Extract profile-wide metrics
        followers = user_data.get("followers", 0)
        following = user_data.get("following", 0)
        public_repos = user_data.get("public_repos", 0)

        print(f"   Profile: {user_data.get('name', GITHUB_USERNAME)}")
        print(
            f"   Followers: {followers} | Following: {following} | Public Repos: {public_repos}"
        )

        # Fetch ALL repositories to aggregate metrics (not just one repo)
        all_repos_url = f"{base_url}/users/{GITHUB_USERNAME}/repos"
        params = {"per_page": 100, "type": "all", "sort": "updated"}

        all_repos = []
        page = 1

        while True:
            resp = requests.get(
                all_repos_url,
                headers=headers,
                params={**params, "page": page},
                timeout=10,
            )
            resp.raise_for_status()
            repos_page = resp.json()

            if not repos_page:
                break

            all_repos.extend(repos_page)
            page += 1

            if len(repos_page) < 100:
                break

        print(f"   Fetched {len(all_repos)} repositories...")

        # Aggregate metrics across ALL repos
        total_stars = 0
        total_forks = 0
        total_open_issues = 0
        total_prs = 0

        for repo in all_repos:
            total_stars += repo.get("stargazers_count", 0)
            total_forks += repo.get("forks_count", 0)

            # Count open issues (exclude PRs which GitHub treats as issues)
            open_issues = repo.get("open_issues_count", 0)
            total_open_issues += open_issues

        # Fetch PR count (profile-wide)
        prs_url = f"{base_url}/search/issues"
        pr_params = {"q": f"author:{GITHUB_USERNAME} is:pr is:merged", "per_page": 1}

        try:
            pr_resp = requests.get(
                prs_url, headers=headers, params=pr_params, timeout=10
            )
            if pr_resp.ok:
                pr_data = pr_resp.json()
                total_prs = pr_data.get("total_count", 0)
        except Exception as e:
            print(f"   Warning: Could not fetch PR count: {e}")
            total_prs = 0

        metrics = {
            "stars": total_stars,
            "forks": total_forks,
            "open_issues": total_open_issues,
            "followers": followers,
            "repos": public_repos,
            "prs": total_prs,
            "contributors": 0,  # Would need additional API calls for accurate count
        }

        print(f"\n[STATS] Aggregated Profile Metrics:")
        print(f"   [*] Total Stars: {total_stars:,}")
        print(f"   [~] Total Forks: {total_forks:,}")
        print(f"   [!] Open Issues: {total_open_issues:,}")
        print(f"   [@] Followers: {followers:,}")
        print(f"   [R] Repositories: {public_repos:,}")
        print(f"   [M] Pull Requests: {total_prs:,}")

        return metrics

    except requests.exceptions.RequestException as e:
        print(f"   [WARNING] Error fetching from GitHub API: {e}")
        print("   Using mock data for demonstration...")
        return {
            "stars": 0,
            "forks": 0,
            "open_issues": 0,
            "followers": 0,
            "repos": 0,
            "prs": 0,
            "contributors": 0,
        }


def get_github_avatar_url() -> Optional[str]:
    """Fetch the user's GitHub avatar URL."""
    try:
        user_url = f"https://api.github.com/users/{GITHUB_USERNAME}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Metrics-Dashboard",
        }

        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        resp = requests.get(user_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("avatar_url")
    except Exception:
        return None


# ============================================================
# MAIN EXECUTION - Fetch metrics first
# ============================================================

if __name__ == "__main__":
    # Get real metrics from GitHub API
    metrics = fetch_github_profile_metrics()

    # Global user metrics (aggregated across all repos)
    stars = metrics.get("stars", 0)
    forks = metrics.get("forks", 0)
    issues = metrics.get("open_issues", 0)
    followers = metrics.get("followers", 0)
    repos = metrics.get("repos", 0)
    prs = metrics.get("prs", 0)
    contributors = metrics.get("contributors", 0)

    # Create assets directory
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)

    # Save metrics data
    metrics_data = {
        "stars": stars,
        "forks": forks,
        "issues": issues,
        "followers": followers,
        "repos": repos,
        "prs": prs,
        "contributors": contributors,
    }
    with open("metrics_data.json", "w") as f:
        json.dump(metrics_data, f, indent=2)

    # ============================================================
    # VISUALIZATION CLASSES - High Resolution, 2x2 Grid Support
    # ============================================================

    class Colors:
        """Color palettes for different metric types."""

        STAR = {
            "primary": (255, 200, 80),
            "secondary": (255, 150, 50),
            "glow": (255, 220, 150),
            "bg": (12, 10, 18),
        }
        FORK = {
            "primary": (150, 120, 255),
            "secondary": (80, 200, 255),
            "glow": (200, 180, 255),
            "bg": (12, 10, 18),
        }
        ISSUE = {
            "primary": (255, 100, 70),
            "secondary": (255, 160, 100),
            "glow": (255, 200, 160),
            "bg": (18, 12, 12),
        }
        FOLLOWER = {
            "primary": (80, 210, 150),
            "secondary": (100, 170, 240),
            "glow": (170, 240, 210),
            "bg": (10, 12, 15),
        }
        PR = {
            "primary": (100, 180, 255),
            "secondary": (80, 220, 180),
            "glow": (150, 230, 220),
            "bg": (10, 15, 20),
        }

    class Particle:
        """Animated particle for visual effects."""

        def __init__(self, x, y, vx, vy, size, color, life=1.0, decay=0.02):
            self.x, self.y = x, y
            self.vx, self.vy = vx, vy
            self.base_size = max(0.5, float(size))
            self.size = self.base_size
            self.color = color
            self.life = min(1.0, max(0.1, float(life)))
            self.decay = max(0.005, min(0.05, float(decay)))
            self.pulse = random.random() * 6.28

        def update(self):
            self.x += self.vx
            self.y += self.vy
            self.life -= self.decay
            self.pulse += 0.15
            if self.life < 0.1:
                self.life = 0.1
            return self.life > 0.05

        def get_size(self):
            pulse_factor = 0.85 + 0.15 * math.sin(self.pulse)
            return self.base_size * self.life * pulse_factor

    class ParticleSystem:
        """Manages particle animations."""

        def __init__(self, w, h):
            self.w, self.h = w, h
            self.particles = []

        def spawn(
            self,
            x,
            y,
            count=1,
            size=3.0,
            speed=1.5,
            color=(255, 255, 255),
            life=1.0,
            decay=0.02,
            angle=None,
        ):
            size = max(0.5, float(size))
            speed = max(0.1, float(speed))
            for _ in range(count):
                a = angle if angle is not None else random.random() * 6.28
                s = speed * (0.5 + random.random() * 0.5)
                self.particles.append(
                    Particle(
                        x, y, math.cos(a) * s, math.sin(a) * s, size, color, life, decay
                    )
                )

        def update(self):
            self.particles = [p for p in self.particles if p.update()]

        def render(self, img):
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)

            for p in self.particles:
                sz = p.get_size() * 3.0  # Larger glow
                alpha = int(80 * p.life)
                glow_draw.ellipse(
                    [p.x - sz, p.y - sz, p.x + sz, p.y + sz], fill=p.color + (alpha,)
                )

            img_p = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
            draw = ImageDraw.Draw(img_p)

            for p in self.particles:
                sz = p.get_size()
                draw.ellipse([p.x - sz, p.y - sz, p.x + sz, p.y + sz], fill=p.color)

            return img_p

    class MetricVisualizer:
        """Base class for metric visualizations with high resolution."""

        def __init__(self, w, h, palette, label):
            self.w, self.h = w, h
            self.palette = palette
            self.label = label
            self.system = ParticleSystem(w, h)
            # Hero number dominates the canvas
            self.value_font_size = max(72, int(h * 0.30))
            self.label_font_size = max(18, int(h * 0.075))

        def _load_font(self, size):
            """Load a font with graceful fallback across platforms."""
            from PIL import ImageFont

            for path in [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
            return ImageFont.load_default()

        def _draw_glow_text(self, img_rgb, text, pos, font, color, glow_color=None):
            """Draw text with a multi-layer neon glow halo via RGBA compositing."""
            if glow_color is None:
                glow_color = color
            overlay = Image.new("RGBA", img_rgb.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            x, y = pos
            # Concentric halo layers: large radius = very transparent
            for r, alpha in [(12, 18), (8, 35), (5, 65), (3, 105), (1, 160)]:
                gc = glow_color[:3] + (alpha,)
                step = max(1, r // 2)
                for dx in range(-r, r + 1, step):
                    for dy in range(-r, r + 1, step):
                        d.text((x + dx, y + dy), text, fill=gc, font=font)
            # Crisp main text on top
            d.text(pos, text, fill=color[:3] + (255,), font=font)
            return Image.alpha_composite(img_rgb.convert("RGBA"), overlay).convert("RGB")

        def _make_background(self, metric_value, frame_idx, total_frames):
            """Draw background radial glow + logarithmic progress arc. No text."""
            img = Image.new("RGB", (self.w, self.h), self.palette["bg"])
            draw = ImageDraw.Draw(img)
            t = (frame_idx / max(1, total_frames)) * 2 * math.pi
            cx, cy = self.w / 2, self.h / 2

            # Radial bg glow: paint concentric circles outside→inside so inner = brightest
            glow_r = int(min(self.w, self.h) * 0.44)
            for radius in range(glow_r, 0, -6):
                factor = (1.0 - radius / glow_r) * 0.40
                gc = tuple(
                    min(255, int(self.palette["bg"][i] + self.palette["glow"][i] * factor))
                    for i in range(3)
                )
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=gc)

            # Logarithmic progress arc (full at ~30 000 units)
            log_val = math.log10(max(1, metric_value) + 1)
            level = min(1.0, log_val / 4.5)
            arc_sweep = int(level * 250)
            arc_pad = 16

            arc_box = [arc_pad, arc_pad, self.w - arc_pad, self.h - arc_pad]
            # Dim track ring
            track_col = tuple(min(255, int(c * 0.22)) for c in self.palette["secondary"])
            draw.arc(arc_box, start=145, end=395, fill=track_col, width=3)
            # Bright progress fill
            if arc_sweep > 1:
                draw.arc(arc_box, start=145, end=145 + arc_sweep, fill=self.palette["primary"], width=5)
                # Pulsing glowing dot at arc tip
                tip_rad = math.radians(145 + arc_sweep)
                tip_rx = (self.w - 2 * arc_pad) / 2 - 2
                tip_ry = (self.h - 2 * arc_pad) / 2 - 2
                tip_x = cx + math.cos(tip_rad) * tip_rx
                tip_y = cy + math.sin(tip_rad) * tip_ry
                pulse = 4 + 2 * math.sin(t * 3)
                draw.ellipse(
                    [tip_x - pulse, tip_y - pulse, tip_x + pulse, tip_y + pulse],
                    fill=self.palette["glow"],
                )
            return img

        def _overlay_text(self, img, metric_value, frame_idx, total_frames):
            """Stamp label + big glowing number on top of whatever is already in img."""
            value_font = self._load_font(self.value_font_size)
            label_font = self._load_font(self.label_font_size)
            draw = ImageDraw.Draw(img)

            # Label (metric name) — centred near top
            bbox = draw.textbbox((0, 0), self.label, font=label_font)
            lw = bbox[2] - bbox[0]
            draw.text(
                (int((self.w - lw) / 2), 22),
                self.label,
                fill=self.palette["secondary"],
                font=label_font,
            )

            # Big glowing number centred vertically
            value_str = f"{metric_value:,}"
            bbox = draw.textbbox((0, 0), value_str, font=value_font)
            vw, vh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            vx = int((self.w - vw) / 2)
            vy = int((self.h - vh) / 2) + 4
            img = self._draw_glow_text(
                img, value_str, (vx, vy), value_font,
                self.palette["primary"], self.palette["glow"],
            )
            return img

        def make_frame(self, metric_value, frame_idx, total_frames):
            """Combined background + text (legacy / fallback path)."""
            img = self._make_background(metric_value, frame_idx, total_frames)
            return self._overlay_text(img, metric_value, frame_idx, total_frames)

        def animate_frame(self, img, metric_value, frame_idx, total_frames):
            pass

        def animate(self, metric_value, path, frames=40, fps=15):
            """Generate animated GIF — text is always drawn last (on top of particles)."""
            print(f"  {self.label}: {metric_value:,} ({frames} frames)...")
            result_frames = []

            import random
            random.seed(42)

            # Pre-seed background particles
            for _ in range(30):
                self.system.spawn(
                    random.uniform(20, self.w - 20),
                    random.uniform(50, self.h - 80),
                    1,
                    2.5,
                    0.35,
                    self.palette["glow"],
                    0.85,
                    0.012,
                )

            for i in range(frames):
                # 1. Background + arc
                frame = self._make_background(metric_value, i, frames)
                # 2. Geometry + particles (drawn by each subclass)
                self.animate_frame(frame, metric_value, i, frames)
                # 3. Text always on top of particles
                frame = self._overlay_text(frame, metric_value, i, frames)
                if frame.mode != "RGB":
                    frame = frame.convert("RGB")
                result_frames.append(frame)

            # CROSSFADE INTERPOLATION for smooth looping
            # Blend from last frame back to first frame for seamless transition
            crossfade_frames = 8
            first_frame = result_frames[0].copy()
            last_frame = result_frames[-1].copy()

            crossfade_result = []

            # Add first part of animation (non-crossfaded)
            for i in range(frames - crossfade_frames):
                crossfade_result.append(result_frames[i])

            # Create crossfade transition frames: interpolate from last_frame to first_frame
            for i in range(crossfade_frames):
                # Blend from last_frame (1.0) to first_frame (0.0) - reverse order for smooth return
                blend = i / (crossfade_frames - 1)
                blended = Image.blend(last_frame, first_frame, blend)
                crossfade_result.append(blended)

            # Convert all frames to palette mode
            palette_frames = []
            for f in crossfade_result:
                if f.mode != "P":
                    f_p = f.convert("P", palette=Image.ADAPTIVE, colors=256)
                else:
                    f_p = f
                palette_frames.append(f_p)

            palette_frames[0].save(
                path,
                save_all=True,
                append_images=palette_frames[1:],
                duration=int(1000 / fps),
                loop=0,
                optimize=False,  # Disable to preserve crossfade frames
                disposal=2,
            )
            print(f"    Saved: {path}")

    class StarVisualizer(MetricVisualizer):
        """Animated star visualization — orbit radius and particle density scale with star count."""

        def animate_frame(self, img, metric_value, frame_idx, total_frames):
            t = (frame_idx / total_frames) * 2 * math.pi
            cx, cy = self.w / 2, self.h / 2

            log_val = math.log10(max(1, metric_value) + 1)
            level = min(1.0, log_val / 4.5)

            # More stars → larger orbit radius and more particles
            count = max(12, min(80, int(log_val * 22)))
            base_orbit_r = 38 + int(level * 38)  # 38–76 px
            p_size = 2.5 + level * 2.8            # 2.5–5.3 px

            for i in range(count):
                phase_offset = (i / count) * 2 * math.pi
                orbit_r = base_orbit_r + 10 * math.sin(phase_offset * 2 + i * 0.3)
                angle = phase_offset + t * 0.5
                r = orbit_r + 6 * math.sin(t * 2 + i * 0.2)
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                self.system.spawn(x, y, 1, p_size, 0.25, self.palette["primary"], 0.65, 0.01, angle + 1.57)

            # Background sparkles — density scales with metric
            sparkle_count = max(5, int(level * 18))
            for j in range(sparkle_count):
                x = 40 + (self.w - 80) * (j / max(1, sparkle_count - 1))
                y = 60 + (self.h - 120) * ((j * 0.7) % 1.0)
                b = 0.5 + 0.4 * math.sin(t * 2 + j * 0.8)
                c = tuple(int(v * b) for v in self.palette["glow"])
                self.system.spawn(x, y, 1, 1.2 + level, 0, c, 0.5, 0.015)

            self.system.update()
            new_img = self.system.render(img)
            img.paste(new_img, (0, 0))

    class ForkVisualizer(MetricVisualizer):
        """Animated fork visualization — branch count and particle size scale with forks."""

        def animate_frame(self, img, metric_value, frame_idx, total_frames):
            t = (frame_idx / total_frames) * 2 * math.pi
            cx, cy = self.w / 2, self.h / 2

            log_val = math.log10(max(1, metric_value) + 1)
            level = min(1.0, log_val / 4.5)

            # Branch count and thickness scale with fork count
            branches = max(4, min(20, 4 + int(log_val * 6)))
            line_w = max(2, int(2 + level * 2))
            branch_len = 42 + int(level * 28)
            for i in range(branches):
                phase_offset = (i / branches) * 2 * math.pi
                angle = phase_offset - 1.57 + t * 0.15
                length = branch_len + 8 * math.sin(phase_offset + t + i * 0.4)
                ex = cx + math.cos(angle) * length
                ey = cy + math.sin(angle) * length
                draw = ImageDraw.Draw(img)
                draw.line([cx, cy, ex, ey], fill=self.palette["primary"], width=line_w)

            # Orbiting particles — count and size scale with metric
            count = max(10, min(45, 10 + int(log_val * 9)))
            p_size = 2.0 + level * 2.5
            for i in range(count):
                phase_offset = (i / count) * 2 * math.pi
                angle = phase_offset + t * 0.4
                r = 28 + int(level * 22) + 18 * abs(math.sin(phase_offset + t * 0.8 + i * 0.2))
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                self.system.spawn(x, y, 1, p_size, 0.3, self.palette["glow"], 0.55, 0.01)

            self.system.update()
            new_img = self.system.render(img)
            img.paste(new_img, (0, 0))

    class IssueVisualizer(MetricVisualizer):
        """Animated issue visualization — pulse ring size and particle count scale with issues."""

        def animate_frame(self, img, metric_value, frame_idx, total_frames):
            t = (frame_idx / total_frames) * 2 * math.pi
            cx, cy = self.w / 2, self.h / 2

            log_val = math.log10(max(1, metric_value) + 1)
            level = min(1.0, log_val / 4.5)

            # Pulsing rings — base radius grows with issue count
            pulse_base = 28 + int(level * 22)
            pulse = pulse_base + 10 * math.sin(t * 2.2)
            for i in range(3):
                rs = pulse + i * (10 + int(level * 6))
                draw = ImageDraw.Draw(img)
                alpha_factor = 1.0 - i * 0.28
                c = tuple(max(0, int(v * alpha_factor)) for v in self.palette["primary"])
                draw.ellipse([cx - rs, cy - rs, cx + rs, cy + rs], outline=c, width=3)

            # Floating particles — count and spread scale with metric
            count = max(8, min(50, 8 + int(log_val * 9)))
            p_size = 2.0 + level * 2.5
            spread = 60 + int(level * 35)
            for i in range(count):
                phase_offset = (i / count) * 2 * math.pi
                y = self.h - 75 - 35 * (1 - math.cos(phase_offset + t * 1.5))
                x = cx + spread * math.sin(phase_offset + t + i * 0.35)
                sz = max(0.6, p_size + math.sin(phase_offset + t * 2 + i) * 1.0)
                self.system.spawn(x, y, 1, sz, 0.4, self.palette["primary"], 0.75, 0.012)

            self.system.update()
            new_img = self.system.render(img)
            img.paste(new_img, (0, 0))

    class FollowerVisualizer(MetricVisualizer):
        """Animated follower visualization — node count = follower count, orbit scales too."""

        def animate_frame(self, img, metric_value, frame_idx, total_frames):
            t = (frame_idx / total_frames) * 2 * math.pi
            cx, cy = self.w / 2, self.h / 2

            log_val = math.log10(max(1, metric_value) + 1)
            level = min(1.0, log_val / 4.5)

            # Node count mirrors actual follower count (capped); orbit radius grows with count
            nodes = max(4, min(20, max(1, metric_value)))
            orbit_r_base = 28 + int(level * 30)  # 28–58 px
            node_size = 4 + int(level * 3)        # node dot size grows too
            conn_dist = 55 + int(level * 30)      # connection draw distance grows

            node_pos = []
            for i in range(nodes):
                phase_offset = (i / nodes) * 2 * math.pi
                angle = phase_offset + t * 0.18
                r = orbit_r_base + 13 * math.sin(phase_offset + t + i * 0.35)
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                node_pos.append((x, y))
                draw = ImageDraw.Draw(img)
                draw.ellipse([x - node_size, y - node_size, x + node_size, y + node_size],
                             fill=self.palette["primary"])

            for i in range(len(node_pos)):
                for j in range(i + 1, len(node_pos)):
                    x1, y1 = node_pos[i]
                    x2, y2 = node_pos[j]
                    d = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    if d < conn_dist:
                        alpha = int(200 * (1 - d / conn_dist))
                        c = tuple(int(v * alpha / 255) for v in self.palette["secondary"])
                        draw = ImageDraw.Draw(img)
                        draw.line([x1, y1, x2, y2], fill=c, width=2)

            # Orbiting glow particles — count and size scale with followers
            p_count = max(10, min(32, 10 + int(log_val * 7)))
            p_size = 1.8 + level * 2.2
            for i in range(p_count):
                phase_offset = (i / p_count) * 2 * math.pi
                angle = phase_offset + t * 0.6
                r = 20 + int(level * 16) + 10 * math.sin(phase_offset + t + i * 0.25)
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                self.system.spawn(x, y, 1, p_size, 0.25, self.palette["glow"], 0.5, 0.015)

            self.system.update()
            new_img = self.system.render(img)
            img.paste(new_img, (0, 0))

    class PRVisualizer(MetricVisualizer):
        """Animated PR visualization — arrow scale and particle density reflect PR count."""

        def animate_frame(self, img, metric_value, frame_idx, total_frames):
            t = (frame_idx / total_frames) * 2 * math.pi
            cx, cy = self.w / 2, self.h / 2

            log_val = math.log10(max(1, metric_value) + 1)
            level = min(1.0, log_val / 4.5)

            # Merge arrows — size and spacing scale with PR count
            arrow_scale = 1.0 + level * 0.6
            shaft_w = max(2, int(3 * arrow_scale))
            for i in range(2):
                offset = (i - 0.5) * (32 + int(level * 14))
                draw = ImageDraw.Draw(img)
                draw.line(
                    [cx - int(28 * arrow_scale), cy + offset,
                     cx + int(28 * arrow_scale), cy + offset],
                    fill=self.palette["primary"], width=shaft_w,
                )
                draw.polygon(
                    [
                        (cx + int(28 * arrow_scale), cy + offset),
                        (cx + int(18 * arrow_scale), cy + offset - int(9 * arrow_scale)),
                        (cx + int(18 * arrow_scale), cy + offset + int(9 * arrow_scale)),
                    ],
                    fill=self.palette["primary"],
                )

            # Floating PR particles — count and size scale with PRs
            count = max(8, min(48, 8 + int(log_val * 11)))
            p_size = 2.0 + level * 2.5
            spread = 12 + int(level * 6)
            for i in range(count):
                y = self.h - 80 - (frame_idx / total_frames) * 70 + 16 * math.sin(t * 1.5 + i)
                x = cx + (i - count / 2) * spread * math.sin(t + i * 0.35)
                sz = max(0.5, p_size + math.sin(t * 2 + i) * 0.9)
                self.system.spawn(x, y, 1, sz, 0.35, self.palette["primary"], 0.7, 0.013)

            # Orbiting glow particles — count scales with PRs
            orb_count = max(3, min(10, 3 + int(log_val * 3)))
            for j in range(orb_count):
                angle = (j / orb_count) * 6.28 + t
                r = 48 + int(level * 22) + 12 * math.sin(t + j)
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                self.system.spawn(x, y, 1, 2.0 + level * 1.5, 0.2, self.palette["glow"], 0.45, 0.016)

            self.system.update()
            new_img = self.system.render(img)
            img.paste(new_img, (0, 0))

    def hstack(images):
        """Horizontal concatenation of images."""
        if not images:
            raise ValueError("No images")
        ws, hs = zip(*(i.size for i in images))
        h = max(hs)
        w = sum(ws)
        res = Image.new("RGB", (w, h))
        x = 0
        for img in images:
            res.paste(img, (x, (h - img.height) // 2))
            x += img.width
        return res

    def vstack(images):
        """Vertical concatenation of images."""
        if not images:
            raise ValueError("No images")
        ws, hs = zip(*(i.size for i in images))
        w = max(ws)
        h = sum(hs)
        res = Image.new("RGB", (w, h))
        y = 0
        for img in images:
            res.paste(img, ((w - img.width) // 2, y))
            y += img.height
        return res

    def create_2x2_grid(gif_paths, out_path, fps=12):
        """Create a 2x2 grid dashboard from individual metric GIFs with smooth looping using ping-pong."""
        print("  Building 2x2 grid dashboard...")

        all_frames = []

        for p in gif_paths:
            try:
                frames = []
                with Image.open(p) as img:
                    try:
                        while True:
                            frames.append(img.copy().convert("RGB"))
                            img.seek(img.tell() + 1)
                    except EOFError:
                        pass
                all_frames.append(frames)
                print(f"    {p}: {len(frames)} frames")
            except Exception as e:
                print(f"    Warning: {p} - {e}")
                all_frames.append([Image.new("RGB", (600, 300), (25, 25, 35))])

        # Ensure all have same frame count
        target_frames = min(len(f) for f in all_frames)
        print(f"    Using {target_frames} frames for grid...")

        # Trim frames to exact target
        for i in range(4):
            if len(all_frames[i]) > target_frames:
                all_frames[i] = all_frames[i][:target_frames]

        # Create grid frames - all 4 GIFs synchronized at same frame index
        result = []
        for i in range(target_frames):
            # Get frames at same index from all 4 GIFs (synchronized)
            frame0 = all_frames[0][i].resize((600, 300), Image.LANCZOS)
            frame1 = all_frames[1][i].resize((600, 300), Image.LANCZOS)
            frame2 = all_frames[2][i].resize((600, 300), Image.LANCZOS)
            frame3 = all_frames[3][i].resize((600, 300), Image.LANCZOS)

            # Create 2x2 grid
            top_row = hstack([frame0, frame1])
            bottom_row = hstack([frame2, frame3])
            grid = vstack([top_row, bottom_row])
            result.append(grid)

        # PING-PONG LOOP: Forward then backward to create seamless transition
        # This ensures the animation smoothly returns to start
        ping_pong_result = result.copy()

        # Add reverse frames (excluding first and last to avoid duplication)
        for i in range(len(result) - 2, 0, -1):
            ping_pong_result.append(result[i])

        print(f"    Created {len(ping_pong_result)} frames (ping-pong)")

        ping_pong_result[0].save(
            out_path,
            save_all=True,
            append_images=result[1:],
            duration=int(1000 / fps),
            loop=0,
            optimize=False,
            disposal=2,
        )
        print(f"    Saved: {out_path} ({len(result)} frames)")

    def create_svg_embedded_gif(gif_path, output_path, width=1200, height=600):
        """Create SVG embed for the GIF with responsive sizing."""
        print("  Building SVG embed...")

        with open(gif_path, "rb") as f:
            gif_data = base64.b64encode(f.read()).decode("ascii")

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <title>Marcelo Burgos - GitHub Profile Metrics</title>
  <desc>GitHub profile metrics: {stars:,} total stars, {forks:,} total forks, {issues:,} open issues, {followers:,} followers across {repos:,} repositories</desc>
  <defs>
    <style>
      .metrics-gif {{
        width: 100%;
        height: auto;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      }}
    </style>
  </defs>
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml" style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;background:transparent;">
      <img src="data:image/gif;base64,{gif_data}" alt="GitHub Metrics: {stars:,} stars, {forks:,} forks, {issues:,} issues, {followers:,} followers across {repos:,} repositories" class="metrics-gif"/>
    </div>
  </foreignObject>
</svg>'''

        with open(output_path, "w") as f:
            f.write(svg)
        print(f"    Saved: {output_path}")

    # ============================================================
    # GENERATE HIGH-RESOLUTION ANIMATIONS
    # ============================================================

    print("\n[ART] Generating high-resolution animations...")

    # High resolution: 600x300 per metric (was 400x200)
    w, h = 600, 300
    fps_individual = 15
    frames_individual = 40
    fps_dashboard = 12

    paths = []

    # Generate 4 metric animations for 2x2 grid
    StarVisualizer(w, h, Colors.STAR, "[*] Total Stars").animate(
        stars, "assets/metric_stars.gif", frames_individual, fps_individual
    )
    paths.append("assets/metric_stars.gif")

    ForkVisualizer(w, h, Colors.FORK, "[~] Total Forks").animate(
        forks, "assets/metric_forks.gif", frames_individual, fps_individual
    )
    paths.append("assets/metric_forks.gif")

    IssueVisualizer(w, h, Colors.ISSUE, "[!] Open Issues").animate(
        issues, "assets/metric_issues.gif", frames_individual, fps_individual
    )
    paths.append("assets/metric_issues.gif")

    FollowerVisualizer(w, h, Colors.FOLLOWER, "[@] Followers").animate(
        followers, "assets/metric_followers.gif", frames_individual, fps_individual
    )
    paths.append("assets/metric_followers.gif")

    # Create 2x2 grid dashboard
    create_2x2_grid(paths, "assets/metrics_dashboard.gif", fps_dashboard)

    # Create SVG embed for web display
    create_svg_embedded_gif(
        "assets/metrics_dashboard.gif",
        "assets/metrics_dashboard.svg",
        width=1200,
        height=600,
    )

    print("\n" + "=" * 60)
    print("[OK] Done!")
    print(f"   Resolution: 600x300 per metric, 1200x600 dashboard (2x2 grid)")
    print(f"   Dashboard shows: Stars, Forks, Issues, Followers")
    print("=" * 60)
